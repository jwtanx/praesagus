"""Pure synthetic arithmetic; no source admission, I/O or predictive certification."""
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
import math
import re

ROOT = {'schema_version', 'synthetic', 'classification', 'contract', 'scheduled_total',
        'schedule', 'opportunities', 'forecast_bindings', 'outcome_bindings'}
CONTRACT = {'cohort_id', 'instrument_id', 'market', 'mic', 'currency', 'unit', 'basis',
            'value_semantics', 'scale_id', 'calendar_version', 'instrument_version',
            'method_id', 'method_version', 'interval_baseline_id', 'horizon_sessions', 'alpha'}
SCHEDULE = {'opportunity_id', 'target_session', 'target_close_at', 'scheduled_at'}
OPPORTUNITY = {'disposition', 'decision_at', 'reason_code', 'forecast', 'outcome'}
FORECAST = {'opportunity_id', 'contract_sha256', 'issued_at', 'forecast_vintage',
            'reference_session', 'reference_close_at', 'reference_known_at', 'prior_close_at',
            'prior_known_at', 'reference', 'prior_close', 'candidate_point',
            'candidate_direction', 'baseline_direction', 'candidate_interval',
            'baseline_interval', 'interval_construction'}
OUTCOME = {'kind', 'opportunity_id', 'contract_sha256', 'forecast_sha256', 'outcome_vintage',
           'scale_id', 'close_at', 'available_at', 'known_at', 'actual'}
UNAVAILABLE = {'kind', 'reason_code', 'known_at'}
DIRECTIONS = {'up', 'down', 'flat', 'abstain'}
LIMITATIONS = (
    'synthetic arithmetic only',
    'no scheduler completeness/calendar/source/rights verification',
    'hashes do not prove historical possession',
    'authored interval construction not verified',
    'direction authored independently of candidate_point',
    'no calibration/significance/promotion',
    'adjusted series is not an executable target',
)
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}', re.ASCII)
SHA = re.compile(r'[0-9a-f]{64}', re.ASCII)
DAY = re.compile(r'\d{4}-\d{2}-\d{2}', re.ASCII)
INSTANT = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z', re.ASCII)
MAX_OPPORTUNITIES = 1000
MAX_VALUES = 250000
MAX_DEPTH = 8
MAX_STRING = 128


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _budget(value):
    """Iterative, bounded walk also rejects cycles without recursing into them."""
    stack, visited, reasons = [(value, 0)], 0, set()
    while stack:
        item, depth = stack.pop()
        visited += 1
        if visited > MAX_VALUES or depth > MAX_DEPTH:
            return {'resource_limit'}
        kind = type(item)
        if kind not in (dict, list, str, int, float, bool, type(None)):
            reasons.add('schema')
        elif kind is str:
            if len(item) > MAX_STRING:
                reasons.add('resource_limit')
        elif kind in (dict, list):
            count = len(item) * (2 if kind is dict else 1)
            if count > MAX_VALUES - visited - len(stack):
                return {'resource_limit'}
            if kind is dict:
                for key, child in item.items():
                    if type(key) is not str:
                        reasons.add('schema')
                    stack.append((key, depth + 1))
                    stack.append((child, depth + 1))
            else:
                stack.extend((child, depth + 1) for child in item)
    # Budget precedes type/schema checks; over-budget inputs are never partially walked.
    return {'resource_limit'} if 'resource_limit' in reasons else reasons


def _object(value, keys):
    return type(value) is dict and set(value) == keys


def _strings(value, fields):
    return all(type(value[field]) is str for field in fields)


def _schema(packet):
    if not _object(packet, ROOT):
        return {'schema'}
    if (type(packet['schema_version']) is not int or type(packet['synthetic']) is not bool
            or type(packet['classification']) is not str or type(packet['scheduled_total']) is not int
            or type(packet['schedule']) is not list
            or any(type(packet[k]) is not dict for k in ('opportunities', 'forecast_bindings', 'outcome_bindings'))):
        return {'schema'}
    reasons = set()
    contract = packet['contract']
    if not _object(contract, CONTRACT) or not _strings(contract, CONTRACT - {'alpha', 'horizon_sessions'}):
        reasons.add('schema')
    elif type(contract['horizon_sessions']) is not int:
        reasons.add('schema')
    if len(packet['schedule']) > MAX_OPPORTUNITIES:
        reasons.add('resource_limit')
    for scheduled in packet['schedule']:
        if not _object(scheduled, SCHEDULE) or not _strings(scheduled, SCHEDULE):
            reasons.add('schema')
    for bindings in (packet['forecast_bindings'], packet['outcome_bindings']):
        if not all(type(v) is str for v in bindings.values()):
            reasons.add('schema')
    for opportunity in packet['opportunities'].values():
        if not _object(opportunity, OPPORTUNITY):
            reasons.add('schema')
            continue
        if not _strings(opportunity, {'disposition', 'decision_at'}):
            reasons.add('schema')
        if opportunity['reason_code'] is not None and type(opportunity['reason_code']) is not str:
            reasons.add('schema')
        forecast = opportunity['forecast']
        if forecast is not None:
            if not _object(forecast, FORECAST):
                reasons.add('schema')
            else:
                strings = FORECAST - {'reference', 'prior_close', 'candidate_point',
                                      'candidate_interval', 'baseline_interval'}
                if not _strings(forecast, strings):
                    reasons.add('schema')
                for name in ('candidate_interval', 'baseline_interval'):
                    if not _object(forecast[name], {'low', 'high'}):
                        reasons.add('schema')
        outcome = opportunity['outcome']
        if outcome is not None:
            if type(outcome) is not dict:
                reasons.add('schema')
            elif outcome.get('kind') == 'eligible':
                if not _object(outcome, OUTCOME) or not _strings(outcome, OUTCOME - {'actual'}):
                    reasons.add('schema')
            elif outcome.get('kind') == 'unavailable':
                if not _object(outcome, UNAVAILABLE) or not _strings(outcome, UNAVAILABLE):
                    reasons.add('schema')
            else:
                reasons.add('schema')
    return reasons


def _instant(value):
    if type(value) is not str or not INSTANT.fullmatch(value):
        raise ValueError
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _day(value):
    if not DAY.fullmatch(value):
        raise ValueError
    return date.fromisoformat(value)


def _number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and 1e-100 <= value <= 1e100
    except OverflowError:
        return False


def _format_stage(packet, review_at):
    """Parse times once and collect contract/domain errors without input mutation."""
    reasons, times, days = set(), {}, {}

    def instant(value):
        try:
            times[value] = _instant(value)
        except (ValueError, TypeError):
            reasons.add('timestamp')

    def day(value):
        try:
            days[value] = _day(value)
        except ValueError:
            reasons.add('timestamp')

    def identifier(value):
        if not ID.fullmatch(value):
            reasons.add('contract')

    def number(value):
        if not _number(value):
            reasons.add('numeric_domain')

    instant(review_at)
    c = packet['contract']
    for field in ('cohort_id', 'instrument_id', 'scale_id', 'calendar_version',
                  'instrument_version', 'method_id', 'method_version'):
        identifier(c[field])
    if (c['market'] != 'US' or not re.fullmatch(r'[A-Z0-9]{4}', c['mic'], re.ASCII)
            or not re.fullmatch(r'[A-Z]{3}', c['currency'], re.ASCII)
            or c['unit'] not in {'price_unit', 'series_unit'}
            or c['basis'] not in {'unadjusted', 'split_adjusted', 'total_return_adjusted'}
            or c['interval_baseline_id'] != 'authored_zero_drift_interval_v1'
            or c['horizon_sessions'] != 1):
        reasons.add('contract')
    total_return = c['basis'] == 'total_return_adjusted'
    if (c['value_semantics'] != ('total_return_series' if total_return else 'traded_close_series')
            or total_return and c['unit'] != 'series_unit'):
        reasons.add('contract')
    alpha = c['alpha']
    if type(alpha) not in (int, float):
        reasons.add('numeric_domain')
    else:
        try:
            if not math.isfinite(alpha):
                reasons.add('numeric_domain')
            elif alpha != .05:
                reasons.add('contract')
        except OverflowError:
            reasons.add('numeric_domain')
    for s in packet['schedule']:
        identifier(s['opportunity_id'])
        day(s['target_session'])
        instant(s['scheduled_at']); instant(s['target_close_at'])
    for key, o in packet['opportunities'].items():
        identifier(key)
        instant(o['decision_at'])
        f = o['forecast']
        if f is not None:
            identifier(f['opportunity_id']); identifier(f['forecast_vintage'])
            day(f['reference_session'])
            for field in ('issued_at', 'reference_close_at', 'reference_known_at', 'prior_close_at', 'prior_known_at'):
                instant(f[field])
            for field in ('reference', 'prior_close', 'candidate_point'):
                number(f[field])
            for field in ('candidate_interval', 'baseline_interval'):
                number(f[field]['low']); number(f[field]['high'])
        actual = o['outcome']
        if actual is not None:
            instant(actual['known_at'])
            if actual['kind'] == 'eligible':
                for field in ('opportunity_id', 'outcome_vintage', 'scale_id'):
                    identifier(actual[field])
                instant(actual['close_at']); instant(actual['available_at'])
                number(actual['actual'])
    for bindings in (packet['forecast_bindings'], packet['outcome_bindings']):
        for key in bindings:
            identifier(key)
    return reasons, times, days


def _schedule_stage(packet, now, times):
    reasons, ids, targets = set(), set(), set()
    for s in packet['schedule']:
        if s['opportunity_id'] in ids or s['target_session'] in targets:
            reasons.add('schedule_identity')
        ids.add(s['opportunity_id']); targets.add(s['target_session'])
        if times[s['scheduled_at']] > now:
            reasons.add('schedule_not_due')
        if times[s['scheduled_at']] >= times[s['target_close_at']]:
            reasons.add('schedule_identity')
    if (packet['scheduled_total'] != len(packet['schedule'])
            or not 0 <= packet['scheduled_total'] <= MAX_OPPORTUNITIES
            or ids != set(packet['opportunities'])):
        reasons.add('schedule_membership')
    return reasons


def _forecast_stage(packet, now, times, days):
    reasons, issued = set(), set()
    contract_hash = _digest(packet['contract'])
    for s in packet['schedule']:
        key = s['opportunity_id']; o = packet['opportunities'][key]
        decision = times[o['decision_at']]
        if not times[s['scheduled_at']] <= decision <= now:
            reasons.add('opportunity_state')
        if o['disposition'] in ('source_gate_abstention', 'issuance_failure'):
            expected = ('synthetic_source_blocked' if o['disposition'] == 'source_gate_abstention'
                        else 'synthetic_issuance_failed')
            if o['reason_code'] != expected or o['forecast'] is not None or o['outcome'] is not None:
                reasons.add('opportunity_state')
            continue
        if o['disposition'] != 'issued' or o['forecast'] is None or o['reason_code'] is not None:
            reasons.add('opportunity_state')
            continue
        issued.add(key); f = o['forecast']
        target = times[s['target_close_at']]
        if (times[f['issued_at']] != decision or decision >= target
                or days[f['reference_session']] >= days[s['target_session']]
                or not times[f['reference_close_at']] < target
                or not times[f['reference_close_at']] <= times[f['reference_known_at']] <= decision
                or not times[f['prior_close_at']] < times[f['reference_close_at']]
                or not times[f['prior_close_at']] <= times[f['prior_known_at']] <= decision):
            reasons.add('forecast_time')
        if (f['opportunity_id'] != key or f['contract_sha256'] != contract_hash
                or not SHA.fullmatch(f['contract_sha256'])):
            reasons.add('forecast_binding')
        if (f['candidate_direction'] not in DIRECTIONS or f['baseline_direction'] not in DIRECTIONS
                or f['interval_construction'] != 'authored_not_verified'
                or any(f[name]['low'] > f[name]['high'] for name in ('candidate_interval', 'baseline_interval'))):
            reasons.add('opportunity_state')
        expected = ('up' if f['reference'] > f['prior_close'] else
                    'down' if f['reference'] < f['prior_close'] else 'abstain')
        if f['baseline_direction'] != expected:
            reasons.add('baseline_direction')
    # Forecast digest checks belong to the subsequent outcome/bindings stage.
    return reasons, issued, contract_hash


def _outcome_stage(packet, now, times, issued, contract_hash):
    reasons, eligible = set(), set()
    fb, ob = packet['forecast_bindings'], packet['outcome_bindings']
    if set(fb) != issued:
        reasons.add('forecast_binding')
    for key in sorted(issued):
        f = packet['opportunities'][key]['forecast']
        if key not in fb or not SHA.fullmatch(fb[key]) or fb[key] != _digest(f):
            reasons.add('forecast_binding')
    for s in packet['schedule']:
        key = s['opportunity_id']
        if key not in issued:
            continue
        outcome = packet['opportunities'][key]['outcome']
        if outcome is None:
            continue
        target = times[s['target_close_at']]
        if now < target:
            reasons.add('outcome_time')
        if outcome['kind'] == 'unavailable':
            if (outcome['reason_code'] not in {'absent', 'ineligible'}
                    or not target <= times[outcome['known_at']] <= now):
                reasons.add('outcome_time')
            continue
        eligible.add(key)
        if (outcome['opportunity_id'] != key or outcome['contract_sha256'] != contract_hash
                or outcome['forecast_sha256'] != fb.get(key)
                or not SHA.fullmatch(outcome['contract_sha256'])
                or not SHA.fullmatch(outcome['forecast_sha256'])):
            reasons.add('outcome_binding')
        if outcome['scale_id'] != packet['contract']['scale_id']:
            reasons.add('outcome_scale')
        if (times[outcome['close_at']] != target
                or not target <= times[outcome['available_at']] <= times[outcome['known_at']] <= now):
            reasons.add('outcome_time')
        if key not in ob or not SHA.fullmatch(ob[key]) or ob[key] != _digest(outcome):
            reasons.add('outcome_binding')
    if set(ob) != eligible:
        reasons.add('outcome_binding')
    return reasons


def _log_return(value, reference):
    if reference / 2 <= value <= 2 * reference:
        return 100 * math.log1p((value - reference) / reference)
    return 100 * (math.log(value) - math.log(reference))


def _interval(bounds, actual, reference):
    low, high = bounds['low'], bounds['high']
    width = high - low
    lower, upper = actual < low, actual > high
    return dict(covered=low <= actual <= high, lower_miss=lower, upper_miss=upper,
                normalized_width=width / reference,
                interval_score=width + (40 * (low - actual) if lower else
                                        40 * (actual - high) if upper else 0))


def _losses(f, actual):
    reference = f['reference']
    realized = _log_return(actual, reference)
    candidate_log = abs(_log_return(f['candidate_point'], reference) - realized)
    baseline_log = abs(realized)

    def hit(direction):
        return (actual > reference if direction == 'up' else actual < reference
                if direction == 'down' else None)

    return dict(candidate_log_absolute=candidate_log, baseline_log_absolute=baseline_log,
                log_loss_delta=candidate_log - baseline_log,
                candidate_absolute=abs(f['candidate_point'] - actual), baseline_absolute=abs(reference - actual),
                candidate_direction_hit=hit(f['candidate_direction']), baseline_direction_hit=hit(f['baseline_direction']),
                realized_zero=actual == reference,
                candidate_interval=_interval(f['candidate_interval'], actual, reference),
                baseline_interval=_interval(f['baseline_interval'], actual, reference))


def _fraction(numerator, denominator):
    return numerator / denominator if denominator else None


def _aggregate(losses):
    count = len(losses)

    def mean(field):
        return math.fsum(row[field] for row in losses) / count if count else None

    def rmse(field):
        return math.sqrt(math.fsum(row[field] ** 2 for row in losses) / count) if count else None

    point = dict(paired_count=count, candidate_log_mae=mean('candidate_log_absolute'),
                 baseline_log_mae=mean('baseline_log_absolute'), mean_log_loss_delta=mean('log_loss_delta'),
                 candidate_mae=mean('candidate_absolute'), baseline_mae=mean('baseline_absolute'),
                 candidate_rmse=rmse('candidate_absolute'), baseline_rmse=rmse('baseline_absolute'))
    direction = {}
    for method in ('candidate', 'baseline', 'matched'):
        if method == 'matched':
            rows = [row for row in losses if row['candidate_direction_hit'] is not None
                    and row['baseline_direction_hit'] is not None]
        else:
            rows = [row for row in losses if row[method + '_direction_hit'] is not None]
        n = len(rows)
        if method == 'matched':
            hits = {name: sum(row[name + '_direction_hit'] for row in rows) for name in ('candidate', 'baseline')}
            hit_fraction = {name: hits[name] / n for name in hits} if n else None
        else:
            hits = sum(row[method + '_direction_hit'] for row in rows)
            hit_fraction = _fraction(hits, n)
        direction[method] = dict(eligible_count=n, hits=hits,
                                 realized_zero_count=sum(row['realized_zero'] for row in rows),
                                 hit_fraction=hit_fraction, coverage_fraction=_fraction(n, count))
    interval = {'paired_count': count}
    for method in ('candidate', 'baseline'):
        rows = [row[method + '_interval'] for row in losses]
        covered = sum(row['covered'] for row in rows)
        interval[method] = dict(covered=covered, lower_misses=sum(row['lower_miss'] for row in rows),
                                upper_misses=sum(row['upper_miss'] for row in rows),
                                coverage_fraction=_fraction(covered, count),
                                mean_normalized_width=math.fsum(row['normalized_width'] for row in rows) / count if count else None,
                                mean_interval_score=math.fsum(row['interval_score'] for row in rows) / count if count else None)
    return dict(point=point, direction=direction, interval=interval)


def _finite(value):
    if type(value) in (dict, list):
        return all(_finite(child) for child in (value.values() if type(value) is dict else value))
    return type(value) not in (int, float) or math.isfinite(value)


def score_cohort(packet, *, review_at):
    """Score only a bounded, explicitly synthetic due-set at an explicit UTC instant.

    Invalid packets return fixed reasons and no partial counts or metrics. Binding
    hashes check caller-authored consistency, never historical possession/rights.
    """
    result = dict(schema_version=1, synthetic_only=True, classification='synthetic_only',
                  source_eligibility='not_assessed', rights_status='unverified', invalid=True,
                  review_at=None, contract=None, reasons=[], counts=None, operational=None,
                  metrics=None, rows=[], limitations=list(LIMITATIONS))
    try:
        result['review_at'] = review_at if _instant(review_at) else None
    except (ValueError, TypeError):
        pass

    def invalid(reasons):
        result['reasons'] = sorted(reasons)
        return result

    reasons = _budget(packet) | _budget(review_at)
    if not reasons:
        reasons = _schema(packet)
    if reasons:
        return invalid(reasons)
    reasons = set()
    if packet['schema_version'] != 1:
        reasons.add('unsupported_version')
    if packet['synthetic'] is not True or packet['classification'] != 'synthetic_only':
        reasons.add('not_synthetic')
    if reasons:
        return invalid(reasons)
    reasons, times, days = _format_stage(packet, review_at)
    if reasons:
        return invalid(reasons)
    now = times[review_at]
    reasons = _schedule_stage(packet, now, times)
    if reasons:
        return invalid(reasons)
    reasons, issued, contract_hash = _forecast_stage(packet, now, times, days)
    if reasons:
        return invalid(reasons)
    reasons = _outcome_stage(packet, now, times, issued, contract_hash)
    if reasons:
        return invalid(reasons)
    try:
        rows, losses = [], []
        counts = dict.fromkeys(('scheduled', 'source_gate_abstention', 'issuance_failure', 'issued_pending',
                                'mature_missing_outcome', 'scored', 'issued', 'mature_issued'), 0)
        counts['scheduled'] = len(packet['schedule'])
        for s in sorted(packet['schedule'], key=lambda item: (item['target_session'], item['opportunity_id'])):
            key = s['opportunity_id']; o = packet['opportunities'][key]
            state, missing, loss = o['disposition'], None, None
            if state == 'issued':
                if now < times[s['target_close_at']]:
                    state = 'issued_pending'
                elif o['outcome'] is None or o['outcome']['kind'] == 'unavailable':
                    state = 'mature_missing_outcome'
                    missing = o['outcome']['reason_code'] if o['outcome'] else 'absent'
                else:
                    state = 'scored'
                    loss = _losses(o['forecast'], o['outcome']['actual'])
                    losses.append(loss)
            counts[state] += 1
            rows.append(dict(opportunity_id=key, target_session=s['target_session'], state=state,
                             missing_reason=missing, forecast_sha256=packet['forecast_bindings'].get(key),
                             outcome_sha256=packet['outcome_bindings'].get(key) if state == 'scored' else None,
                             losses=loss))
        counts['issued'] = counts['issued_pending'] + counts['mature_missing_outcome'] + counts['scored']
        counts['mature_issued'] = counts['mature_missing_outcome'] + counts['scored']
        operational = {
            'issuance_coverage': dict(numerator=counts['issued'], denominator=counts['scheduled'],
                                      fraction=_fraction(counts['issued'], counts['scheduled'])),
            'outcome_completion': dict(numerator=counts['scored'], denominator=counts['mature_issued'],
                                       fraction=_fraction(counts['scored'], counts['mature_issued'])),
        }
        metrics = _aggregate(losses)
        if not _finite(rows) or not _finite(metrics):
            return invalid({'numeric_overflow'})
        candidate = dict(result, invalid=False, contract={key: deepcopy(packet['contract'][key]) for key in sorted(CONTRACT)}, counts=counts,
                         operational=operational, metrics=metrics, rows=rows)
        json.dumps(candidate, allow_nan=False)
        return candidate
    except (OverflowError, ValueError):
        return invalid({'numeric_overflow'})
