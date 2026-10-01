"""Pure synthetic completed-session metrics; see SESSION_METRICS.md."""
from datetime import date, datetime
import math
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

METRICS = ('gap', 'close_return', 'intraday', 'range', 'relative_volume')
IDENTITY = ('instrument', 'venue', 'currency', 'adjustment_basis')


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + ' requires nonempty text')
    return value


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('session requires YYYY-MM-DD')
    date.fromisoformat(value)
    return value


def _time(value, field):
    if not isinstance(value, str) or 'T' not in value:
        raise ValueError(field + ' requires aware ISO timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError(field + ' requires timezone offset')
    return parsed


def _number(value, field, positive=True):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(field + ' requires finite ' + ('positive' if positive else 'nonnegative') + ' number')


def _sessions(values, field):
    if not isinstance(values, list) or not values:
        raise ValueError(field + ' requires a nonempty ordered session list')
    for value in values:
        _date(value)
    if any(a >= b for a, b in zip(values, values[1:])):
        raise ValueError(field + ' must be ordered and unique')
    return values


def calculate_session_metrics(fixture):
    """Validate a synthetic envelope and return every requested target/control row.

    Source vintages must already be resolved by the caller. No store lookup, latest
    revision selection, exchange calendar verification or action adjustment occurs.
    """
    if not isinstance(fixture, dict) or type(fixture.get('schema_version')) is not int or fixture['schema_version'] != 1:
        raise ValueError('fixture schema_version must be 1')
    if fixture.get('origin') != 'synthetic':
        raise ValueError('only synthetic fixtures are supported')
    identity = {field: _text(fixture.get(field), field) for field in IDENTITY}
    selection = fixture.get('source_vintage_selection')
    if not isinstance(selection, dict):
        raise ValueError('explicit source_vintage_selection required')
    selection = {field: _text(selection.get(field), 'selection.' + field) for field in ('method', 'reference')}
    cutoff = _time(fixture.get('decision_cutoff'), 'decision_cutoff')
    try:
        zone = ZoneInfo(_text(fixture.get('exchange_timezone'), 'exchange_timezone'))
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('exchange_timezone requires IANA timezone') from None
    expected = _sessions(fixture.get('expected_sessions'), 'expected_sessions')
    targets = _sessions(fixture.get('target_sessions'), 'target_sessions')
    if any(session not in expected for session in targets):
        raise ValueError('target session outside expected_sessions')
    bars = fixture.get('bars')
    if not isinstance(bars, list):
        raise ValueError('bars must be an explicit list')
    records, eligible, quarantines = {}, {}, {}
    last = None
    for bar in bars:
        if not isinstance(bar, dict):
            raise ValueError('bar must be an object')
        session = _date(bar.get('session'))
        if session not in expected or (last is not None and session <= last):
            raise ValueError('bars require ordered unique expected sessions; resolve conflicting source vintages first')
        last = session
        if any(bar.get(field) != value for field, value in identity.items()):
            raise ValueError('bar instrument/venue/currency/adjustment basis mismatch')
        if bar.get('interval') != '1d' or bar.get('session_type') != 'regular':
            raise ValueError('only regular daily bars supported; snapshots rejected')
        if type(bar.get('completed')) is not bool:
            raise ValueError('completed must be explicit boolean')
        for field in ('open', 'high', 'low', 'close'):
            _number(bar.get(field), field)
        _number(bar.get('volume'), 'volume', positive=False)
        if not bar['low'] <= min(bar['open'], bar['close']) <= max(bar['open'], bar['close']) <= bar['high']:
            raise ValueError('invalid OHLC ordering')
        _text(bar.get('source_version'), 'source_version')
        _text(bar.get('provenance_ref'), 'provenance_ref')
        action = bar.get('action_status')
        if not isinstance(action, str) or action not in {'clear', 'uncertain', 'split', 'dividend', 'other'}:
            raise ValueError('explicit action_status required')
        for flag in ('shortened_session', 'halted', 'reopening'):
            if type(bar.get(flag)) is not bool:
                raise ValueError(flag + ' must be explicit boolean')
        completed = _time(bar.get('completed_at'), 'completed_at')
        available = _time(bar.get('available_at'), 'available_at')
        known = _time(bar.get('known_at'), 'known_at')
        if completed.astimezone(zone).date().isoformat() != session:
            raise ValueError('completion date differs from exchange-local session')
        reasons = []
        if not bar['completed']:
            reasons.append('incomplete_bar')
        if not completed <= available <= known:
            reasons.append('invalid_temporal_order')
        for field, instant in (('completion', completed), ('availability', available), ('knowledge', known)):
            if instant > cutoff:
                reasons.append('future_' + field)
        quarantine = (['action_' + action] if action != 'clear' else []) + [flag for flag in ('shortened_session', 'halted', 'reopening') if bar[flag]]
        records[session] = bar
        eligible[session] = reasons
        quarantines[session] = quarantine

    rows = []
    for session in targets:
        index = expected.index(session)
        current = records.get(session)
        values = dict.fromkeys(METRICS)
        reasons = {metric: [] for metric in METRICS}
        refs = {'current': current['provenance_ref'] if current else None, 'prior': None, 'volume_baseline': []}
        prior_session = expected[index - 1] if index else None
        window = expected[max(0, index - 20):index]
        row = {'session': session, 'metrics': values, 'reasons': reasons, 'status': 'unavailable',
               'provenance': refs, 'source_version': current['source_version'] if current else None,
               'prior_expected_session': prior_session,
               'volume_baseline': {'scheduled_sessions': list(window), 'valid_count': 0, 'median_volume': None}}
        rows.append(row)
        if current is None or eligible.get(session) or quarantines.get(session):
            failure = ['missing_target_bar'] if current is None else eligible[session] + quarantines[session]
            for metric in METRICS:
                reasons[metric] = list(failure)
            if current and quarantines[session]:
                row['status'] = 'quarantined'
            continue

        def set_value(metric, value):
            if math.isfinite(value):
                values[metric] = value
            else:
                reasons[metric].append('nonfinite_calculation')

        set_value('intraday', current['close'] / current['open'] - 1)
        prior = records.get(prior_session)
        if prior:
            refs['prior'] = prior['provenance_ref']
        prior_failure = (['no_prior_expected_session'] if prior_session is None else
                         ['missing_prior_expected_session'] if prior is None else
                         ['prior_' + reason for reason in eligible[prior_session] + quarantines[prior_session]])
        if prior_failure:
            for metric in ('gap', 'close_return', 'range'):
                reasons[metric] = list(prior_failure)
        else:
            set_value('gap', current['open'] / prior['close'] - 1)
            set_value('close_return', current['close'] / prior['close'] - 1)
            set_value('range', (current['high'] - current['low']) / prior['close'])
        historical = [records[day] for day in window if day in records and not eligible[day] and not quarantines[day]]
        refs['volume_baseline'] = [bar['provenance_ref'] for bar in historical]
        row['volume_baseline']['valid_count'] = len(historical)
        if len(historical) < 15:
            reasons['relative_volume'] = ['insufficient_volume_history']
        else:
            # Midpoint avoids addition overflow for two large finite volumes.
            ordered = sorted(bar['volume'] for bar in historical)
            middle = len(ordered) // 2
            baseline = ordered[middle] if len(ordered) % 2 else ordered[middle - 1] + (ordered[middle] - ordered[middle - 1]) / 2
            row['volume_baseline']['median_volume'] = baseline
            if baseline == 0:
                reasons['relative_volume'] = ['zero_median_volume']
            else:
                set_value('relative_volume', current['volume'] / baseline)
        row['status'] = 'quarantined' if prior and quarantines[prior_session] else 'ok' if all(value is not None for value in values.values()) else 'partial' if any(value is not None for value in values.values()) else 'unavailable'
    return {'schema_version': 1, 'origin': 'synthetic', 'decision_cutoff': fixture['decision_cutoff'],
            'identity': identity, 'exchange_timezone': fixture['exchange_timezone'],
            'source_vintage_selection': selection, 'rows': rows}
