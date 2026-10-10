"""Inline simulated metadata only: no market data, persistence or provider calls."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


MODULE = Path(__file__).resolve().parents[1] / 'harness/engineering/price-prediction/outcome_v2.py'
spec = importlib.util.spec_from_file_location('outcome_v2', MODULE)
outcome = importlib.util.module_from_spec(spec)
spec.loader.exec_module(outcome)
REVIEW = '2026-10-10T12:00:00Z'


def seal(record, fixtures):
    payload = dict(schema_version=2, synthetic=True, forecast_id=record['forecast_id'],
                   ledger_revision=record['ledger_revision'], reference=record['reference'],
                   actual=record['actual'])
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    fixtures['evidence'][record['evidence_fixture_id']] = raw
    record['evidence_sha256'] = hashlib.sha256(raw).hexdigest()


@pytest.fixture
def case():
    record = dict(schema_version=2, synthetic=True, market='US', forecast_id='synthetic-forecast',
                  ledger_revision='synthetic-frozen-v1-revision', listing_id='synthetic-listing', ticker='SYNTH',
                  forecast_cutoff='2026-10-05T21:00:00Z', reference_session='2026-10-05',
                  target_session='2026-10-09', horizon_kind='trading_sessions', horizon_count=3,
                  ledger_version='synthetic-ledger-1', instruments_version='synthetic-listings-1',
                  calendar_version='synthetic-calendar-1', mic_version='synthetic-mics-1',
                  evidence_fixture_id='synthetic-evidence-1', rights_declaration='synthetic_only',
                  review_state='requested')
    for name, day, close in [('reference', '2026-10-05', '20:00:00'), ('actual', '2026-10-09', '17:00:00')]:
        record[name] = dict(listing_id='synthetic-listing', ticker='SYNTH', mic='XNAS', currency='USD',
                            session_date=day, session_timezone='America/New_York',
                            source_class='vendor_reported_bar', source_claim='simulated',
                            observation_kind='final_regular_session_close', price_field='close',
                            adjustment_basis='unadjusted', corporate_action_treatment='none_in_synthetic_window',
                            value_semantics='traded_close_series', series_vintage='synthetic-vintage-1',
                            close_at=day + 'T' + close + 'Z', observed_at=day + 'T' + close + 'Z',
                            available_at=day + 'T' + close + 'Z', retrieved_at=day + 'T21:00:00Z',
                            availability_status='known', availability_fallback='none')
    fixtures = dict(
        ledger=dict(synthetic=True, version=record['ledger_version'], revision=record['ledger_revision'],
                    forecasts={record['forecast_id']: {field: record[field] for field in outcome.BINDING_FIELDS}}),
        instruments=dict(synthetic=True, version=record['instruments_version'], mic_version=record['mic_version'],
                         listings=[dict(listing_id='synthetic-listing', ticker='SYNTH', market='US', mic='XNAS',
                                        currency='USD', effective_from='2026-01-01', effective_to='2027-01-01')]),
        calendar=dict(synthetic=True, version=record['calendar_version'], mic_version=record['mic_version'],
                      mic='XNAS', timezone='America/New_York', coverage_start='2026-10-05',
                      coverage_end='2026-10-09', complete=True,
                      sessions={day: dict(close_at=day + 'T' + close + 'Z', close_kind='final_regular_session_close')
                                for day, close in [('2026-10-05', '20:00:00'), ('2026-10-06', '20:00:00'),
                                                   ('2026-10-08', '20:00:00'), ('2026-10-09', '17:00:00')]}),
        evidence={})
    fixtures['ledger']['forecasts'][record['forecast_id']]['reference_metadata'] = deepcopy(record['reference'])
    # The holiday and early close above are authored synthetic calendar entries.
    seal(record, fixtures)
    return record, fixtures


def assess(case, review=REVIEW):
    return outcome.assess_outcome(case[0], fixtures=case[1], review_at=review)


def test_complete_metadata_only_reaches_human_review_without_mutation(case):
    original = deepcopy(case)
    result = assess(case)
    assert result == dict(maturity='mature', provenance_status='synthetic_consistent',
                          rights_status='unverified', review_status='requested',
                          assessment_status='ready_for_human_review', reasons=[])
    assert case == original
    assert not {'score', 'return', 'direction_hit', 'range_hit', 'brier_score'} & result.keys()


@pytest.mark.parametrize('endpoint,field,value,reason', [
    ('reference', 'mic', '', 'nonempty_string_required'),
    ('actual', 'mic', 'XNYS', 'mic_mapping_mismatch'),
    ('actual', 'listing_id', 'another-listing', 'listing_identity_mismatch'),
    ('actual', 'ticker', 'OLD', 'ticker_mapping_mismatch'),
    ('actual', 'currency', 'EUR', 'currency_mapping_mismatch'),
    ('reference', 'observation_kind', 'intraday_snapshot', 'nonfinal_observation'),
    ('actual', 'observation_kind', 'provisional_auction_close', 'nonfinal_observation'),
    ('actual', 'observation_kind', 'extended_hours_last_trade', 'nonfinal_observation'),
    ('actual', 'price_field', 'last_trade', 'unsupported_price_field'),
    ('actual', 'adjustment_basis', 'unknown', 'unknown_adjustment_basis'),
    ('actual', 'adjustment_basis', 'split_adjusted', 'endpoint_semantics_mismatch:adjustment_basis'),
    ('actual', 'series_vintage', 'revised-vintage', 'endpoint_semantics_mismatch:series_vintage'),
    ('actual', 'source_class', 'social_quote', 'unsupported_source_class'),
    ('actual', 'source_class', 'exchange_certified_close', 'endpoint_semantics_mismatch:source_class'),
    ('actual', 'source_claim', 'certified', 'source_claim_not_simulated'),
    ('actual', 'corporate_action_treatment', 'different', 'endpoint_semantics_mismatch:corporate_action_treatment'),
    ('actual', 'corporate_action_treatment', 'unknown', 'unknown_corporate_action_treatment'),
    ('actual', 'value_semantics', 'traded_close', 'value_semantics_mismatch'),
    ('reference', 'available_at', '2026-10-05T21:00:01Z', 'availability_after_boundary'),
    ('reference', 'retrieved_at', '2026-10-05T21:00:01Z', 'timestamp_after_boundary'),
    ('reference', 'observed_at', '2026-10-05T19:59:59Z', 'observation_not_at_final_close'),
    ('actual', 'observed_at', '2026-10-09T16:59:59Z', 'observation_not_at_final_close'),
    ('actual', 'available_at', '2026-10-09T16:59:59Z', 'source_time_order_invalid'),
    ('actual', 'retrieved_at', '2026-10-09T16:59:59Z', 'retrieval_before_observation'),
    ('actual', 'retrieved_at', '2026-10-11T00:00:00Z', 'timestamp_after_boundary'),
    ('actual', 'close_at', '2026-10-09T20:00:00Z', 'session_close_mismatch'),
    ('actual', 'close_at', '2026-10-09T13:00:00-04:00', 'utc_timestamp_required'),
    ('actual', 'session_date', '2026-10-08', 'session_date_mismatch'),
    ('actual', 'session_timezone', 'UTC', 'session_timezone_mismatch'),
])
def test_endpoint_failures(case, endpoint, field, value, reason):
    record, fixtures = case
    record[endpoint][field] = value
    seal(record, fixtures)
    result = assess(case)
    assert result['assessment_status'] == 'blocked'
    assert any(reason in entry for entry in result['reasons'])


@pytest.mark.parametrize('endpoint', ['reference', 'actual'])
@pytest.mark.parametrize('declaration', [False, True])
def test_unknown_availability_is_never_inferred_from_retrieval(case, declaration, endpoint):
    record, fixtures = case
    record[endpoint]['available_at'] = None
    if declaration:
        record[endpoint]['availability_status'] = 'unknown'
    seal(record, fixtures)
    result = assess(case)
    assert endpoint + ':availability_unknown' in result['reasons']
    assert (endpoint + ':unknown_availability_declaration_missing' in result['reasons']) is not declaration
    assert record[endpoint]['available_at'] is None
    assert result['assessment_status'] == 'blocked'


@pytest.mark.parametrize('field,value,reason', [
    ('horizon_count', 4, 'horizon_count_mismatch'),
    ('horizon_count', True, 'positive_integer_horizon_required'),
    ('horizon_kind', 'calendar_days', 'unsupported_horizon_kind'),
    ('ledger_revision', 'new-revision', 'ledger_revision_mismatch'),
    ('forecast_id', 'missing-forecast', 'forecast_binding:object_required'),
    ('calendar_version', 'missing-calendar', 'calendar_version_mismatch'),
    ('instruments_version', 'new-map', 'instruments_version_mismatch'),
    ('mic_version', 'new-mics', 'mic_version_mismatch'),
    ('market', 'MY', 'us_only'),
    ('target_session', '2026-10-07', 'target_not_trading_session'),
    ('forecast_cutoff', '2026-10-09T17:00:00Z', 'forecast_not_before_target_close'),
    ('forecast_cutoff', '2026-10-11T00:00:00Z', 'forecast_after_review'),
    ('rights_declaration', 'unverified', 'rights_not_synthetic_only'),
    ('rights_declaration', 'denied', 'rights_not_synthetic_only'),
    ('rights_declaration', 'approved', 'rights_not_synthetic_only'),
    ('review_state', 'pending', 'human_review_not_requested'),
    ('review_state', 'denied', 'human_review_not_requested'),
    ('review_state', 'approved', 'human_review_not_requested'),
    ('evidence_fixture_id', 'absent', 'evidence_fixture_bytes_missing'),
    ('evidence_sha256', 'bad-digest', 'evidence_digest_mismatch'),
    ('synthetic', False, 'synthetic_record_required'),
    ('schema_version', 3, 'schema_version_2_required'),
])
def test_record_gates(case, field, value, reason):
    case[0][field] = value
    result = assess(case)
    assert result['assessment_status'] == 'blocked'
    assert reason in result['reasons']
    assert result['rights_status'] == ('denied' if value == 'denied' and field == 'rights_declaration' else 'unverified')


@pytest.mark.parametrize('change,reason', [
    ('effective-end', 'actual:effective_listing_not_unique'),
    ('effective-start', 'reference:effective_listing_not_unique'),
    ('duplicate-listing', 'reference:effective_listing_not_unique'),
    ('calendar-incomplete', 'calendar_not_declared_complete'),
    ('calendar-coverage', 'calendar_coverage_gap'),
    ('calendar-local-day', 'session_local_date_mismatch'),
    ('calendar-provisional', 'calendar_close_not_final'),
    ('nonsynthetic-fixture', 'calendar_fixture_not_synthetic'),
    ('binding', 'ledger_binding:target_session'),
    ('evidence-substitution', 'evidence_metadata_mismatch'),
])
def test_fixtures_fail_closed(case, change, reason):
    record, fixtures = case
    listing = fixtures['instruments']['listings'][0]
    calendar = fixtures['calendar']
    if change == 'effective-end': listing['effective_to'] = '2026-10-09'
    elif change == 'effective-start': listing['effective_from'] = '2026-10-06'
    elif change == 'duplicate-listing': fixtures['instruments']['listings'].append(deepcopy(listing))
    elif change == 'calendar-incomplete': calendar['complete'] = False
    elif change == 'calendar-coverage': calendar['coverage_end'] = '2026-10-08'
    elif change == 'calendar-local-day': calendar['sessions']['2026-10-09']['close_at'] = '2026-10-10T12:00:00Z'
    elif change == 'calendar-provisional': calendar['sessions']['2026-10-09']['close_kind'] = 'provisional'
    elif change == 'nonsynthetic-fixture': calendar['synthetic'] = False
    elif change == 'binding': fixtures['ledger']['forecasts'][record['forecast_id']]['target_session'] = '2026-10-08'
    else:
        raw = b'{"synthetic":true}'
        fixtures['evidence'][record['evidence_fixture_id']] = raw
        record['evidence_sha256'] = hashlib.sha256(raw).hexdigest()
    assert reason in assess(case)['reasons']


def test_pending_target_and_review_boundary(case):
    result = assess(case, '2026-10-09T16:59:59Z')
    assert result['maturity'] == 'pending'
    assert result['assessment_status'] == 'blocked'
    assert 'target_not_mature' in result['reasons']
    # Exactly at close is mature, but retrieval still must be available by review.
    record, fixtures = case
    record['actual']['retrieved_at'] = record['actual']['close_at']
    seal(record, fixtures)
    assert assess(case, '2026-10-09T17:00:00Z')['assessment_status'] == 'ready_for_human_review'


def test_total_return_series_requires_explicit_semantics(case):
    record, fixtures = case
    for endpoint in ('reference', 'actual'):
        record[endpoint]['adjustment_basis'] = 'total_return_adjusted'
    seal(record, fixtures)
    assert 'actual:value_semantics_mismatch' in assess(case)['reasons']
    for endpoint in ('reference', 'actual'):
        record[endpoint]['value_semantics'] = 'total_return_series'
        record[endpoint]['corporate_action_treatment'] = 'synthetic_reinvestment'
    fixtures['ledger']['forecasts'][record['forecast_id']]['reference_metadata'] = deepcopy(record['reference'])
    seal(record, fixtures)
    assert assess(case)['assessment_status'] == 'ready_for_human_review'


def test_both_endpoints_cannot_replace_frozen_reference_vintage(case):
    record, fixtures = case
    for name in ('reference', 'actual'):
        record[name]['series_vintage'] = 'substituted-vintage'
    seal(record, fixtures)
    assert 'ledger_binding:reference_metadata' in assess(case)['reasons']


def test_provenance_rights_and_review_gates_are_independent(case):
    case[0]['rights_declaration'] = 'denied'
    case[0]['review_state'] = 'pending'
    result = assess(case)
    assert result['provenance_status'] == 'synthetic_consistent'
    assert result['rights_status'] == 'denied'
    assert result['review_status'] == 'pending'
    assert result['assessment_status'] == 'blocked'


@pytest.mark.parametrize('raw', [b'{bad-json', b'{"synthetic":true,"synthetic":false}', b'\xff', b'{"extra":NaN}'])
def test_invalid_or_duplicate_evidence_json_blocks(case, raw):
    record, fixtures = case
    fixtures['evidence'][record['evidence_fixture_id']] = raw
    record['evidence_sha256'] = hashlib.sha256(raw).hexdigest()
    assert 'evidence_fixture_invalid_json' in assess(case)['reasons']


def test_deep_evidence_json_returns_blocked_without_recursion_error(case):
    record, fixtures = case
    raw = b'[' * 2000 + b'0' + b']' * 2000
    fixtures['evidence'][record['evidence_fixture_id']] = raw
    record['evidence_sha256'] = hashlib.sha256(raw).hexdigest()
    result = assess(case)
    assert result['assessment_status'] == 'blocked'
    assert result['reasons'] == ['evidence_fixture_invalid_json']
    assert assess(case) == result


def test_recursive_frozen_metadata_comparison_returns_blocked(case):
    record, fixtures = case
    # Separately allocated self-references must not escape the bounded API.
    record['reference']['extra'] = record['reference']
    frozen = fixtures['ledger']['forecasts'][record['forecast_id']]['reference_metadata']
    frozen['extra'] = frozen
    result = assess(case)
    assert result['assessment_status'] == 'blocked'
    assert result['reasons'] == ['malformed_input']


@pytest.mark.parametrize('field', ['forecast_id', 'ledger_revision', 'reference', 'actual',
                                   'rights_declaration', 'review_state', 'evidence_fixture_id'])
def test_missing_required_record_fields_block(case, field):
    del case[0][field]
    assert assess(case)['assessment_status'] == 'blocked'


@pytest.mark.parametrize('field', ['ledger', 'instruments', 'calendar', 'evidence'])
def test_missing_fixture_objects_block(case, field):
    del case[1][field]
    assert assess(case)['assessment_status'] == 'blocked'


def test_exchange_class_is_only_a_simulated_declaration(case):
    record, fixtures = case
    for endpoint in ('reference', 'actual'):
        record[endpoint]['source_class'] = 'exchange_certified_close'
    fixtures['ledger']['forecasts'][record['forecast_id']]['reference_metadata'] = deepcopy(record['reference'])
    seal(record, fixtures)
    assert assess(case)['provenance_status'] == 'synthetic_consistent'
    assert assess(case)['rights_status'] == 'unverified'


@pytest.mark.parametrize('record,fixtures,review', [
    (None, {}, REVIEW), ({}, {}, REVIEW), ([], {}, REVIEW),
    ({'schema_version': 2}, [], REVIEW), ({'schema_version': 2}, {}, '2026-10-10'),
])
def test_malformed_inputs_are_bounded_and_deterministic(record, fixtures, review):
    one = outcome.assess_outcome(record, fixtures=fixtures, review_at=review)
    assert one['assessment_status'] == 'blocked'
    assert one == outcome.assess_outcome(record, fixtures=fixtures, review_at=review)
    assert one['reasons'] == sorted(set(one['reasons']))


def test_legacy_record_is_unverifiable_without_dispatch(case, monkeypatch):
    from harness import forecast_review
    monkeypatch.setattr(forecast_review, 'evaluate_row', lambda *args: pytest.fail('v1 scoring dispatch'))
    result = outcome.assess_outcome({'schema_version': 1}, fixtures={}, review_at=REVIEW)
    assert result['provenance_status'] == 'legacy_unverifiable'
    assert result['assessment_status'] == 'blocked'
    assert result['reasons'] == ['legacy_v1_not_assessed']
