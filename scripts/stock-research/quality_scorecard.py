"""Offline, immutable forecast follow-through. Never collect, fit, predict or promote."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
import hashlib
import html
import importlib.util
from importlib.metadata import version
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
MAX_FILE = 32 * 1024**2
MAX_TOTAL = 128 * 1024**2
MAX_JSON = 10 * 1024**2
MAX_ROWS = 10000
MAX_REFS = 256
CHECKS = {'frozen_evidence_admission_hashes', 'exact_original_security_currency',
          'same_source_field_basis', 'original_target_binding', 'reference_same_close',
          'issue_before_target', 'actual_after_settlement', 'original_actions_cover_outcome',
          'new_overlap_closes_same'}
EXPORT_COLUMNS = {'purpose', 'ticker', 'market', 'currency', 'status', 'reasons',
    'classification', 'is_demo', 'reference_session', 'reference_close_at', 'reference_close',
    'target_session', 'target_close_at', 'issued_at', 'report_cutoff', 'point', 'low', 'high',
    'direction', 'method_id', 'observations', 'horizon_sessions', 'calibration_status',
    'range_scope', 'mu', 'sample_sd', 'provider', 'source_url', 'public_derived_forecast',
    'evidence_sha256', 'admission_sha256', 'result_sha256'}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def keys(value, required, optional=()):
    require(type(value) is dict and set(required) <= set(value)
            and set(value) <= set(required) | set(optional), 'unknown-or-missing-fields')


def integer(value, minimum=0):
    require(type(value) is int and value >= minimum, 'invalid-integer')
    return value


def stamp(value):
    require(type(value) is str, 'timestamp-missing')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None and result.utcoffset() is not None, 'timestamp-offset-required')
    return result


def milliseconds(value):
    return int(stamp(value).timestamp() * 1000)


def number(value):
    require(type(value) is not bool, 'invalid-number')
    result = float(value)
    require(math.isfinite(result) and result > 0, 'invalid-positive-number')
    return result


def decode(raw):
    require(len(raw) <= MAX_JSON, 'json-budget')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate-json-key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('nonfinite-json')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except RecursionError:
        raise ValueError('json-nesting-budget') from None


def check_ref(ref):
    keys(ref, ('path', 'sha256', 'bytes'))
    require(type(ref['path']) is str and Path(ref['path']).is_absolute(), 'absolute-path-required')
    require(type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'invalid-sha256')
    require(integer(ref['bytes']) <= MAX_FILE, 'file-budget')


def private_path(value, directory=False):
    path = Path(value)
    require(path.is_absolute() and str(path) == str(path.resolve()) and '..' not in path.parts,
            'symlink-or-relative-path')
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink-or-relative-path')
    info = path.stat()
    require(info.st_uid == os.getuid() and (stat.S_ISDIR(info.st_mode) if directory
            else stat.S_ISREG(info.st_mode)), 'private-file-type-or-owner')
    require(stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600), 'private-permissions')
    if not directory:
        require(stat.S_IMODE(path.parent.stat().st_mode) == 0o700, 'private-permissions')
    return path


def private_read(path):
    path = private_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_FILE
                and stat.S_IMODE(info.st_mode) == 0o600, 'file-budget-or-permissions')
        raw = source.read(MAX_FILE + 1)
        require(len(raw) == info.st_size and len(raw) <= MAX_FILE, 'file-changed-or-budget')
    return raw


class Snapshots:
    """Finite explicit refs only. JSON paths are never followed recursively."""
    def __init__(self, reader=private_read):
        self.reader, self.raw, self.refs = reader, {}, {}
        self.total = 0

    def read(self, ref):
        check_ref(ref)
        path = ref['path']
        if path in self.raw:
            require(self.refs[path] == ref, 'conflicting-file-reference')
            return self.raw[path]
        require(len(self.raw) < MAX_REFS, 'reference-budget')
        raw = self.reader(path)
        require(len(raw) == ref['bytes'] and sha(raw) == ref['sha256'], 'input-hash-or-bytes-mismatch')
        self.total += len(raw)
        require(self.total <= MAX_TOTAL, 'aggregate-input-budget')
        self.raw[path], self.refs[path] = raw, dict(ref)
        return raw

    def document(self, ref):
        return decode(self.read(ref))


def csv_rows(raw):
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')), strict=True)
    headers = reader.fieldnames or []
    require(len(headers) == len(set(headers)), 'duplicate-csv-header')
    result = []
    for row in reader:
        require(None not in row and all(v is not None for v in row.values()), 'csv-row-width')
        require(len(result) < MAX_ROWS, 'forecast-row-budget')
        result.append(row)
    require(result, 'empty-csv')
    return result, set(headers)


def legacy_evaluator():
    # Fixed repository module, never an input-supplied executable or model artifact.
    path = ROOT / 'harness/forecast_review.py'
    spec = importlib.util.spec_from_file_location('_quality_terminal_review', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def result_row(cohort, identity, target, horizon, origin, issued, forecast_id, semantics, currency):
    return dict(cohort_id=cohort, instrument=identity, target=target, horizon=horizon,
        origin=origin, issued_at=issued, forecast_id=forecast_id, target_semantics=semantics,
        currency=currency, scoring_status='unscored', quality_status='insufficient', reasons=[],
        model_metrics=None, baseline_metrics=None, baseline_comparison=None,
        low_endpoint_error=None, high_endpoint_error=None, terminal_error=None,
        whole_window_containment=None, terminal_range_hit=None, direction_hit=None,
        brier_score=None, point_absolute_error=None, point_error_fraction=None,
        terminal_range_width=None, terminal_width_fraction=None,
        normalized_error=None, market=identity.split('.')[0], interval_coverage=None,
        baseline_available=False, baseline_present_at_origin=None)


def failed(row, reason):
    for name in ('model_metrics', 'baseline_metrics', 'baseline_comparison', 'low_endpoint_error',
                 'high_endpoint_error', 'terminal_error', 'whole_window_containment',
                 'terminal_range_hit', 'direction_hit', 'brier_score', 'point_absolute_error',
                 'point_error_fraction', 'terminal_range_width', 'terminal_width_fraction',
                 'normalized_error', 'interval_coverage'):
        row[name] = None
    row['baseline_available'] = False
    row['baseline_present_at_origin'] = None
    row.update(scoring_status='invalid', quality_status='failed', reasons=[reason])
    return row


def financial_binding(analysis, analysis_sha, financial, now):
    keys(financial, ('schema_version', 'kind', 'analysis_sha256', 'reviewer', 'reviewed_at',
                     'decision', 'cohorts', 'limitations'))
    require(type(financial['schema_version']) is int and financial['schema_version'] == 1
        and financial['kind'] == 'quality-scorecard-financial-review'
        and financial['analysis_sha256'] == analysis_sha and financial['reviewer'] == 'Trader'
        and financial['decision'] == 'accepted', 'financial-review-not-bound-or-accepted')
    # This is a later workflow review, not a backdated observation/issuance clock.
    require(stamp(financial['reviewed_at']) <= now, 'future-financial-workflow-review')
    require(type(financial['limitations']) is list and type(financial['cohorts']) is list,
            'financial-review-schema')
    mapping = {}
    for item in financial['cohorts']:
        keys(item, ('cohort_id', 'forecasts_sha256', 'target_semantics',
                    'accepted_outcome_review_sha256', 'limitations'))
        require(item['cohort_id'] not in mapping and type(item['accepted_outcome_review_sha256']) is list
                and type(item['limitations']) is list, 'financial-cohort-duplicate-or-schema')
        mapping[item['cohort_id']] = item
    require(set(mapping) == {c['cohort_id'] for c in analysis['cohorts']}, 'financial-cohort-set')
    for cohort in analysis['cohorts']:
        item = mapping[cohort['cohort_id']]
        require(item['forecasts_sha256'] == cohort['forecasts']['sha256'], 'financial-forecast-hash')
        expected = 'terminal_close' if cohort['kind'] == 'terminal_close_csv' else 'whole_window_ohlc'
        require(item['target_semantics'] == expected, 'financial-target-semantics')
    return mapping


def accepted_terminal_actual(original, cohort, reviews, financial, cutoff, batch_item):
    matches = [(ref, doc) for ref, doc in reviews
               if doc.get('ticker') == original['ticker'] and doc.get('market') == original['market']]
    if not matches:
        return None
    require(len(matches) == 1, 'duplicate-or-conflicting-actual-reviews')
    ref, review = matches[0]
    require(ref['sha256'] in financial['accepted_outcome_review_sha256'], 'financial-actual-not-accepted')
    require(review.get('decision') == 'accepted_private_outcome_comparability'
        and review.get('reviewer') == 'Trader' and review.get('failures') == []
        and all(review.get('checks', {}).get(k) is True for k in CHECKS), 'outcome-comparability-not-accepted')
    require(review.get('frozen_csv_sha256') == cohort['forecasts']['sha256']
        and review.get('frozen_row_sha256') == sha(canonical(original))
        and all(review.get('frozen_'+name+'_sha256') == original[name+'_sha256']
                for name in ('evidence', 'admission', 'result')), 'original-forecast-binding-mismatch')
    require(stamp(review['reviewed_at']) <= cutoff, 'actual-review-after-cutoff')
    evidence = batch_item['evidence']
    admission = batch_item['admission']
    require(sha(canonical(evidence)) == original['evidence_sha256']
        and sha(canonical(admission)) == original['admission_sha256'], 'original-evidence-admission-mismatch')
    require(evidence['instrument']['instrument_id'] == original['market']+'.'+original['ticker']
        and evidence['instrument']['currency'] == original['currency'] == review.get('actual_currency')
        and evidence['source']['basis'] == review.get('actual_basis') == 'unadjusted'
        and evidence['source']['source_field'] == review.get('actual_source_field') == 'close'
        and evidence['source']['estimand'] == 'vendor_regular_close'
        and review.get('actual_session') == original['target_session'], 'actual-target-currency-basis-identity')
    available, settled = stamp(review['actual_available_at']), stamp(review['actual_settled_at'])
    close = stamp(original['target_close_at'])
    require(close <= settled <= available <= cutoff and available <= stamp(review['reviewed_at']),
            'actual-availability-or-settlement')
    store = review['actual_store_binding']
    record, observed = store['record'], store['observation']
    actual = number(review['actual_close'])
    require(record['code'] == original['market']+'.'+original['ticker']
        and record['date'] == original['target_session'] and type(record['adjustment']) is int and record['adjustment'] == 0
        and number(record['close']) == actual and observed['known_ms'] == milliseconds(review['actual_available_at'])
        and observed['raw_hash'] == review['actual_raw_hash']
        and store['semantic_hash'] == review['actual_semantic_hash'], 'actual-retained-source-binding')
    require(observed['observed_ms'] <= observed['ingested_ms'] <= observed['known_ms']
            and observed['status'] == 'success', 'actual-source-clock-order')
    return review, ref['sha256']


def audit_baseline(original, audit_rows, audit, manifest, batch_item, actual):
    """Extract two already-issued estimates, using identical unrounded precision."""
    selected = [r for r in audit_rows if r.get('market') == original['market']
                and r.get('ticker') == original['ticker'] and r.get('currency') == original['currency']]
    require(len(selected) == 1, 'baseline-audit-identity-not-unique')
    row = selected[0]
    require(all(row.get(k+'_sha256') == original[k+'_sha256'] for k in ('evidence', 'admission', 'result'))
        and sha(canonical(row['result'])) == original['result_sha256'], 'baseline-audit-result-binding')
    result = row['result']
    require(result['status'] == 'generated' and result['classification'] == 'reviewed_real'
            and result['instrument']['instrument_id'] == original['market']+'.'+original['ticker']
            and result['instrument']['currency'] == original['currency'], 'baseline-audit-result-identity')
    estimates, origin = result['estimates'], result['provenance']['audit']
    require(audit['issued_at'] == original['issued_at'] == origin['issued_at']
        and audit['report_cutoff'] == original['report_cutoff'] == origin['report_cutoff']
        and all(origin[k] == original[k] for k in ('reference_session', 'target_session', 'method_id'))
        and stamp(origin['target_close_at']) == stamp(original['target_close_at'])
        and stamp(origin['reference_close_at']) == stamp(original['reference_close_at'])
        and number(origin['reference_close']) == number(original['reference_close'])
        and origin['horizon_sessions'] == 1
        and origin['evidence_sha256'] == original['evidence_sha256']
        and origin['admission_sha256'] == original['admission_sha256']
        and origin['method_sha256'] == sha(canonical(batch_item['evidence']['method']))
        and stamp(audit['issued_at']) <= stamp(manifest['created_at']) < stamp(original['target_close_at']),
        'baseline-origin-or-method-mismatch')
    require(all(number(estimates['display_'+k]) == number(original[k]) for k in ('point', 'low', 'high')),
            'baseline-model-display-mismatch')
    reference = number(original['reference_close'])
    output = []
    for prefix in ('', 'baseline_'):
        values = {k:number(estimates[prefix+k]) for k in ('point', 'low', 'high')}
        require(values['low'] <= values['point'] <= values['high']
            and all(values[k] == number(origin[prefix+k]) for k in values), 'baseline-audit-estimate-mismatch')
        values.update(absolute_error=abs(values['point']-actual),
            absolute_error_fraction=abs(values['point']-actual)/reference,
            range_hit=values['low'] <= actual <= values['high'],
            width=values['high']-values['low'], width_fraction=(values['high']-values['low'])/reference)
        output.append(values)
    return output


def terminal_rows(cohort, snapshots, financial, cutoff):
    keys(cohort, ('cohort_id', 'kind', 'forecasts', 'original_batch', 'outcome_reviews',
                  'outcome_acceptance', 'baseline'))
    originals, headers = csv_rows(snapshots.read(cohort['forecasts']))
    require(headers == EXPORT_COLUMNS, 'unsupported-terminal-export-columns')
    batch = snapshots.document(cohort['original_batch'])
    require(type(batch.get('items')) is list, 'original-batch-schema')
    items = {(x['market'], x['ticker']): x for x in batch['items']}
    require(len(items) == len(batch['items']), 'duplicate-original-batch-identity')
    require(type(cohort['outcome_reviews']) is list and len(cohort['outcome_reviews']) <= MAX_REFS,
            'outcome-review-budget')
    reviews = [(ref, snapshots.document(ref)) for ref in cohort['outcome_reviews']]
    require(set(financial['accepted_outcome_review_sha256']) == {r['sha256'] for r, _ in reviews},
            'financial-actual-review-set')
    acceptance = snapshots.document(cohort['outcome_acceptance'])
    require(acceptance.get('status') == 'accepted_privateonly'
            and acceptance.get('original_forecasts_preserved') is True
            and type(acceptance.get('outcome_comparability')) is int
            and acceptance['outcome_comparability'] >= len(reviews)
            and stamp(acceptance['at']) <= cutoff, 'original-outcome-acceptance-missing')
    evaluator, output = legacy_evaluator(), []
    baseline, saved_audit = None, None
    if cohort['baseline'] is not None:
        if cohort['baseline'].get('kind') == 'original_audit':
            keys(cohort['baseline'], ('kind', 'audit', 'manifest', 'precision'))
            require(cohort['baseline']['precision'] == 'original_unrounded_both', 'baseline-precision-contract')
            audit = snapshots.document(cohort['baseline']['audit'])
            manifest = snapshots.document(cohort['baseline']['manifest'])
            for name, ref in (('forecasts.csv', cohort['forecasts']), ('private-audit.json', cohort['baseline']['audit'])):
                require(manifest.get('artifacts', {}).get(name) == dict(sha256=ref['sha256'], bytes=ref['bytes']),
                        'baseline-manifest-artifact-binding')
            require(manifest.get('kind') == 'private-forecast-csv' and manifest.get('is_demo') is False
                and manifest.get('purpose') == 'private_research_only' and type(audit.get('rows')) is list
                and len(audit['rows']) == len(originals)
                and manifest.get('input_sha256') == audit.get('input_sha256'), 'baseline-audit-manifest-schema')
            saved_audit = (audit, manifest)
        else:
            keys(cohort['baseline'], ('forecasts', 'origin_review'))
            baseline_rows, baseline_headers = csv_rows(snapshots.read(cohort['baseline']['forecasts']))
            require(baseline_headers == EXPORT_COLUMNS, 'baseline-schema')
            receipt = snapshots.document(cohort['baseline']['origin_review'])
            require(receipt.get('kind') == 'origin-frozen-baseline'
                and receipt.get('forecasts_sha256') == cohort['baseline']['forecasts']['sha256'],
                'baseline-origin-binding')
            baseline = (baseline_rows, receipt)
    for original in originals:
        row = result_row(cohort['cohort_id'], original['market']+'.'+original['ticker'],
            original['target_session'], 'next_session', original['reference_session'],
            original['issued_at'], sha(canonical(original)), 'terminal_close', original['currency'])
        try:
            require(re.fullmatch(r'(US\.[A-Z][A-Z0-9.-]{0,63}|MY\.[0-9]{4}(?:EA)?)', row['instrument']),
                    'invalid-instrument')
            require(stamp(original['issued_at']) <= cutoff, 'forecast-issued-after-review')
            require(original['is_demo'] == 'False', 'synthetic-forecast')
            require(original['status'] in {'generated', 'withheld'}, 'unknown-original-status')
            if original['status'] != 'generated':
                row.update(scoring_status='withheld', reasons=[original['reasons'] or 'original-withheld'])
                output.append(row)
                continue
            require(original['classification'] == 'reviewed_real' and original['purpose'] == 'private_research_only'
                and original['range_scope'].startswith('next_close_not_intraday_extrema')
                and original['horizon_sessions'] == '1', 'terminal-target-semantics')
            require(stamp(original['reference_close_at']) <= stamp(original['report_cutoff'])
                    <= stamp(original['issued_at']) < stamp(original['target_close_at']), 'forecast-time-order')
            point, low, high, reference = (number(original[k]) for k in ('point', 'low', 'high', 'reference_close'))
            require(low <= point <= high, 'terminal-range-order')
            row.update(original_point=point, original_low=low, original_high=high,
                       original_direction=original['direction'], reference_close=reference,
                       target_mature=cutoff >= stamp(original['target_close_at']))
            if cutoff < stamp(original['target_close_at']):
                row.update(scoring_status='pending', quality_status='pending', reasons=['target-not-mature'])
                output.append(row)
                continue
            accepted = accepted_terminal_actual(original, cohort, reviews, financial, cutoff,
                                                items[(original['market'], original['ticker'])])
            if accepted is None:
                row.update(scoring_status='missing_actual', reasons=['reviewed-comparable-actual-missing'])
                output.append(row)
                continue
            review, actual_review_sha = accepted
            ledger = {k: '' for k in evaluator.REQUIRED}
            ledger.update(forecast_id=row['forecast_id'], report_date=stamp(original['issued_at']).date().isoformat(),
                as_of=original['issued_at'], horizon_type='next_session', market=original['market'],
                venue=original['market'], ticker=original['ticker'], reference_close_date=original['reference_session'],
                reference_close=original['reference_close'], reference_source=original['source_url'],
                forecast_target_date=original['target_session'], forecast_target_close_at=original['target_close_at'],
                forecast_direction=original['direction'], forecast_range_low=original['low'],
                forecast_range_high=original['high'], actual_close_date=review['actual_session'],
                actual_close=str(review['actual_close']), actual_source=review['actual_source_url'],
                actual_available_at=review['actual_available_at'], status='pending', scoring_notes='')
            scored = evaluator.evaluate_row(ledger, cutoff)
            require(scored['status'] == 'scored', 'terminal-evaluator-not-scored')
            actual = number(review['actual_close'])
            row.update(scoring_status='scored', direction_hit=scored['direction_hit'],
                terminal_range_hit=scored['range_hit'], interval_coverage=scored['range_hit'],
                brier_score=scored['brier_score'], point_absolute_error=abs(point-actual),
                point_error_fraction=abs(point-actual)/reference, normalized_error=abs(point-actual)/reference,
                terminal_range_width=high-low, terminal_width_fraction=(high-low)/reference,
                terminal_error=abs(point-actual), actual_close=actual, reference_close=reference,
                original_point=point, original_low=low, original_high=high,
                actual_review_sha256=actual_review_sha,
                unavailable_metrics=dict(brier_score='Original export supplies no probability_up.',
                    low_endpoint_error='Terminal-close forecast, not an intraday-low forecast.',
                    high_endpoint_error='Terminal-close forecast, not an intraday-high forecast.',
                    whole_window_containment='Terminal-close interval, not a whole-window envelope.'),
                reasons=['no-frozen-qualification-policy', 'terminal-range-is-not-intraday-extrema'])
            row['display_metric_precision'] = 'original CSV currency-rounded point/range'
            if saved_audit is not None:
                try:
                    model_metrics, base_metrics = audit_baseline(original, saved_audit[0]['rows'],
                        saved_audit[0], saved_audit[1], items[(original['market'], original['ticker'])], actual)
                    row.update(baseline_available=True, model_metrics=model_metrics,
                        baseline_metrics=base_metrics, baseline_present_at_origin=True,
                        baseline_comparison=dict(precision='original_unrounded_both',
                            absolute_error_fraction_difference=base_metrics['absolute_error_fraction']
                                - model_metrics['absolute_error_fraction'],
                            model_range_hit=model_metrics['range_hit'], baseline_range_hit=base_metrics['range_hit']))
                except (ValueError, KeyError, TypeError, OverflowError) as error:
                    row['reasons'].append('baseline-unavailable: '+str(error))
            elif baseline is None:
                row['reasons'].append('origin-time-matched-baseline-not-supplied')
            else:
                candidates = [b for b in baseline[0] if all(b[k] == original[k] for k in
                    ('market', 'ticker', 'currency', 'reference_session', 'target_session', 'method_id', 'horizon_sessions'))]
                require(len(candidates) == 1, 'baseline-match-not-unique')
                b = candidates[0]
                require(b['reference_close'] == original['reference_close'] and b['status'] == 'generated'
                    and stamp(b['issued_at']) <= stamp(original['issued_at'])
                    and stamp(baseline[1]['known_at']) <= stamp(original['issued_at']), 'baseline-not-known-at-origin')
                base_error = abs(number(b['point'])-actual)/reference
                row.update(baseline_available=True, baseline_metrics={'point_error_fraction': base_error},
                    baseline_comparison={'point_error_fraction_difference': base_error-row['point_error_fraction']})
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            failed(row, str(error))
        output.append(row)
    return output


def ohlc_rows(cohort, snapshots, financial, cutoff):
    keys(cohort, ('cohort_id', 'kind', 'forecasts', 'actuals', 'calendar', 'baseline'))
    require(cohort['baseline'] == 'embedded-original-only', 'saved-baseline-contract')
    keys(cohort['calendar'], ('name', 'start', 'end', 'version'))
    start, end = (date.fromisoformat(cohort['calendar'][k]) for k in ('start', 'end'))
    require(0 < (end-start).days <= 3660, 'calendar-span-budget')
    # Import numerical evaluation functions, never a model artifact/fit/prediction entry point.
    directory = str(ROOT / 'scripts/stock-research')
    if directory not in sys.path:
        sys.path.insert(0, directory)
    from data import assemble
    from market_calendar import MarketCalendar
    from evaluation import review_forecasts, check_forecast_id
    payload = snapshots.document(cohort['forecasts'])
    forecasts = payload.get('forecasts')
    require(type(forecasts) is list and 0 < len(forecasts) <= MAX_ROWS, 'saved-forecast-budget')
    calendar = MarketCalendar(cohort['calendar']['start'], cohort['calendar']['end'], cohort['calendar']['name'])
    require(calendar.version == cohort['calendar']['version'], 'calendar-version-mismatch')
    history, basis = assemble([], []), {}
    if cohort['actuals'] is not None:
        actuals = cohort['actuals']
        keys(actuals, ('history_csv', 'receipt', 'basis_evidence', 'review'))
        review = snapshots.document(actuals['review'])
        keys(review, ('kind', 'decision', 'known_at', 'forecasts_sha256', 'inputs_sha256', 'calendar', 'targets'))
        require(actuals['review']['sha256'] in financial['accepted_outcome_review_sha256']
            and review['kind'] == 'reviewed-ohlc-actuals' and review['decision'] == 'accepted'
            and review['forecasts_sha256'] == cohort['forecasts']['sha256']
            and review['inputs_sha256'] == {k: actuals[k]['sha256'] for k in ('history_csv', 'receipt', 'basis_evidence')}
            and review['calendar'] == cohort['calendar']
            and review['targets'] == ['low_return', 'high_return', 'terminal_logreturn']
            and stamp(review['known_at']) <= cutoff, 'actual-ohlc-review-binding')
        rows, _ = csv_rows(snapshots.read(actuals['history_csv']))
        receipt = snapshots.document(actuals['receipt'])
        history = assemble(rows, [receipt])
        basis = snapshots.document(actuals['basis_evidence'])
    else:
        require(financial['accepted_outcome_review_sha256'] == [], 'unexpected-actual-approval')
    output = []
    for forecast in forecasts:
        reference = forecast.get('reference') or {}
        row = result_row(cohort['cohort_id'], forecast['code'], forecast['window']['end'], forecast['horizon'],
            forecast['origin'], datetime.fromtimestamp(forecast['issued_at_ms']/1000, timezone.utc).isoformat(),
            forecast['forecast_id'], 'whole_window_ohlc', reference.get('currency'))
        row['baseline_present_at_origin'] = forecast.get('baseline') is not None
        model = forecast.get('model') or {}
        row.update(original_low=model.get('predicted_low'), original_high=model.get('predicted_high'),
                   target_mature=int(cutoff.timestamp()*1000) >= forecast['window']['last_close_ms'])
        prices = model.get('price_quantiles')
        if type(prices) is list and len(prices) == 3 and type(prices[2]) is list and len(prices[2]) == 3:
            row['original_point'] = prices[2][1]
        try:
            check_forecast_id(forecast)
            if forecast['status'] != 'available':
                row.update(scoring_status='withheld', reasons=['original-forecast-unavailable'])
                output.append(row)
                continue
            require(type(forecast['as_of_ms']) is int and type(forecast['issued_at_ms']) is int
                and forecast['as_of_ms'] <= forecast['issued_at_ms'] < forecast['window']['first_open_ms'],
                'saved-full-window-issuance-after-start')
            outcomes = review_forecasts([forecast], history, calendar=calendar,
                review_at_ms=int(cutoff.timestamp()*1000), basis_evidence=basis)
            actual = outcomes['current_outcomes'][0]
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            output.append(failed(row, str(error)))
            continue
        if actual['status'] == 'pending':
            row.update(scoring_status='pending', quality_status='pending', reasons=[actual['reason']],
                       unavailable_metrics={'all_outcome_metrics':actual['reason']})
        elif actual['status'] == 'scored':
            metrics = actual['metrics']['model']
            row.update(scoring_status='scored', model_metrics=metrics, baseline_metrics=actual['metrics']['baseline'],
                baseline_available=True, baseline_comparison={t: actual['metrics']['baseline'][t]['absolute_error']
                    - metrics[t]['absolute_error'] for t in ('low_return', 'high_return', 'terminal_logreturn')},
                low_endpoint_error=metrics['low_return']['price_absolute_error'],
                high_endpoint_error=metrics['high_return']['price_absolute_error'],
                terminal_error=metrics['terminal_logreturn']['absolute_error'],
                whole_window_containment=metrics['joint_envelope_containment'],
                normalized_error=metrics['terminal_logreturn']['absolute_error'],
                interval_coverage=metrics['terminal_logreturn']['coverage'],
                actual_close=actual['actual']['terminal_close'], actual_low=actual['actual']['realized_low'],
                actual_high=actual['actual']['realized_high'],
                reasons=['no-frozen-qualification-policy', 'sample-and-class-gates-not-established'])
        else:
            missing = cohort['actuals'] is None or actual['reason'] == 'missing-required-session'
            if missing:
                row.update(scoring_status='missing_actual', reasons=[actual['reason']])
            else:
                failed(row, actual['reason'])
        output.append(row)
    return output


def weighted_mean(rows, getter):
    dates = defaultdict(lambda:defaultdict(lambda:defaultdict(list)))
    for row in rows:
        value = getter(row)
        if value is not None:
            dates[row['origin']][row['instrument']][row['horizon']].append(float(value))
    per_date = []
    for instruments in dates.values():
        per_instrument = [sum(sum(v)/len(v) for v in horizons.values())/len(horizons)
                          for horizons in instruments.values()]
        per_date.append(sum(per_instrument)/len(per_instrument))
    return sum(per_date)/len(per_date) if per_date else None


def summarize(rows):
    """Equal origins, then instruments, horizons, then correlated issuances."""
    counts = dict(Counter(r['scoring_status'] for r in rows))
    scored = [r for r in rows if r['scoring_status'] == 'scored']
    weighted = {metric:weighted_mean(scored, lambda r:r[metric])
                for metric in ('normalized_error', 'interval_coverage', 'direction_hit')}
    paired = [r for r in rows if r['scoring_status'] == 'scored' and r['baseline_available']
              and r['target_semantics'] == 'terminal_close' and r['model_metrics'] is not None]
    paired_summary = None
    if paired:
        # The pair count remains descriptive; cross-sectional names are not dates.
        paired_summary = dict(precision='original_unrounded_both', pairs=len(paired),
            distinct_origin_dates=len({r['origin'] for r in paired}),
            distinct_instrument_targets=len({(r['instrument'],r['target'],r['horizon']) for r in paired}),
            model_mean_absolute_error_fraction=weighted_mean(paired, lambda r:r['model_metrics']['absolute_error_fraction']),
            baseline_mean_absolute_error_fraction=weighted_mean(paired, lambda r:r['baseline_metrics']['absolute_error_fraction']),
            model_weighted_range_hit_rate=weighted_mean(paired, lambda r:r['model_metrics']['range_hit']),
            baseline_weighted_range_hit_rate=weighted_mean(paired, lambda r:r['baseline_metrics']['range_hit']),
            model_range_hits=sum(r['model_metrics']['range_hit'] for r in paired),
            baseline_range_hits=sum(r['baseline_metrics']['range_hit'] for r in paired),
            model_smaller_absolute_error=sum(r['model_metrics']['absolute_error_fraction']
                < r['baseline_metrics']['absolute_error_fraction'] for r in paired),
            interpretation='MAE and range rates use equal dates, instruments, horizons, then issuances. '
                'Raw pair/hit/win counts are diagnostic correlated issuance counts only. '
                'No confidence interval, independent-date or qualification claim.')
    return dict(issuances=len(rows), counts=counts, paired_comparison=paired_summary,
        mature_generated_targets=sum(r.get('target_mature') is True and r['scoring_status'] != 'withheld' for r in rows),
        quality_counts=dict(Counter(r['quality_status'] for r in rows)),
        distinct_instruments=len({r['instrument'] for r in rows}),
        distinct_instrument_targets=len({(r['instrument'], r['target'], r['horizon']) for r in rows if r['target']}),
        distinct_origin_dates=len({r['origin'] for r in rows if r['origin']}),
        scored_origin_dates=len({r['origin'] for r in rows if r['scoring_status'] == 'scored'}),
        scored_instrument_targets=len({(r['instrument'], r['target'], r['horizon']) for r in rows
                                      if r['scoring_status'] == 'scored'}),
        scored_with_baseline=sum(r['scoring_status'] == 'scored' and r['baseline_available'] for r in rows),
        metrics=weighted,
        metric_units='terminal_close normalized_error: original CSV display point/reference fraction; '
                     'paired_comparison: original unrounded estimates; whole_window_ohlc: terminal logreturn',
        weighting='equal origin dates, instruments, horizons, then correlated issuances')


def build_scorecard(analysis, analysis_sha, financial, snapshots, *, workflow_now):
    """Pure scoring over verified in-memory snapshots; workflow time never replaces review cutoff."""
    keys(analysis, ('schema_version', 'review_at', 'qualification_policy', 'cohorts'),
         ('status', 'qualification_disposition', 'interface_notes'))
    require(type(analysis['schema_version']) is int and analysis['schema_version'] == 1, 'analysis-schema')
    require(analysis['qualification_policy'] is None, 'unimplemented-qualification-policy')
    for field in ('status', 'qualification_disposition'):
        require(field not in analysis or type(analysis[field]) is str, 'analysis-metadata-schema')
    require('interface_notes' not in analysis or type(analysis['interface_notes']) is list
            and all(type(x) is str for x in analysis['interface_notes']), 'analysis-metadata-schema')
    cutoff = stamp(analysis['review_at'])
    require(cutoff <= workflow_now, 'future-review-cutoff')
    require(type(analysis['cohorts']) is list and 1 <= len(analysis['cohorts']) <= 16, 'cohort-budget')
    identifiers = [c['cohort_id'] for c in analysis['cohorts']]
    require(len(identifiers) == len(set(identifiers)) and all(type(x) is str
            and re.fullmatch('[A-Za-z0-9_-]{1,100}', x) for x in identifiers), 'cohort-id')
    financial_map = financial_binding(analysis, analysis_sha, financial, workflow_now)
    rows = []
    for cohort in analysis['cohorts']:
        require(cohort['kind'] in {'terminal_close_csv', 'saved_ohlc'}, 'unknown-target-adapter')
        adapter = terminal_rows if cohort['kind'] == 'terminal_close_csv' else ohlc_rows
        rows.extend(adapter(cohort, snapshots, financial_map[cohort['cohort_id']], cutoff))
        require(len(rows) <= MAX_ROWS, 'aggregate-forecast-row-budget')
    duplicates = Counter(r['forecast_id'] for r in rows)
    for row in rows:
        if duplicates[row['forecast_id']] > 1:
            failed(row, 'duplicate-original-forecast-id')
    target_counts = Counter((r['instrument'], r['target'], r['horizon']) for r in rows if r['target'])
    groups = {}
    for dimension, field in (('market', 'market'), ('horizon', 'horizon'), ('instrument', 'instrument')):
        groups[dimension] = {}
        for value in sorted({r[field] for r in rows}):
            selected = [r for r in rows if r[field] == value]
            groups[dimension][value] = {s: summarize([r for r in selected if r['target_semantics'] == s])
                for s in sorted({r['target_semantics'] for r in selected})}
    return dict(schema_version=1, kind='forecast-quality-scorecard', review_at=analysis['review_at'],
        qualification_policy=None, promotion=False, accuracy_is_not_profitability=True,
        summary={s: summarize([r for r in rows if r['target_semantics'] == s])
                 for s in sorted({r['target_semantics'] for r in rows})}, groups=groups, rows=rows,
        financial_review=dict(reviewed_at=financial['reviewed_at'], limitations=financial['limitations'],
                              cohorts=financial['cohorts']),
        correlated_vintages=[dict(instrument=k[0], target=k[1], horizon=k[2], issuances=n)
                             for k, n in sorted(target_counts.items()) if n > 1],
        limitations=['Descriptive private research only; no frozen qualification policy or promotion.',
            'Original CSV display-rounded terminal metrics are separate from unrounded original-audit paired metrics.',
            'Terminal ranges are not intraday extrema, endpoint bands or measured 95% confidence.',
            'Missing origin-time baselines remain missing; no hindsight reconstruction.',
            'Repeated issuances and tickers on one date are not independent date samples.',
            'Hash/receipt validation is not independent authentication of provider truth.',
            'Timing/RSS/provider-health telemetry is unavailable unless separately measured.'])


def safe_cell(value):
    if value is None:
        return ''
    if type(value) in (dict, list):
        value = json.dumps(value, sort_keys=True, allow_nan=False)
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + value
    return value


def render_csv(scorecard):
    fields = ['cohort_id', 'forecast_id', 'instrument', 'market', 'currency', 'origin', 'target', 'horizon',
        'issued_at', 'target_semantics', 'scoring_status', 'quality_status', 'baseline_available', 'baseline_present_at_origin',
        'actual_close', 'original_point', 'original_low', 'original_high', 'point_absolute_error',
        'point_error_fraction', 'terminal_range_hit', 'terminal_range_width', 'direction_hit', 'brier_score',
        'low_endpoint_error', 'high_endpoint_error', 'terminal_error', 'whole_window_containment',
        'model_metrics', 'baseline_metrics', 'baseline_comparison', 'unavailable_metrics', 'reasons']
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows({k: safe_cell(r.get(k)) for k in fields} for r in scorecard['rows'])
    return stream.getvalue().encode()


def render_html(scorecard):
    """Local report; all source text escaped, filters use textContent, no remote assets."""
    import base64
    esc = lambda value: html.escape(str(value), quote=True)
    numeric = lambda v: 'Unavailable' if v is None else format(v, '.6g')
    percent = lambda v: 'Unavailable' if v is None else format(v*100, '.4f')+'%'
    hit = lambda v: 'Unavailable' if v is None else 'Hit' if v else 'Miss'
    titles = {'terminal_close':'Original terminal-close cohort', 'whole_window_ohlc':'Saved OHLC forecasts'}
    all_counts = Counter(r['scoring_status'] for r in scorecard['rows'])
    cards = ''.join('<div class="count"><strong>'+str(all_counts[state])+'</strong><span>'+label+'</span></div>'
        for state, label in (('scored','Scored'),('pending','Pending'),('missing_actual','Missing actual'),
                             ('withheld','Withheld'),('invalid','Failed input')))
    financial = scorecard.get('financial_review', {})
    cohort_sections = []
    for semantics, summary in scorecard['summary'].items():
        counts = summary['counts']
        intraday = any(('intraday-issued' in text.lower() or 'intradayissued' in text.lower())
                      for c in financial.get('cohorts', []) if c['target_semantics'] == semantics
                      for text in c['limitations'])
        label = 'Intraday-issued closing forecasts · not pre-open forecasts' if intraday else titles[semantics]
        scored, mature = counts.get('scored',0), summary['mature_generated_targets']
        denominator = str(scored)+' / '+str(mature)
        pairs = summary['paired_comparison']
        pair_html = ''
        if pairs:
            pair_html = ('<div class="comparison"><div><span>Model normalized absolute error</span><strong>'
                +percent(pairs['model_mean_absolute_error_fraction'])+'</strong></div><div>'
                '<span>Original baseline normalized absolute error</span><strong>'
                +percent(pairs['baseline_mean_absolute_error_fraction'])+'</strong></div></div>'
                '<p class="small">'+str(pairs['pairs'])+' matched pairs · both use original unrounded estimates. '
                'Error is |point − actual close| ÷ reference close. Lower is smaller error, not evidence of profit or edge.</p>'
                '<p class="small">Paired sample: '+str(pairs['distinct_origin_dates'])+' distinct origin dates / '
                +str(pairs['distinct_instrument_targets'])+' distinct instrument-targets. Grouped terminal interval hit rates: model '
                +percent(pairs['model_weighted_range_hit_rate'])+'; baseline '+percent(pairs['baseline_weighted_range_hit_rate'])+'. '
                'Raw hit counts (diagnostic): model '+str(pairs['model_range_hits'])+' / '+str(pairs['pairs'])
                +'; baseline '+str(pairs['baseline_range_hits'])+' / '+str(pairs['pairs'])+'.</p>')
        elif counts.get('pending'):
            pair_html = '<p>Outcome metrics are pending until each complete window ends and reviewed actuals are available.</p>'
        else:
            pair_html = '<p>Matched comparison unavailable. See each original row for its exact reason.</p>'
        display = ''
        if semantics == 'terminal_close' and scored:
            matching = [r for r in scorecard['rows'] if r['target_semantics']==semantics and r['scoring_status']=='scored']
            direction = [r['direction_hit'] for r in matching if r['direction_hit'] is not None]
            ranges = [r['terminal_range_hit'] for r in matching if r['terminal_range_hit'] is not None]
            display = ('<p><b>Original CSV display outcomes:</b> direction '+str(sum(direction))+' / '+str(len(direction))
                +'; inclusive closing interval '+str(sum(ranges))+' / '+str(len(ranges))+'. '
                'These are closing outcomes, not intraday extremes or a calibration claim.</p>')
        cohort_sections.append('<section class="panel"><div class="section-heading"><h2>'+esc(titles[semantics])
            +'</h2><span class="badge">No quality qualification</span></div><p class="scope">'+esc(label)+'</p>'
            '<div class="facts"><div><strong>'+denominator+'</strong><span>scored / mature generated targets</span></div>'
            '<div><strong>'+str(summary['scored_origin_dates'])+'</strong><span>scored origin dates</span></div>'
            '<div><strong>'+str(summary['distinct_instruments'])+'</strong><span>identities retained</span></div></div>'
            '<p class="small">'+str(summary['issuances'])+' rows retained, including withheld entries. Pending: '
            +str(counts.get('pending',0))+' · missing actual: '+str(counts.get('missing_actual',0))+' · withheld: '
            +str(counts.get('withheld',0))+' · failed: '+str(counts.get('invalid',0))+'. Withheld rows are not forecasts.</p>'
            +pair_html+display+'<p class="caution">'+('One target session; names are correlated. ' if summary['scored_origin_dates']==1 else '')
            +'Frozen qualification policy is null. Descriptive results do not establish calibrated accuracy or justify promotion.</p></section>')
    table = []
    for r in scorecard['rows']:
        if r['target_semantics']=='terminal_close':
            prediction = 'Point '+numeric(r.get('original_point'))+'; closing interval '+numeric(r.get('original_low'))+'–'+numeric(r.get('original_high'))
            actual = numeric(r.get('actual_close'))
        else:
            prediction = 'Window median low '+numeric(r.get('original_low'))+' / high '+numeric(r.get('original_high'))+'; terminal median '+numeric(r.get('original_point'))
            actual = ('Low '+numeric(r.get('actual_low'))+' / high '+numeric(r.get('actual_high'))+'; close '+numeric(r.get('actual_close'))
                      if r['scoring_status']=='scored' else 'Unavailable')
        cells = (r['instrument'], (r['target'] or 'No target')+' / '+r['horizon'], r['target_semantics'],
            prediction+' '+str(r['currency'] or ''), actual, r['scoring_status'],
            hit(r['direction_hit']), hit(r['terminal_range_hit']), '; '.join(r['reasons']))
        attrs = ''.join(' data-'+name+'="'+esc(r[field])+'"' for name,field in
                        (('status','scoring_status'),('horizon','horizon'),('semantics','target_semantics')))
        table.append('<tr'+attrs+'>'+''.join('<td>'+esc(c)+'</td>' for c in cells)+'</tr>')
    def options(field):
        return '<option value="">All</option>'+''.join('<option value="'+esc(v)+'">'+esc(v)+'</option>'
            for v in sorted({r[field] for r in scorecard['rows']}))
    filters = ('<div class="filters"><label>Search instrument, target or reason<input id="search" type="search" '
        'placeholder="For example: US.SPY or missing" autocomplete="off"></label>'
        '<label>Status<select id="status">'+options('scoring_status')+'</select></label>'
        '<label>Horizon<select id="horizon">'+options('horizon')+'</select></label>'
        '<label>Target semantics<select id="semantics">'+options('target_semantics')+'</select></label>'
        '<button id="reset" type="button">Reset filters</button></div>')
    findings = '<details><summary>Financial review and source limitations</summary>'
    for cohort in financial.get('cohorts', []):
        findings += '<h3>'+esc(cohort['cohort_id'])+'</h3><ul>'+''.join(
            '<li>'+esc(value)+'</li>' for value in cohort['limitations'])+'</ul>'
    findings += '</details><details><summary>Technical summaries and sample weighting</summary><pre>'+esc(
        json.dumps(scorecard['summary'],indent=2))+'</pre></details>'
    script = """'use strict';
const rows=Array.from(document.querySelectorAll('tbody tr'));
const controls=['search','status','horizon','semantics'].map(id=>document.getElementById(id));
function filterRows(){let count=0;const query=controls[0].value.toLowerCase().trim();
for(const row of rows){const show=(!query||row.textContent.toLowerCase().includes(query))&&
(!controls[1].value||row.dataset.status===controls[1].value)&&
(!controls[2].value||row.dataset.horizon===controls[2].value)&&
(!controls[3].value||row.dataset.semantics===controls[3].value);
row.hidden=!show;if(show)count++;}
document.getElementById('shown').textContent='Showing '+count+' of '+rows.length+' original rows';}
for(const control of controls)control.addEventListener('input',filterRows);
document.getElementById('reset').addEventListener('click',()=>{for(const control of controls)control.value='';filterRows();});
filterRows();"""
    script_hash = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    csp = "default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-"+script_hash+"'; base-uri 'none'; form-action 'none'"
    style = """*{box-sizing:border-box}body{margin:0;background:#f3f5f8;color:#17283b;font:15px/1.5 system-ui,sans-serif}
main{max-width:1240px;margin:auto;padding:36px 24px}h1{font-size:32px;line-height:1.15;margin:8px 0 16px}h2{font-size:21px;margin:0}h3{font-size:16px}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#52667d;font-weight:700}.subtitle,.small{color:#526174}.small{font-size:13px}
.counts{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:24px 0}.count,.panel{background:white;border:1px solid #dbe2ea;border-radius:12px}
.count{padding:16px}.count strong{display:block;font-size:28px;font-weight:650}.count span{color:#526174}.panel{padding:24px;margin:18px 0}.section-heading{display:flex;gap:16px;justify-content:space-between;align-items:start}
.badge{background:#edf1f5;padding:5px 10px;border-radius:20px;font-size:12px;white-space:nowrap}.scope{font-weight:600;color:#526174;margin-top:8px}.facts{display:flex;gap:42px;flex-wrap:wrap;margin:20px 0}.facts strong{display:block;font-size:23px}.facts span,.comparison span{display:block;font-size:13px;color:#526174}
.comparison{display:grid;grid-template-columns:1fr 1fr;gap:16px;background:#f4f6f9;padding:16px;border-radius:8px}.comparison strong{font-size:25px}.caution{border-left:3px solid #a97926;padding:8px 14px;background:#fff9ee;font-size:13px}
.downloads{display:flex;flex-wrap:wrap;gap:10px}.downloads a,button{display:inline-block;padding:9px 13px;background:white;border:1px solid #bdcbd9;border-radius:7px;color:#203c57;text-decoration:none;font:inherit}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #327eb8;outline-offset:2px}
.filters{display:grid;grid-template-columns:2fr 1fr 1fr 1.3fr auto;gap:12px;align-items:end;margin:20px 0 12px}label{font-size:12px;font-weight:650}input,select{display:block;width:100%;padding:10px;margin-top:5px;border:1px solid #b9c7d5;border-radius:6px;background:white;font:14px system-ui;color:#17283b}
.table-scroll{overflow:auto;border:1px solid #dbe2ea;border-radius:8px;max-height:680px}table{border-collapse:collapse;min-width:1100px;width:100%;font-size:13px}caption{text-align:left;padding:12px;background:#f3f6fa;color:#526174}th,td{padding:12px;border-bottom:1px solid #e2e8ef;text-align:left;vertical-align:top}th{position:sticky;top:0;background:#edf2f7;z-index:1}td:nth-child(4){min-width:205px}td:last-child{min-width:240px}tr[hidden]{display:none}tbody tr:nth-child(even){background:#fafbfd}
details{background:white;border:1px solid #dbe2ea;padding:16px;margin:14px 0;border-radius:10px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}li{margin:8px 0}.footer{font-size:12px;color:#526174;margin:24px 0}
@media(max-width:760px){main{padding:24px 14px}h1{font-size:27px}.counts{grid-template-columns:repeat(3,1fr)}.count{padding:12px}.panel{padding:16px}.section-heading{display:block}.badge{display:inline-block;margin-top:10px}.comparison{grid-template-columns:1fr}.filters{grid-template-columns:1fr 1fr}.filters label:first-child{grid-column:1/-1}.facts{gap:20px}.downloads a{font-size:13px}}"""
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="'+esc(csp)+'"><title>Forecast quality scorecard</title><style>'+style+'</style></head><body><main>'
        '<header><div class="eyebrow">Praesagus · private research</div><h1>Forecast quality scorecard</h1>'
        '<p class="subtitle">What the original forecasts said, what happened, and what remains unknown.</p>'
        '<p class="small">Frozen outcome cutoff: <b>'+esc(scorecard['review_at'])+'</b>. Later review workflow does not move this cutoff.</p></header>'
        '<div class="counts" aria-label="All original row statuses">'+cards+'</div>'
        '<nav class="downloads" aria-label="Download evidence"><a href="scorecard.csv" download>Download rows · CSV</a>'
        '<a href="scorecard.json" download>Full scorecard · JSON</a><a href="provenance.json" download>Input provenance · JSON</a></nav>'
        +''.join(cohort_sections)+'<section class="panel"><h2>Original rows</h2><p class="small">Terminal point/range columns retain original CSV display precision. '
        'OHLC rows show separate window medians; they are not closing intervals. Unavailable values are never zero-filled.</p>'+filters
        +'<p id="shown" aria-live="polite">Showing '+str(len(scorecard['rows']))+' original rows</p>'
        '<div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable original forecast rows"><table>'
        '<caption>All original identities retained, including pending, missing and withheld rows</caption><thead><tr>'
        +''.join('<th scope="col">'+esc(x)+'</th>' for x in ('Instrument','Target / horizon','Semantics','Original prediction',
            'Actual outcome','Status','Direction outcome','Closing range outcome','Exact reason'))
        +'</tr></thead><tbody>'+''.join(table)+'</tbody></table></div></section>'+findings
        +'<details><summary>General interpretation limits</summary><ul>'+''.join('<li>'+esc(x)+'</li>' for x in scorecard['limitations'])
        +'</ul></details><p class="footer">No provider calls, model training, prediction or promotion. Readiness and descriptive scores are separate from validated performance.</p>'
        '</main><script>'+script+'</script></body></html>').encode()


def run(bundle_path, bundle_sha, output_parent):
    raw = private_read(bundle_path)
    require(sha(raw) == bundle_sha, 'bundle-hash-mismatch')
    bundle = decode(raw)
    keys(bundle, ('schema_version', 'kind', 'analysis', 'financial_review'))
    require(type(bundle['schema_version']) is int and bundle['schema_version'] == 1
            and bundle['kind'] == 'quality-scorecard-inputs', 'bundle-schema')
    snapshots = Snapshots()
    analysis = snapshots.document(bundle['analysis'])
    financial = snapshots.document(bundle['financial_review'])
    scorecard = build_scorecard(analysis, bundle['analysis']['sha256'], financial, snapshots,
                               workflow_now=datetime.now(timezone.utc))
    output = private_path(output_parent, directory=True)
    require(not output.is_relative_to(ROOT) and output != Path.home() and len(output.parts) >= 4,
            'output-must-be-narrow-private-outside-repository')
    # Recheck bytes and permissions, preserving all source files, before any output.
    for path, original in snapshots.raw.items():
        require(private_read(path) == original, 'input-changed-during-review')
    require(private_read(bundle_path) == raw, 'bundle-changed-during-review')
    provenance = dict(bundle={'path':str(Path(bundle_path)), 'sha256':bundle_sha, 'bytes':len(raw)},
        input_refs=sorted(snapshots.refs.values(), key=lambda r:r['path']),
        code_sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in
            (Path(__file__), ROOT/'harness/forecast_review.py', *[ROOT/'scripts/stock-research'/name
            for name in ('evaluation.py', 'data.py', 'storage.py', 'market_calendar.py', 'inference.py', 'model.py')])},
        runtime_versions=dict(python=sys.version.split()[0], numpy=version('numpy'),
                              exchange_calendars=version('exchange_calendars')),
        operations=dict(provider_calls=0, fit=False, prediction=False, model_artifact_loaded=False),
        telemetry=dict(wall_seconds=None, peak_RSS_bytes=None),
        output_policy='Exclusive private output; identical bound inputs yield identical report bytes.')
    artifacts = {'scorecard.json':canonical(scorecard)+b'\n', 'scorecard.csv':render_csv(scorecard),
                 'scorecard.html':render_html(scorecard), 'provenance.json':canonical(provenance)+b'\n'}
    require(sum(map(len, artifacts.values())) <= 32*1024**2, 'output-budget')
    folder = output/('scorecard-'+bundle_sha[:20])
    require(all(not Path(p).is_relative_to(folder) for p in snapshots.raw), 'output-overlaps-inputs')
    folder.mkdir(mode=0o700, exist_ok=False)
    for name, content in artifacts.items():
        fd = os.open(folder/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as target:
            target.write(content)
    return dict(status='scorecard-written', folder=str(folder), summary=scorecard['summary'],
        artifacts={name:dict(sha256=sha(raw), bytes=len(raw)) for name, raw in artifacts.items()})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--bundle-sha256', required=True)
    parser.add_argument('--output-parent', required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run(args.bundle, args.bundle_sha256, args.output_parent), allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, csv.Error, OverflowError) as error:
        print(json.dumps(dict(status='blocked', reason=str(error)), allow_nan=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
