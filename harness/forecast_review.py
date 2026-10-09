"""Deterministic, offline review of frozen forecast CSV rows."""
import argparse
import csv
from collections import Counter
from datetime import date, datetime
import json
import math
from pathlib import Path
import re

REQUIRED = {
    'forecast_id', 'report_date', 'as_of', 'horizon_type', 'market', 'venue', 'ticker',
    'reference_close_date', 'reference_close', 'reference_source',
    'forecast_target_date', 'forecast_direction', 'forecast_range_low',
    'forecast_range_high', 'probability_up', 'actual_close_date',
    'actual_close', 'actual_source', 'status', 'scoring_notes',
}
STATUSES = {'pending', 'scored', 'not_scored', 'abstain', 'data_unavailable'}
DIRECTIONS = {'up', 'down', 'flat', 'sideways', 'abstain', 'data_unavailable'}


def aware_timestamp(value, field='as_of'):
    if not isinstance(value, str):
        raise ValueError(field + ' must include a timezone offset')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError(field + ' must be a valid ISO datetime') from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(field + ' must include a timezone offset')
    return parsed


def iso_date(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('date must use YYYY-MM-DD')
    return date.fromisoformat(value)


def number(value, field, probability=False):
    parsed = float(value)
    if not math.isfinite(parsed) or (not probability and parsed <= 0):
        raise ValueError(field + ' must be finite and positive')
    if probability and not 0 <= parsed <= 1:
        raise ValueError(field + ' must be finite and between 0 and 1')
    return parsed


def evaluate_row(row, review_at):
    if not all(row[k] for k in ('market', 'venue', 'ticker')):
        raise ValueError('market, venue and ticker are required')
    forecast_at = aware_timestamp(row['as_of'])
    report_date = iso_date(row['report_date'])
    target = iso_date(row['forecast_target_date'])
    if forecast_at > review_at:
        raise ValueError('forecast as_of is after review as_of')
    target_close_value = row.get('forecast_target_close_at', '')
    target_close_at = (aware_timestamp(target_close_value, 'forecast_target_close_at')
                       if target_close_value else None)
    if target_close_at and target_close_at.date() != target:
        raise ValueError('forecast_target_close_at local date must match forecast_target_date')
    latest_forecast_day = max(report_date, forecast_at.date())
    if target < latest_forecast_day:
        raise ValueError('target must be later than forecast date')
    if target == latest_forecast_day and not target_close_at:
        raise ValueError('same-day target requires forecast_target_close_at')
    if target_close_at and forecast_at >= target_close_at:
        raise ValueError('forecast as_of must be before forecast_target_close_at')
    if row['horizon_type'] not in {'next_session', 'week_end'}:
        raise ValueError('unsupported horizon_type')
    if row['status'] not in STATUSES or row['forecast_direction'] not in DIRECTIONS:
        raise ValueError('unsupported status or forecast_direction')
    abstention = next((v for v in (row['status'], row['forecast_direction'])
                       if v in {'abstain', 'data_unavailable'}), None)
    reference = number(row['reference_close'], 'reference_close') if row['reference_close'] else None
    if row['reference_close_date']:
        if iso_date(row['reference_close_date']) > forecast_at.date():
            raise ValueError('reference date is after forecast date')
    if not abstention and (reference is None or not row['reference_close_date'] or not row['reference_source']):
        raise ValueError('reference price, date and source are required')
    low, high = row['forecast_range_low'], row['forecast_range_high']
    if bool(low) != bool(high):
        raise ValueError('forecast range must have both bounds')
    bounds = (number(low, 'range_low'), number(high, 'range_high')) if low else None
    if bounds and bounds[0] > bounds[1]:
        raise ValueError('forecast range low exceeds high')
    probability = number(row['probability_up'], 'probability_up', True) if row['probability_up'] else None
    actual_fields = [row[k] for k in ('actual_close_date', 'actual_close', 'actual_source')]
    if any(actual_fields) and not all(actual_fields):
        raise ValueError('actual price, date and source must all be supplied')
    actual = None
    unavailable_reason = None
    available_at = row.get('actual_available_at', '')
    if available_at and not all(actual_fields):
        raise ValueError('actual_available_at requires complete actual fields')
    if all(actual_fields):
        actual_date = iso_date(row['actual_close_date'])
        actual = number(row['actual_close'], 'actual_close')
        if actual_date != target or actual_date > review_at.date():
            raise ValueError('actual date must match target and not be after review as_of')
        if available_at:
            available = aware_timestamp(available_at, 'actual_available_at')
            if available > review_at or available.date() < actual_date:
                raise ValueError('actual_available_at is future or earlier than actual close date')
            if target_close_at and available < target_close_at:
                raise ValueError('actual_available_at is before forecast_target_close_at')
        else:
            unavailable_reason = 'actual availability timestamp missing; close availability is unverified'
        if re.search(r'\b(intraday|snapshot)\b', row['scoring_notes'], re.IGNORECASE):
            unavailable_reason = 'reference close basis is incomparable or ambiguous: intraday/snapshot notes'
    if actual is not None:
        status = 'not_scored' if unavailable_reason else 'scored'
    elif target_close_at:
        status = 'pending' if review_at < target_close_at else 'not_scored'
    else:
        status = 'pending' if target > review_at.date() else 'not_scored'
    result = dict(forecast_id=row['forecast_id'], horizon_type=row['horizon_type'],
                  market=row['market'], venue=row['venue'], ticker=row['ticker'],
                  forecast_target_date=target.isoformat(), status=abstention or status)
    if result['status'] != 'scored':
        result['reason'] = abstention or unavailable_reason or ('target has not matured' if result['status'] == 'pending' else 'mature target has no actual data')
        return result
    realized = (actual / reference - 1) * 100
    if not math.isfinite(realized):
        raise ValueError('computed return is not finite')
    result['realized_return_pct'] = realized
    direction = row['forecast_direction']
    result['direction_hit'] = ((actual > reference) if direction == 'up' else
                               (actual < reference) if direction == 'down' else None)
    result['range_hit'] = bounds[0] <= actual <= bounds[1] if bounds else None
    result['brier_score'] = (probability - int(actual > reference)) ** 2 if probability is not None and actual != reference else None
    return result


def summarize(results):
    counts = Counter(r['status'] for r in results)
    directions = [r['direction_hit'] for r in results if r.get('direction_hit') is not None]
    ranges = [r['range_hit'] for r in results if r.get('range_hit') is not None]
    briers = [r['brier_score'] for r in results if r.get('brier_score') is not None]
    mature = counts['scored'] + counts['not_scored']
    return {
        'total': len(results),
        'unique_instrument_targets': len({(r['market'], r['venue'], r['ticker'], r['horizon_type'], r['forecast_target_date'])
                                         for r in results if r['status'] != 'invalid'}),
        'counts': {k: counts[k] for k in ('scored', 'pending', 'not_scored', 'abstain', 'data_unavailable', 'invalid')},
        'coverage': {'scored': counts['scored'], 'mature_eligible': mature,
                     'fraction': counts['scored'] / mature if mature else None},
        'direction': {'hits': sum(directions), 'denominator': len(directions),
                      'hit_rate': sum(directions) / len(directions) if directions else None},
        'range': {'hits': sum(ranges), 'denominator': len(ranges),
                  'hit_rate': sum(ranges) / len(ranges) if ranges else None},
        'brier': {'denominator': len(briers), 'mean': sum(briers) / len(briers) if briers else None},
    }


def review_ledger(ledger, as_of):
    """Return a JSON-compatible summary; invalid rows are visible and never scored."""
    review_at = aware_timestamp(as_of)
    results, errors = [], []
    try:
        with Path(ledger).open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)) or not REQUIRED <= set(headers):
                raise ValueError('duplicate or missing required CSV headers')
            rows = list(reader)
            if not rows:
                raise ValueError('ledger contains no forecast rows')
        ids = Counter((r.get('forecast_id') or '').strip() for r in rows)
        for line, raw in enumerate(rows, 2):
            row = {k: v.strip() if isinstance(v, str) else v for k, v in raw.items()}
            try:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError('malformed CSV row width')
                if not row['forecast_id'] or ids[row['forecast_id']] != 1:
                    raise ValueError('missing or duplicate forecast_id')
                result = evaluate_row(row, review_at)
            except (ValueError, OverflowError) as exc:
                errors.append({'line': line, 'forecast_id': row.get('forecast_id'), 'error': str(exc)})
                result = {'forecast_id': row.get('forecast_id'), 'horizon_type': row.get('horizon_type') or 'unknown', 'status': 'invalid'}
            results.append(result)
    except (csv.Error, ValueError) as exc:
        errors.append({'error': str(exc)})
    vintages = Counter((r['market'], r['venue'], r['ticker'], r['horizon_type'], r['forecast_target_date'])
                       for r in results if r['status'] != 'invalid')
    warnings = [{'market': key[0], 'venue': key[1], 'ticker': key[2], 'horizon_type': key[3],
                 'forecast_target_date': key[4], 'issuance_count': count,
                 'warning': 'repeated instrument-target forecast vintages are correlated'}
                for key, count in sorted(vintages.items()) if count > 1]
    return {
        'as_of': review_at.isoformat(), 'valid': not errors, 'errors': errors,
        'warnings': warnings,
        'aggregation_policy': 'all issuances, correlated vintages; not independent samples',
        'summary': summarize(results),
        'by_horizon': {h: summarize([r for r in results if r['horizon_type'] == h])
                       for h in sorted({r['horizon_type'] for r in results})},
        'rows': results,
        'assumptions': [
            'Offline review uses supplied source references; it does not verify or fetch prices.',
            'Target maturity without actual data uses a supplied forecast_target_close_at when present; otherwise it uses the review timezone calendar date. Scoring requires a supplied aware actual_available_at no later than review as_of and, when target close is supplied, not before that close.',
            'Corporate-action adjustment, currency, venue and session consistency require human/provider validation; no exchange calendar engine is used.',
            'Ranges and forecasts are assumed frozen before outcomes; CSV history is not independently verified.',
            'Direction scoring covers up/down only; zero return misses. Range bounds are inclusive.',
            'Brier scoring uses a positive-return outcome and excludes zero returns.',
            'Coverage is scored / (scored + mature not_scored); invalid and abstention rows are excluded.',
            'Stored status and derived hit/return cells do not establish outcomes; actual inputs determine maturity and scoring.',
            'Small or correlated samples do not establish trading skill or guarantee returns.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', required=True, type=Path)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.output and (args.output.resolve() == args.ledger.resolve() or
                        (args.output.exists() and args.ledger.exists() and args.output.samefile(args.ledger))):
        parser.error('--output must not overwrite the ledger')
    try:
        result = review_ledger(args.ledger, args.as_of)
        encoded = json.dumps(result, indent=2, allow_nan=False) + '\n'
        if args.output:
            args.output.write_text(encoded, encoding='utf-8')
        print(encoded, end='')
        return 0 if result['valid'] else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({'valid': False, 'errors': [{'error': str(exc)}]}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
