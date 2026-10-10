"""Deterministic authored values only; no SDK, market data or indicator formulas."""
from copy import deepcopy
import json

import pytest

from ingest.ta_signal_assessment import assess_ticker, synthetic_demo


@pytest.fixture
def demo():
    return synthetic_demo()


def item(result, name):
    return next(row for row in result['indicators'] if row['name'] == name)


def invariants(result):
    counts = result['counts']
    assert sum(counts[key] for key in ('bullish', 'bearish', 'neutral', 'unavailable')) == 3
    assert counts['expected'] == 3 and counts['evaluated'] == 3 - counts['unavailable']
    assert [row['name'] for row in result['indicators']] == ['KDJ', 'MACD', 'BOLL']
    json.dumps(result, allow_nan=False)


def test_demo_is_fresh_read_only_explicit_simulation(demo):
    original = deepcopy(demo)
    result = assess_ticker(**demo)
    assert demo == original == synthetic_demo()
    assert result['synthetic'] is True
    assert result['source_class'] == 'provider_calculated_values'
    assert result['event_author'] == 'Praesagus'
    assert result['counts'] == dict(bullish=2, bearish=1, neutral=0, unavailable=0, evaluated=3, expected=3)
    assert result['expected_session'] == '2026-10-09'
    assert not {'forecast', 'confidence', 'target', 'probability', 'raw_response'} & result.keys()
    invariants(result)


@pytest.mark.parametrize('name,left,right', [('KDJ', 'K', 'D'), ('MACD', 'DIF', 'DEA')])
@pytest.mark.parametrize('prior,current,status', [
    ((40, 40), (41, 40), 'bullish_event'), ((40, 40), (39, 40), 'bearish_event'),
    ((39, 40), (40, 40), 'neutral'), ((41, 40), (40, 40), 'neutral'),
    ((41, 40), (42, 40), 'neutral'), ((39, 40), (38, 40), 'neutral'),
    ((39, 40), (41, 40), 'bullish_event'), ((41, 40), (39, 40), 'bearish_event'),
])
def test_crossover_direction_equality_and_no_carry_forward(demo, name, left, right, prior, current, status):
    rows = demo['record']['indicators'][name]['rows']
    for row, values in zip(rows, (prior, current)):
        row['values'][left], row['values'][right] = values
    result = assess_ticker(**demo)
    assert item(result, name)['status'] == status
    invariants(result)


@pytest.mark.parametrize('prior,current,status', [
    (94, 95, 'bullish_event'), (106, 105, 'bearish_event'),
    (95, 100, 'neutral'), (105, 100, 'neutral'),
    (94, 94, 'neutral'), (106, 106, 'neutral'), (100, 101, 'neutral'),
    (94, 106, 'neutral'), (106, 94, 'neutral'),
])
def test_boll_inclusive_reentry_mere_touch_and_continued_outside(demo, prior, current, status):
    rows = demo['record']['indicators']['BOLL']['rows']
    rows[0]['values']['close'] = prior
    rows[1]['values']['close'] = current
    result = assess_ticker(**demo)
    assert item(result, 'BOLL')['status'] == status
    invariants(result)


def test_signed_macd_unbounded_j_and_zero_width_bands(demo):
    rows = demo['record']['indicators']['MACD']['rows']
    rows[0]['values'] = {'DIF': -3, 'DEA': -2}
    rows[1]['values'] = {'DIF': -1, 'DEA': -2}
    demo['record']['indicators']['KDJ']['rows'][1]['values']['J'] = 140
    for row in demo['record']['indicators']['BOLL']['rows']:
        row['values'] = dict(close=100, lower=100, middle=100, upper=100)
    result = assess_ticker(**demo)
    assert item(result, 'MACD')['status'] == 'bullish_event'
    assert item(result, 'KDJ')['status'] == 'bullish_event'
    assert item(result, 'BOLL')['status'] == 'neutral'


@pytest.mark.parametrize('cutoff,expected,eligible', [
    ('2026-10-09T17:03:00Z', '2026-10-09', True),
    ('2026-10-10T12:00:00Z', '2026-10-09', True),
    ('2026-10-11T12:00:00Z', '2026-10-09', True),
    ('2026-10-12T19:59:59Z', '2026-10-09', True),
    ('2026-10-12T20:00:00Z', '2026-10-12', False),
    ('2026-10-09T16:59:59Z', '2026-10-08', False),
    ('2026-10-09T17:00:00Z', '2026-10-09', False),
])
def test_early_close_weekend_and_next_close_expiry(demo, cutoff, expected, eligible):
    demo['cutoff'] = cutoff
    result = assess_ticker(**demo)
    assert result['expected_session'] == expected
    assert (result['counts']['evaluated'] == 3) is eligible
    invariants(result)


@pytest.mark.parametrize('name', ['KDJ', 'MACD', 'BOLL'])
@pytest.mark.parametrize('change,reason', [
    ('missing', 'missing_indicator'), ('partial', 'partial_or_duplicate_session_coverage'),
    ('duplicate', 'stale_gap_or_duplicate_session'), ('extra-row', 'partial_or_duplicate_session_coverage'),
    ('gap', 'stale_gap_or_duplicate_session'), ('roles', 'output_role_mismatch'),
    ('parameters', 'parameter_mismatch'), ('binding', 'output_binding_not_simulated'),
    ('warmup-missing', 'warmup_unknown'), ('warmup-insufficient', 'insufficient_warmup'),
    ('warmup-status', 'warmup_unverified'), ('warmup-source', 'warmup_unverified'),
    ('availability', 'source_availability_unknown'), ('future', 'source_time_order_or_cutoff_invalid'),
    ('retrieval', 'source_time_order_or_cutoff_invalid'), ('known', 'source_time_order_or_cutoff_invalid'),
    ('observation', 'observation_not_at_session_close'), ('nonfinal', 'nonfinal_observation'),
    ('close', 'session_close_mismatch'), ('timezone', 'timezone_required'),
    ('basis', 'row_identity_mismatch:adjustment_basis'), ('vintage', 'row_identity_mismatch:series_vintage'),
    ('currency', 'row_identity_mismatch:currency'), ('listing', 'row_identity_mismatch:listing_id'),
    ('nan', 'nonfinite_indicator_value'), ('bool', 'invalid_indicator_value'),
    ('string', 'invalid_indicator_value'), ('missing-value', 'partial_or_unknown_value_roles'),
    ('permission-denied', 'indicator_result_unavailable'), ('coverage-partial', 'indicator_coverage_incomplete'),
    ('item-timeframe', 'indicator_identity_mismatch'), ('row-ticker', 'row_ticker_mismatch'),
    ('warmup-version', 'warmup_version_mismatch'), ('ingest-before-retrieval', 'source_time_order_or_cutoff_invalid'),
    ('ingest-after-known', 'source_time_order_or_cutoff_invalid'),
])
def test_indicator_unavailability_isolated_and_counts_visible(demo, name, change, reason):
    indicator = demo['record']['indicators'][name]
    row = indicator['rows'][1]
    if change == 'missing': del demo['record']['indicators'][name]
    elif change == 'partial': indicator['rows'].pop()
    elif change == 'duplicate': indicator['rows'][1] = deepcopy(indicator['rows'][0])
    elif change == 'extra-row': indicator['rows'].append(deepcopy(row))
    elif change == 'gap': indicator['rows'][0]['session_date'] = '2026-10-06'
    elif change == 'roles': indicator['output_roles'] = {}
    elif change == 'parameters': indicator['parameters'] = {'n': 7}
    elif change == 'binding': indicator['binding_kind'] = 'vendor_verified'
    elif change == 'warmup-missing': del indicator['warmup']
    elif change == 'warmup-insufficient': indicator['warmup']['available_bars'] = 1
    elif change == 'warmup-status': indicator['warmup']['status'] = 'unknown'
    elif change == 'warmup-source': indicator['warmup']['metadata_source'] = 'guessed'
    elif change == 'availability': row['available_at'] = None
    elif change == 'future': row['available_at'] = '2026-10-11T20:00:00Z'
    elif change == 'retrieval': row['retrieved_at'] = '2026-10-09T16:59:00Z'
    elif change == 'known': row['known_at'] = '2026-10-09T17:01:00Z'
    elif change == 'observation': row['observed_at'] = '2026-10-09T16:59:00Z'
    elif change == 'nonfinal': row['observation_kind'] = 'after_hours'
    elif change == 'close': row['close_at'] = '2026-10-09T20:00:00Z'
    elif change == 'timezone': row['known_at'] = '2026-10-09T17:03:00'
    elif change == 'basis': row['adjustment_basis'] = 'unadjusted'
    elif change == 'vintage': row['series_vintage'] = 'different'
    elif change == 'currency': row['currency'] = 'EUR'
    elif change == 'listing': row['listing_id'] = 'another-listing'
    elif change == 'permission-denied': indicator['status'] = 'permission_denied'
    elif change == 'coverage-partial': indicator['coverage'] = 'partial'
    elif change == 'item-timeframe': indicator['timeframe'] = '5m'
    elif change == 'row-ticker': row['code'] = 'US.OTHER'
    elif change == 'warmup-version': indicator['warmup']['version'] = 'vendor-guess'
    elif change == 'ingest-before-retrieval': row['ingested_at'] = '2026-10-09T17:01:30Z'
    elif change == 'ingest-after-known': row['ingested_at'] = '2026-10-09T17:04:00Z'
    else:
        role = next(iter(row['values']))
        if change == 'missing-value': del row['values'][role]
        else: row['values'][role] = {'nan': float('nan'), 'bool': True, 'string': '100'}[change]
    result = assess_ticker(**demo)
    detail = item(result, name)
    assert detail['status'] == 'unavailable' and detail['reasons'] == [reason]
    assert detail['prior_values'] is None and detail['current_values'] is None
    assert result['counts']['unavailable'] == 1 and result['counts']['evaluated'] == 2
    invariants(result)


@pytest.mark.parametrize('change,reason', [
    ('synthetic', 'synthetic_only'), ('source', 'unsupported_source_contract'),
    ('timeframe', 'unsupported_timeframe'), ('ticker', 'unsupported_ticker'),
    ('basis', 'unsupported_adjustment_basis'), ('version', 'calendar_version_mismatch'),
    ('coverage', 'calendar_coverage_unknown'), ('coverage-end', 'cutoff_outside_calendar_coverage'),
    ('calendar-duplicate', 'duplicate_or_unordered_calendar_sessions'),
    ('calendar-nonfinal', 'nonfinal_calendar_close'), ('calendar-date', 'calendar_session_date_mismatch'),
    ('calendar-local-close', 'utc_close_required'), ('extra-indicator', 'unsupported_indicator'),
])
def test_global_rejections_never_produce_neutral(demo, change, reason):
    record, calendar = demo['record'], demo['calendar']
    if change == 'synthetic': record['synthetic'] = False
    elif change == 'source': record['source_class'] = 'native_screener_events'
    elif change == 'timeframe': record['timeframe'] = '5m'
    elif change == 'ticker': record['code'] = 'MY.1155'
    elif change == 'basis': record['adjustment_basis'] = calendar['adjustment_basis'] = 'unknown'
    elif change == 'version': record['calendar_version'] = 'other'
    elif change == 'coverage': calendar['complete'] = False
    elif change == 'coverage-end': calendar['coverage_end'] = '2026-10-09'
    elif change == 'calendar-duplicate': calendar['sessions'].insert(1, deepcopy(calendar['sessions'][0]))
    elif change == 'calendar-nonfinal': calendar['sessions'][0]['close_kind'] = 'provisional'
    elif change == 'calendar-date': calendar['sessions'][0]['close_at'] = '2026-10-06T20:00:00Z'
    elif change == 'calendar-local-close': calendar['sessions'][0]['close_at'] = '2026-10-05T16:00:00-04:00'
    else: record['indicators']['OTHER'] = {}
    result = assess_ticker(**demo)
    assert result['counts']['unavailable'] == 3 and result['counts']['neutral'] == 0
    assert all(row['reasons'] == [reason] for row in result['indicators'])
    invariants(result)


def test_authored_holiday_requires_consecutive_expected_sessions(demo):
    demo['cutoff'] = '2026-10-08T20:03:00Z'
    for indicator in demo['record']['indicators'].values():
        indicator['rows'][1] = deepcopy(indicator['rows'][0])
        row = indicator['rows'][0]
        row['session_date'] = '2026-10-06'
        for field in ('close_at', 'observed_at', 'available_at', 'retrieved_at', 'ingested_at', 'known_at'):
            row[field] = row[field].replace('2026-10-08', '2026-10-06')
    assert assess_ticker(**demo)['counts']['evaluated'] == 3


@pytest.mark.parametrize('record,calendar,cutoff', [(None, {}, 'bad'), ({}, {}, 'bad'), ([], None, None)])
def test_malformed_inputs_are_bounded(record, calendar, cutoff):
    one = assess_ticker(record, calendar=calendar, cutoff=cutoff)
    assert one == assess_ticker(record, calendar=calendar, cutoff=cutoff)
    assert one['counts']['unavailable'] == 3
    invariants(one)


def test_missing_all_indicators_is_visible(demo):
    demo['record']['indicators'] = {}
    result = assess_ticker(**demo)
    assert result['counts']['unavailable'] == 3
    assert result['counts']['evaluated'] == 0
    assert all(row['reasons'] == ['missing_indicator'] for row in result['indicators'])


def test_warmup_counts_are_declared_simulation_not_local_formula_minima(demo):
    for indicator in demo['record']['indicators'].values():
        indicator['warmup']['required_bars'] = 7
        indicator['warmup']['available_bars'] = 8
    result = assess_ticker(**demo)
    assert result['counts']['evaluated'] == 3
    assert result['indicators'][0]['current_times']['ingested_at'] == '2026-10-09T17:02:30+00:00'
    assert result['indicators'][0]['warmup']['required_bars'] == 7
    assert result['provenance']['adjustment_basis'] == 'split_adjusted'


@pytest.mark.parametrize('field', ['available_at', 'retrieved_at', 'ingested_at', 'known_at'])
def test_missing_source_times_cannot_be_inferred(demo, field):
    del demo['record']['indicators']['KDJ']['rows'][1][field]
    assert item(assess_ticker(**demo), 'KDJ')['status'] == 'unavailable'


@pytest.mark.parametrize('name,role,value,reason', [
    ('KDJ', 'K', 101, 'invalid_kdj_range'), ('KDJ', 'D', -1, 'invalid_kdj_range'),
    ('BOLL', 'close', 0, 'nonpositive_close'), ('BOLL', 'lower', 106, 'invalid_band_order'),
    ('MACD', 'DIF', float('inf'), 'nonfinite_indicator_value'),
    ('MACD', 'DIF', 10 ** 500, 'nonfinite_indicator_value'),
])
def test_numeric_rejections_are_bounded(demo, name, role, value, reason):
    demo['record']['indicators'][name]['rows'][1]['values'][role] = value
    result = assess_ticker(**demo)
    assert item(result, name)['reasons'] == [reason]
    invariants(result)


@pytest.mark.parametrize('field', ['schema_version', 'version', 'timezone', 'sessions', 'coverage_start'])
def test_missing_calendar_metadata_fails_closed(demo, field):
    del demo['calendar'][field]
    assert assess_ticker(**demo)['counts']['unavailable'] == 3


def test_equivalent_cutoff_offset_is_normalized(demo):
    original = assess_ticker(**demo)
    demo['cutoff'] = '2026-10-10T20:00:00+08:00'
    assert assess_ticker(**demo) == original
