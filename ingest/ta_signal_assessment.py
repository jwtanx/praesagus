"""Synthetic-only daily TA event simulation from normalized supplied values.

No indicator formulas, provider calls, file access or forecasting. Simulated
bindings/warmup declarations are consistency controls, not vendor equivalence.

Schema 1 record: synthetic/source_claim, US-qualified code, daily timeframe,
listing/MIC/currency/adjustment/vintage, calendar_version and indicator mapping.
Each item explicitly declares complete result/coverage, code/timeframe, fixed
simulated roles/parameters, versioned artificial sufficient-warmup metadata and
exactly two rows. Rows bind identity, session date, final UTC close/observation,
availability, retrieval, ingestion and known-at times, plus named finite values.
Calendar schema 1 declares complete dated coverage, timezone and ordered final
UTC session closes. Its identity must match the record. Missing/contradictory
metadata yields unavailable, never a neutral no-event inference.
"""
from datetime import date, datetime, timezone
import math
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


METHOD_VERSION = 'praesagus-ta-events-v1'
SIMULATED_WARMUP_VERSION = 'artificial-warmup-fixture-v1'
INDICATORS = {
    'KDJ': {'parameters': {'n': 9, 'k': 3, 'd': 3}, 'roles': ('K', 'D', 'J'),
            'rule': 'Prior K<=D and current K>D: bullish; prior K>=D and current K<D: bearish; current equality: neutral.'},
    'MACD': {'parameters': {'fast': 12, 'slow': 26, 'signal': 9}, 'roles': ('DIF', 'DEA'),
             'rule': 'Prior DIF<=DEA and current DIF>DEA: bullish; prior DIF>=DEA and current DIF<DEA: bearish; current equality: neutral.'},
    'BOLL': {'parameters': {'n': 20, 'deviations': 2}, 'roles': ('close', 'lower', 'middle', 'upper'),
             'rule': 'Prior close strictly below lower and current inside inclusive bands: bullish re-entry; prior strictly above upper and current inside inclusive bands: bearish re-entry; otherwise neutral.'},
}
IDENTITY = ('listing_id', 'mic', 'currency', 'adjustment_basis', 'series_vintage')


def _need(condition, reason):
    if not condition:
        raise ValueError(reason)


def _object(value, reason):
    _need(isinstance(value, dict), reason)
    return value


def _text(value, reason):
    _need(isinstance(value, str) and bool(value.strip()), reason)
    return value


def _date(value):
    _need(isinstance(value, str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value)), 'invalid_session_date')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError('invalid_session_date') from None


def _time(value, utc=False):
    _need(isinstance(value, str), 'source_availability_unknown' if value is None else 'invalid_timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('invalid_timestamp') from None
    _need(parsed.utcoffset() is not None, 'timezone_required')
    _need(not utc or parsed.utcoffset().total_seconds() == 0, 'utc_close_required')
    return parsed.astimezone(timezone.utc)


def _number(value):
    _need(type(value) in (int, float), 'invalid_indicator_value')
    try:
        _need(math.isfinite(value), 'nonfinite_indicator_value')
    except OverflowError:
        raise ValueError('nonfinite_indicator_value') from None
    return value


def _global(record, calendar, cutoff):
    record = _object(record, 'malformed_record')
    calendar = _object(calendar, 'malformed_calendar')
    _need(type(record.get('schema_version')) is int and record['schema_version'] == 1, 'unsupported_schema')
    _need(type(calendar.get('schema_version')) is int and calendar['schema_version'] == 1, 'unsupported_calendar_schema')
    _need(record.get('synthetic') is True and calendar.get('synthetic') is True, 'synthetic_only')
    _need(record.get('source_class') == 'provider_calculated_values' and
          record.get('source_claim') == 'simulated' and record.get('event_author') == 'Praesagus', 'unsupported_source_contract')
    _need(record.get('timeframe') == '1d', 'unsupported_timeframe')
    code = record.get('code')
    _need(isinstance(code, str) and bool(re.fullmatch(r'US\.[A-Z0-9][A-Z0-9.-]{0,9}', code)), 'unsupported_ticker')
    for key in IDENTITY:
        _text(record.get(key), 'missing_' + key)
        _need(record[key] == calendar.get(key), 'calendar_identity_mismatch:' + key)
    _need(record['adjustment_basis'] in {'unadjusted', 'split_adjusted'}, 'unsupported_adjustment_basis')
    _need(bool(re.fullmatch(r'[A-Z0-9]{4}', record['mic'])), 'invalid_mic')
    _need(record['currency'] == 'USD', 'unsupported_currency')
    _need(calendar.get('complete') is True, 'calendar_coverage_unknown')
    _text(calendar.get('version'), 'missing_calendar_version')
    _need(record.get('calendar_version') == calendar['version'], 'calendar_version_mismatch')
    try:
        zone = ZoneInfo(_text(calendar.get('timezone'), 'missing_calendar_timezone'))
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('invalid_calendar_timezone') from None
    now = _time(cutoff)
    start, end = _date(calendar.get('coverage_start')), _date(calendar.get('coverage_end'))
    _need(start <= now.astimezone(zone).date() <= end, 'cutoff_outside_calendar_coverage')
    sessions = calendar.get('sessions')
    _need(isinstance(sessions, list) and 2 <= len(sessions) <= 100, 'invalid_calendar_sessions')
    completed = []
    previous = None
    for session in sessions:
        session = _object(session, 'invalid_calendar_session')
        day = _date(session.get('session_date'))
        close = _time(session.get('close_at'), utc=True)
        _need(start <= day <= end and close.astimezone(zone).date() == day, 'calendar_session_date_mismatch')
        _need(previous is None or previous < day, 'duplicate_or_unordered_calendar_sessions')
        _need(session.get('close_kind') == 'final_regular_session_close', 'nonfinal_calendar_close')
        previous = day
        if close <= now:
            completed.append((day.isoformat(), close))
    _need(len(completed) >= 2, 'insufficient_completed_sessions')
    _object(record.get('indicators'), 'missing_indicators')
    _need(len(record['indicators']) <= 3 and not set(record['indicators']) - set(INDICATORS), 'unsupported_indicator')
    return now, completed[-2:]


def _assess_indicator(name, item, record, pair, cutoff):
    config = INDICATORS[name]
    item = _object(item, 'missing_indicator')
    _need(item.get('status') == 'complete', 'indicator_result_unavailable')
    _need(item.get('coverage') == 'complete', 'indicator_coverage_incomplete')
    _need(item.get('code') == record['code'] and item.get('timeframe') == '1d', 'indicator_identity_mismatch')
    _need(item.get('binding_kind') == 'simulated', 'output_binding_not_simulated')
    _need(item.get('parameters') == config['parameters'], 'parameter_mismatch')
    expected_roles = {role: 'simulated_' + name + '_' + role for role in config['roles']}
    _need(item.get('output_roles') == expected_roles, 'output_role_mismatch')
    warmup = _object(item.get('warmup'), 'warmup_unknown')
    _need(warmup.get('version') == SIMULATED_WARMUP_VERSION, 'warmup_version_mismatch')
    _need(warmup.get('metadata_source') == 'simulated_provider' and warmup.get('status') == 'sufficient', 'warmup_unverified')
    _need(type(warmup.get('required_bars')) is int and 1 <= warmup['required_bars'] <= 100 and
          type(warmup.get('available_bars')) is int and warmup['required_bars'] <= warmup['available_bars'] <= 100,
          'insufficient_warmup')
    rows = item.get('rows')
    _need(isinstance(rows, list) and len(rows) == 2, 'partial_or_duplicate_session_coverage')
    validated = []
    for row, (day, close) in zip(rows, pair):
        row = _object(row, 'malformed_indicator_row')
        _need(row.get('code') == record['code'], 'row_ticker_mismatch')
        _need(row.get('session_date') == day, 'stale_gap_or_duplicate_session')
        _need(_time(row.get('close_at'), utc=True) == close, 'session_close_mismatch')
        _need(row.get('observation_kind') == 'final_regular_session_close', 'nonfinal_observation')
        for key in IDENTITY:
            _need(row.get(key) == record[key], 'row_identity_mismatch:' + key)
        observed = _time(row.get('observed_at'))
        _need(observed == close, 'observation_not_at_session_close')
        available = _time(row.get('available_at'))
        retrieved = _time(row.get('retrieved_at'))
        ingested = _time(row.get('ingested_at'))
        known = _time(row.get('known_at'))
        _need(close <= available <= retrieved <= ingested <= known <= cutoff, 'source_time_order_or_cutoff_invalid')
        values = _object(row.get('values'), 'missing_indicator_values')
        _need(set(values) == set(config['roles']), 'partial_or_unknown_value_roles')
        values = {role: _number(values[role]) for role in config['roles']}
        if name == 'KDJ':
            _need(0 <= values['K'] <= 100 and 0 <= values['D'] <= 100, 'invalid_kdj_range')
        if name == 'BOLL':
            _need(values['close'] > 0, 'nonpositive_close')
            _need(values['lower'] <= values['middle'] <= values['upper'], 'invalid_band_order')
        validated.append(dict(session_date=day, close_at=close.isoformat(), values=values,
                              times=dict(observed_at=observed.isoformat(), available_at=available.isoformat(),
                                         retrieved_at=retrieved.isoformat(), ingested_at=ingested.isoformat(),
                                         known_at=known.isoformat())))
    prior, current = (row['values'] for row in validated)
    bullish = bearish = False
    if name in {'KDJ', 'MACD'}:
        left, right = ('K', 'D') if name == 'KDJ' else ('DIF', 'DEA')
        bullish = prior[left] <= prior[right] and current[left] > current[right]
        bearish = prior[left] >= prior[right] and current[left] < current[right]
    else:
        inside = current['lower'] <= current['close'] <= current['upper']
        bullish = prior['close'] < prior['lower'] and inside
        bearish = prior['close'] > prior['upper'] and inside
    return ('bullish_event' if bullish else 'bearish_event' if bearish else 'neutral'), validated


def assess_ticker(record, *, calendar, cutoff):
    """Assess exactly three simulated events; malformed/missing data is unavailable.

    Calendar sessions are ordered authored dates with exact UTC closes and
    complete coverage. Rows contain exactly consecutive prior/latest sessions.
    Roles/parameters and warmup metadata versions are simulated, not SDK mappings.
    Warmup counts are caller-declared artificial fixtures, never vendor minima.
    Result includes only validated values, never raw input or forecast fields.
    """
    result = dict(schema_version=1, synthetic=True, method_version=METHOD_VERSION,
                  ticker=None, source_class='provider_calculated_values', event_author='Praesagus',
                  timeframe='1d', cutoff=None, expected_session=None, provenance=None, indicators=[])
    error = None
    try:
        now, pair = _global(record, calendar, cutoff)
        result.update(ticker=record['code'], cutoff=now.isoformat(), expected_session=pair[-1][0])
        result['provenance'] = dict(calendar_version=calendar['version'], timezone=calendar['timezone'],
                                    mic=record['mic'], currency=record['currency'],
                                    adjustment_basis=record['adjustment_basis'], series_vintage=record['series_vintage'],
                                    source_claim='simulated')
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        error = str(exc) if isinstance(exc, ValueError) else 'malformed_input'
    counts = dict(bullish=0, bearish=0, neutral=0, unavailable=0, evaluated=0, expected=3)
    for name, config in INDICATORS.items():
        detail = dict(name=name, status='unavailable', rule_version=METHOD_VERSION + ':' + name,
                      rule=config['rule'], parameters=dict(config['parameters']), prior_session=None,
                      current_session=result['expected_session'], prior_close_at=None, current_close_at=None,
                      prior_values=None, current_values=None, prior_times=None, current_times=None,
                      warmup=None, output_roles=None, reasons=[])
        if error:
            detail['reasons'] = [error]
        else:
            try:
                status, rows = _assess_indicator(name, record['indicators'].get(name), record, pair, now)
                detail.update(status=status, prior_session=rows[0]['session_date'], current_session=rows[1]['session_date'],
                              prior_close_at=rows[0]['close_at'], current_close_at=rows[1]['close_at'],
                              prior_values=rows[0]['values'], current_values=rows[1]['values'],
                              prior_times=rows[0]['times'], current_times=rows[1]['times'])
                source = record['indicators'][name]
                detail['warmup'] = {key: source['warmup'][key] for key in
                                    ('version', 'status', 'metadata_source', 'required_bars', 'available_bars')}
                detail['output_roles'] = dict(source['output_roles'])
            except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
                detail['reasons'] = [str(exc) if isinstance(exc, ValueError) else 'malformed_input']
        counts[{'bullish_event': 'bullish', 'bearish_event': 'bearish'}.get(detail['status'], detail['status'])] += 1
        result['indicators'].append(detail)
    counts['evaluated'] = 3 - counts['unavailable']
    result['counts'] = counts
    return result


def synthetic_demo():
    """Return fresh, plainly simulated inputs for preview/tests; never market data."""
    # Authored holiday/early close and artificial warmup counts are not real
    # exchange schedules or provider requirements.
    identity = dict(listing_id='simulated-listing', mic='XNAS', currency='USD',
                    adjustment_basis='split_adjusted', series_vintage='simulated-series-1')
    calendar = dict(schema_version=1, synthetic=True, complete=True, version='simulated-calendar-1', timezone='America/New_York',
                    coverage_start='2026-10-05', coverage_end='2026-10-12', **identity,
                    sessions=[dict(session_date=day, close_at=day + 'T' + hour + ':00:00Z',
                                   close_kind='final_regular_session_close')
                              for day, hour in [('2026-10-05', '20'), ('2026-10-06', '20'),
                                                ('2026-10-08', '20'), ('2026-10-09', '17'), ('2026-10-12', '20')]])
    record = dict(schema_version=1, synthetic=True, source_class='provider_calculated_values', source_claim='simulated',
                  event_author='Praesagus', timeframe='1d', code='US.SYNTH', calendar_version=calendar['version'],
                  indicators={}, **identity)
    values = {'KDJ': ({'K': 35, 'D': 40, 'J': 25}, {'K': 45, 'D': 40, 'J': 55}),
              'MACD': ({'DIF': 1, 'DEA': 0}, {'DIF': -1, 'DEA': 0}),
              'BOLL': ({'close': 90, 'lower': 95, 'middle': 100, 'upper': 105},
                       {'close': 100, 'lower': 95, 'middle': 100, 'upper': 105})}
    for name, config in INDICATORS.items():
        record['indicators'][name] = dict(status='complete', coverage='complete', code=record['code'],
            timeframe='1d', binding_kind='simulated', parameters=dict(config['parameters']),
            output_roles={role: 'simulated_' + name + '_' + role for role in config['roles']},
            warmup=dict(version=SIMULATED_WARMUP_VERSION, status='sufficient', metadata_source='simulated_provider',
                        required_bars=2, available_bars=2),
            rows=[dict(code=record['code'], session_date=day, close_at=day + 'T' + hour + ':00:00Z',
                       observed_at=day + 'T' + hour + ':00:00Z', available_at=day + 'T' + hour + ':01:00Z',
                       retrieved_at=day + 'T' + hour + ':02:00Z', ingested_at=day + 'T' + hour + ':02:30Z',
                       known_at=day + 'T' + hour + ':03:00Z',
                       observation_kind='final_regular_session_close', values=value, **identity)
                  for (day, hour), value in zip([('2026-10-08', '20'), ('2026-10-09', '17')], values[name])])
    return dict(record=record, calendar=calendar, cutoff='2026-10-10T12:00:00Z')
