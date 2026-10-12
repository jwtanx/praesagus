"""Authored synthetic oracles: no source, network, store or credentials."""
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / 'harness/engineering/price-prediction/precision_scoring.py'
spec = importlib.util.spec_from_file_location('precision_scoring', MODULE)
scoring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoring)
REVIEW = '2026-10-20T20:00:00Z'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def seal(packet):
    packet['forecast_bindings'] = {}
    packet['outcome_bindings'] = {}
    contract_hash = digest(packet['contract'])
    for key, opportunity in packet['opportunities'].items():
        f = opportunity['forecast']
        if f is not None:
            f['contract_sha256'] = contract_hash
            packet['forecast_bindings'][key] = digest(f)
        outcome = opportunity['outcome']
        if outcome and outcome['kind'] == 'eligible':
            outcome['contract_sha256'] = contract_hash
            outcome['forecast_sha256'] = packet['forecast_bindings'][key]
            packet['outcome_bindings'][key] = digest(outcome)
    return packet


def packet_with(n=1):
    contract = dict(cohort_id='synthetic-cohort', instrument_id='SYNTH', market='US', mic='XNAS',
                    currency='USD', unit='price_unit', basis='unadjusted', value_semantics='traded_close_series',
                    scale_id='frozen-scale', calendar_version='synthetic-calendar-v1', instrument_version='synthetic-listing-v1',
                    method_id='authored-candidate', method_version='v1',
                    interval_baseline_id='authored_zero_drift_interval_v1', horizon_sessions=1, alpha=.05)
    packet = dict(schema_version=1, synthetic=True, classification='synthetic_only', contract=contract,
                  scheduled_total=n, schedule=[], opportunities={}, forecast_bindings={}, outcome_bindings={})
    for i in range(n):
        target = date(2026, 10, 10) + timedelta(days=i)
        reference = target - timedelta(days=1)
        prior = reference - timedelta(days=1)
        key = f'synthetic-{i}'
        close = target.isoformat() + 'T20:00:00Z'
        issue = reference.isoformat() + 'T21:00:00Z'
        f = dict(opportunity_id=key, contract_sha256='', issued_at=issue, forecast_vintage='frozen-issuance',
                 reference_session=reference.isoformat(), reference_close_at=reference.isoformat()+'T20:00:00Z',
                 reference_known_at=reference.isoformat()+'T20:30:00Z', prior_close_at=prior.isoformat()+'T20:00:00Z',
                 prior_known_at=prior.isoformat()+'T20:30:00Z', reference=100, prior_close=99, candidate_point=110,
                 candidate_direction='up', baseline_direction='up', candidate_interval=dict(low=100, high=120),
                 baseline_interval=dict(low=90, high=110), interval_construction='authored_not_verified')
        outcome = dict(kind='eligible', opportunity_id=key, contract_sha256='', forecast_sha256='',
                       outcome_vintage='later-outcome', scale_id='frozen-scale', close_at=close,
                       available_at=close, known_at=close, actual=110)
        packet['schedule'].append(dict(opportunity_id=key, target_session=target.isoformat(),
                                       target_close_at=close, scheduled_at=issue))
        packet['opportunities'][key] = dict(disposition='issued', decision_at=issue, reason_code=None,
                                            forecast=f, outcome=outcome)
    return seal(packet)


@pytest.fixture
def packet():
    return packet_with()


def evaluate(packet, review=REVIEW):
    original = deepcopy(packet)
    result = scoring.score_cohort(packet, review_at=review)
    assert packet == original
    json.dumps(result, allow_nan=False)
    assert set(result) == {'schema_version', 'synthetic_only', 'classification', 'source_eligibility',
                           'rights_status', 'invalid', 'review_at', 'contract', 'reasons', 'counts',
                           'operational', 'metrics', 'rows', 'limitations'}
    assert result['synthetic_only'] is True
    assert result['source_eligibility'] == 'not_assessed'
    assert result['rights_status'] == 'unverified'
    return result


def rejected(packet, reason, review=REVIEW):
    result = evaluate(packet, review)
    assert result['invalid'] is True
    assert reason in result['reasons']
    assert result['reasons'] == sorted(set(result['reasons']))
    assert result['contract'] is result['counts'] is result['operational'] is result['metrics'] is None
    assert result['rows'] == []
    return result


def test_perfect_candidate_matched_losses_and_inclusive_intervals(packet):
    result = evaluate(packet)
    assert not result['invalid']
    point = result['metrics']['point']
    assert point['candidate_log_mae'] == point['candidate_mae'] == point['candidate_rmse'] == 0
    assert point['baseline_log_mae'] == pytest.approx(100 * math.log(1.1))
    assert point['mean_log_loss_delta'] == pytest.approx(-100 * math.log(1.1))
    assert point['baseline_mae'] == point['baseline_rmse'] == 10
    assert point['paired_count'] == result['metrics']['interval']['paired_count'] == 1
    assert result['metrics']['direction']['matched'] == dict(eligible_count=1, hits={'candidate': 1, 'baseline': 1},
                                                            realized_zero_count=0, hit_fraction={'candidate': 1., 'baseline': 1.}, coverage_fraction=1.)
    for method in ('candidate', 'baseline'):
        assert result['metrics']['interval'][method] == dict(covered=1, lower_misses=0, upper_misses=0,
                                                             coverage_fraction=1., mean_normalized_width=.2, mean_interval_score=20.)
    assert result['counts'] == dict(scheduled=1, source_gate_abstention=0, issuance_failure=0,
                                   issued_pending=0, mature_missing_outcome=0, scored=1, issued=1, mature_issued=1)


@pytest.mark.parametrize('actual,candidate,delta_sign', [(110, 110, -1), (110, 100, 0), (100, 120, 1), (90, 90, -1)])
def test_primary_delta_sign(packet, actual, candidate, delta_sign):
    o = packet['opportunities']['synthetic-0']
    o['outcome']['actual'], o['forecast']['candidate_point'] = actual, candidate
    result = evaluate(seal(packet))
    delta = result['metrics']['point']['mean_log_loss_delta']
    assert (delta > 0) - (delta < 0) == delta_sign


@pytest.mark.parametrize('actual,covered,lower,upper,score', [(100, True, False, False, 20),
    (120, True, False, False, 20), (90, False, True, False, 420), (130, False, False, True, 420)])
def test_interval_endpoints_and_proper_penalties(packet, actual, covered, lower, upper, score):
    packet['opportunities']['synthetic-0']['outcome']['actual'] = actual
    row = evaluate(seal(packet))['rows'][0]['losses']['candidate_interval']
    assert row == dict(covered=covered, lower_miss=lower, upper_miss=upper,
                      normalized_width=.2, interval_score=score)


def test_wider_interval_has_higher_score_when_both_cover(packet):
    first = evaluate(packet)['metrics']['interval']['candidate']['mean_interval_score']
    packet['opportunities']['synthetic-0']['forecast']['candidate_interval'] = dict(low=90, high=130)
    second = evaluate(seal(packet))['metrics']['interval']['candidate']
    assert second['coverage_fraction'] == 1.
    assert second['mean_interval_score'] > first
    assert second['mean_normalized_width'] == .4


@pytest.mark.parametrize('direction,prior,baseline', [('up', 99, 'up'), ('down', 101, 'down'),
                                                     ('flat', 100, 'abstain'), ('abstain', 100, 'abstain')])
def test_realized_zero_misses_and_excluded_direction(packet, direction, prior, baseline):
    f = packet['opportunities']['synthetic-0']['forecast']
    f.update(candidate_direction=direction, prior_close=prior, baseline_direction=baseline)
    packet['opportunities']['synthetic-0']['outcome']['actual'] = 100
    result = evaluate(seal(packet))
    direction_result = result['metrics']['direction']['candidate']
    included = direction in ('up', 'down')
    assert direction_result == dict(eligible_count=int(included), hits=0, realized_zero_count=int(included),
                                   hit_fraction=0. if included else None, coverage_fraction=1. if included else 0.)
    assert result['rows'][0]['losses']['realized_zero'] is True
    assert result['metrics']['point']['paired_count'] == 1


def test_zero_direction_intersection_has_zero_coverage_but_null_hit_fraction():
    packet = packet_with(2)
    first, second = packet['opportunities'].values()
    first['forecast'].update(prior_close=100, baseline_direction='abstain', candidate_direction='up')
    second['forecast'].update(candidate_direction='abstain', baseline_direction='up')
    result = evaluate(seal(packet))['metrics']['direction']
    assert result['candidate']['coverage_fraction'] == result['baseline']['coverage_fraction'] == .5
    assert result['matched'] == dict(eligible_count=0, hits={'candidate': 0, 'baseline': 0}, realized_zero_count=0,
                                     hit_fraction=None, coverage_fraction=0.)


@pytest.mark.parametrize('candidate_direction', ['flat', 'abstain'])
def test_all_excluded_direction_coverage_is_zero_not_null(packet, candidate_direction):
    packet['opportunities']['synthetic-0']['forecast'].update(candidate_direction=candidate_direction,
                                                              prior_close=100, baseline_direction='abstain')
    result = evaluate(seal(packet))['metrics']['direction']
    for method in result.values():
        assert method['eligible_count'] == 0
        assert method['coverage_fraction'] == 0.
        assert method['hit_fraction'] is None


def test_empty_cohort_null_metrics_and_denominators():
    result = evaluate(packet_with(0))
    assert not result['invalid']
    assert all(v == 0 for v in result['counts'].values())
    assert result['operational']['issuance_coverage']['fraction'] is None
    assert result['operational']['outcome_completion']['fraction'] is None
    assert all(v is None for k, v in result['metrics']['point'].items() if k != 'paired_count')
    assert all(v['coverage_fraction'] is None for v in result['metrics']['direction'].values())


def test_operational_partition_and_distinct_missing_reason():
    packet = packet_with(6)
    first, second, third, fourth, fifth, sixth = packet['opportunities'].values()
    first.update(disposition='source_gate_abstention', reason_code='synthetic_source_blocked', forecast=None, outcome=None)
    second.update(disposition='issuance_failure', reason_code='synthetic_issuance_failed', forecast=None, outcome=None)
    third['outcome'] = None
    fourth['outcome'] = dict(kind='unavailable', reason_code='ineligible', known_at='2026-10-13T20:00:00Z')
    sixth['outcome'] = None
    review = '2026-10-15T19:59:59Z'
    result = evaluate(seal(packet), review)
    assert not result['invalid']
    assert result['counts'] == dict(scheduled=6, source_gate_abstention=1, issuance_failure=1,
                                   issued_pending=1, mature_missing_outcome=2, scored=1, issued=4, mature_issued=3)
    assert result['operational'] == dict(issuance_coverage=dict(numerator=4, denominator=6, fraction=4/6),
                                         outcome_completion=dict(numerator=1, denominator=3, fraction=1/3))
    assert result['rows'][2]['missing_reason'] == 'absent'
    assert result['rows'][3]['missing_reason'] == 'ineligible'
    assert result['metrics']['point']['paired_count'] == 1


@pytest.mark.parametrize('review,state', [('2026-10-10T19:59:59.999Z', 'issued_pending'),
                                         ('2026-10-10T20:00:00Z', 'mature_missing_outcome')])
def test_exact_close_maturity_without_outcome(packet, review, state):
    packet['opportunities']['synthetic-0']['outcome'] = None
    result = evaluate(seal(packet), review)
    assert result['rows'][0]['state'] == state
    assert result['metrics']['point']['paired_count'] == 0


def test_late_outcome_available_exactly_at_review_and_separate_vintage(packet):
    old_forecast_hash = packet['forecast_bindings']['synthetic-0']
    outcome = packet['opportunities']['synthetic-0']['outcome']
    outcome.update(available_at=REVIEW, known_at=REVIEW, outcome_vintage='independent-later-vintage')
    result = evaluate(seal(packet))
    assert not result['invalid']
    assert packet['forecast_bindings']['synthetic-0'] == old_forecast_hash
    assert result['rows'][0]['state'] == 'scored'


@pytest.mark.parametrize('field,value', [('available_at', '2026-10-10T19:59:59Z'),
    ('available_at', '2026-10-21T20:00:00Z'), ('known_at', '2026-10-10T19:59:59Z'),
    ('close_at', '2026-10-10T20:00:00.001Z')])
def test_invalid_outcome_time_never_becomes_missing(packet, field, value):
    packet['opportunities']['synthetic-0']['outcome'][field] = value
    rejected(seal(packet), 'outcome_time')


def test_future_actual_before_target_maturity_rejected(packet):
    rejected(packet, 'outcome_time', '2026-10-10T19:59:59Z')


@pytest.mark.parametrize('field,value', [('issued_at', '2026-10-10T20:00:00Z'),
    ('reference_known_at', '2026-10-09T21:00:00.001Z'), ('prior_known_at', '2026-10-09T21:00:00.001Z'),
    ('reference_close_at', '2026-10-10T20:00:00Z'), ('prior_close_at', '2026-10-09T20:00:00Z'),
    ('reference_session', '2026-10-10')])
def test_future_or_inconsistent_forecast(packet, field, value):
    packet['opportunities']['synthetic-0']['forecast'][field] = value
    rejected(seal(packet), 'forecast_time')


def test_issuance_exact_target_is_forbidden(packet):
    o = packet['opportunities']['synthetic-0']
    o['decision_at'] = o['forecast']['issued_at'] = '2026-10-10T20:00:00Z'
    rejected(seal(packet), 'forecast_time')


@pytest.mark.parametrize('mutation,reason', [
    (lambda p: p['schedule'][0].update(scheduled_at='2026-10-21T19:00:00Z'), 'schedule_not_due'),
    (lambda p: p['schedule'].append(deepcopy(p['schedule'][0])), 'schedule_identity'),
    (lambda p: p.update(scheduled_total=0), 'schedule_membership'),
    (lambda p: p['opportunities'].update({'other': p['opportunities'].pop('synthetic-0')}), 'schedule_membership'),
    (lambda p: p['opportunities']['synthetic-0'].update(disposition='scored'), 'opportunity_state'),
    (lambda p: p['opportunities']['synthetic-0'].update(decision_at='2026-10-09T20:59:59Z'), 'opportunity_state'),
    (lambda p: p['opportunities']['synthetic-0']['forecast'].update(baseline_direction='down'), 'baseline_direction'),
    (lambda p: p['opportunities']['synthetic-0']['forecast']['candidate_interval'].update(low=121), 'opportunity_state'),
    (lambda p: p['opportunities']['synthetic-0']['outcome'].update(scale_id='different'), 'outcome_scale'),
])
def test_identity_state_and_scale_fail_closed(packet, mutation, reason):
    mutation(packet)
    rejected(seal(packet), reason)


def test_same_target_duplicate_alias_rejected():
    packet = packet_with(2)
    packet['schedule'][1]['target_session'] = packet['schedule'][0]['target_session']
    rejected(packet, 'schedule_identity')


@pytest.mark.parametrize('where', ['forecast', 'outcome', 'contract'])
def test_tampering_without_resealing_rejected(packet, where):
    if where == 'contract':
        packet['contract']['method_version'] = 'altered'
    elif where == 'forecast':
        packet['opportunities']['synthetic-0']['forecast']['candidate_point'] = 115
    else:
        packet['opportunities']['synthetic-0']['outcome']['actual'] = 115
    rejected(packet, 'forecast_binding' if where != 'outcome' else 'outcome_binding')


@pytest.mark.parametrize('which', ['forecast_bindings', 'outcome_bindings'])
@pytest.mark.parametrize('action', ['missing', 'extra', 'malformed'])
def test_binding_membership_and_digest_shape(packet, which, action):
    if action == 'missing':
        packet[which].clear()
    elif action == 'extra':
        packet[which]['extra'] = 'a' * 64
    else:
        packet[which]['synthetic-0'] = 'A' * 64
    rejected(packet, 'forecast_binding' if which == 'forecast_bindings' else 'outcome_binding')


@pytest.mark.parametrize('mutation', [lambda p: p.update(extra=1), lambda p: p['contract'].update(extra=1),
    lambda p: p['schedule'][0].update(extra=1), lambda p: p['opportunities']['synthetic-0'].update(extra=1),
    lambda p: p['opportunities']['synthetic-0']['forecast'].update(baseline_point=100),
    lambda p: p['opportunities']['synthetic-0']['forecast']['candidate_interval'].update(extra=1),
    lambda p: p['opportunities']['synthetic-0']['outcome'].update(extra=1),
    lambda p: p.update(schema_version=True), lambda p: p.update(scheduled_total=True),
    lambda p: p['contract'].update(horizon_sessions=True), lambda p: p.update(schedule=()),
    lambda p: p['opportunities']['synthetic-0'].update(forecast=[]),
    lambda p: p['opportunities']['synthetic-0'].update(outcome={'kind': 'wrong'}),
])
def test_exact_schema_and_type_rejection(packet, mutation):
    mutation(packet)
    rejected(packet, 'schema')


@pytest.mark.parametrize('number', [True, False, None, '100', float('nan'), float('inf'), -1, 0,
                                   1e-101, 1e101, 10**400])
@pytest.mark.parametrize('field', ['reference', 'candidate_point', 'actual', 'interval_low'])
def test_numeric_domain_rejects_nonfinite_bool_and_extremes(packet, number, field):
    o = packet['opportunities']['synthetic-0']
    if field == 'actual':
        o['outcome']['actual'] = number
    elif field == 'interval_low':
        o['forecast']['candidate_interval']['low'] = number
    else:
        o['forecast'][field] = number
    # Invalid numeric fixtures deliberately cannot be canonically resealed.
    rejected(packet, 'numeric_domain')


@pytest.mark.parametrize('review', ['2026-10-20', '2026-10-20T20:00:00+00:00', '2026-10-20T20:00:00.1Z',
                                   '2026-02-30T20:00:00Z', '2026-10-20T20:00:60Z', None])
def test_explicit_strict_utc_review_required(packet, review):
    result = rejected(packet, 'timestamp', review)
    assert result['review_at'] is None


@pytest.mark.parametrize('mutation,reason', [(lambda p: p.update(synthetic=False), 'not_synthetic'),
    (lambda p: p.update(classification='real'), 'not_synthetic'),
    (lambda p: p.update(schema_version=2), 'unsupported_version'),
    (lambda p: p['contract'].update(alpha=.1), 'contract'),
    (lambda p: p['contract'].update(alpha=True), 'numeric_domain'),
    (lambda p: p['contract'].update(alpha=10**400), 'numeric_domain'),
    (lambda p: p['contract'].update(horizon_sessions=2), 'contract'),
    (lambda p: p['contract'].update(basis='total_return_adjusted'), 'contract'),
    (lambda p: p['contract'].update(currency='usd'), 'contract'),
    (lambda p: p['contract'].update(mic='US'), 'contract'),
    (lambda p: p['contract'].update(method_id='bad id'), 'contract')])
def test_synthetic_only_contract_enforcement(packet, mutation, reason):
    mutation(packet)
    rejected(packet, reason)


def test_first_stage_error_policy_prevents_selective_partial_summary(packet):
    packet['opportunities']['synthetic-0']['forecast']['reference'] = 0
    packet['schedule'][0]['scheduled_at'] = '2026-10-21T19:00:00Z'
    result = rejected(packet, 'numeric_domain')
    assert result['reasons'] == ['numeric_domain']


def test_empty_schedule_cannot_hide_nonempty_bindings():
    packet = packet_with(0)
    packet['forecast_bindings']['extra'] = 'a' * 64
    rejected(packet, 'forecast_binding')


@pytest.mark.parametrize('reason', ['absent', 'ineligible'])
def test_unavailable_outcomes_preserve_reason(packet, reason):
    packet['opportunities']['synthetic-0']['outcome'] = dict(kind='unavailable', reason_code=reason,
                                                           known_at='2026-10-10T20:00:00Z')
    result = evaluate(seal(packet))
    assert result['rows'][0]['missing_reason'] == reason
    assert result['operational']['outcome_completion']['fraction'] == 0.


def test_positive_numeric_extremes_remain_finite(packet):
    f = packet['opportunities']['synthetic-0']['forecast']
    f.update(reference=1e-100, prior_close=1e-100, baseline_direction='abstain', candidate_point=1e100,
             candidate_interval=dict(low=1e-100, high=1e100), baseline_interval=dict(low=1e-100, high=1e100))
    packet['opportunities']['synthetic-0']['outcome']['actual'] = 1e100
    result = evaluate(seal(packet))
    assert not result['invalid']
    assert result['metrics']['point']['candidate_log_mae'] == 0
    assert result['metrics']['interval']['candidate']['mean_normalized_width'] == pytest.approx(1e200)
    assert math.isfinite(result['metrics']['point']['baseline_rmse'])


def test_near_equal_and_log_region_oracles(packet):
    for actual in (50, math.nextafter(50., 0.), 200, math.nextafter(200., math.inf),
                   math.nextafter(100., math.inf)):
        o = packet['opportunities']['synthetic-0']
        o['outcome']['actual'] = o['forecast']['candidate_point'] = actual
        point = evaluate(seal(packet))['metrics']['point']
        assert point['candidate_log_mae'] == 0
        oracle = (100 * math.log1p((actual - 100) / 100) if 50 <= actual <= 200
                  else 100 * (math.log(actual) - math.log(100)))
        assert point['baseline_log_mae'] == pytest.approx(abs(oracle), rel=1e-12, abs=1e-10)


def test_scale_effects_and_total_return_series_label(packet):
    before = evaluate(packet)['metrics']
    f, outcome = packet['opportunities']['synthetic-0']['forecast'], packet['opportunities']['synthetic-0']['outcome']
    for field in ('reference', 'prior_close', 'candidate_point'):
        f[field] *= 10
    for bounds in (f['candidate_interval'], f['baseline_interval']):
        bounds['low'] *= 10; bounds['high'] *= 10
    outcome['actual'] *= 10
    packet['contract'].update(basis='total_return_adjusted', value_semantics='total_return_series', unit='series_unit')
    after = evaluate(seal(packet))
    assert after['metrics']['point']['mean_log_loss_delta'] == pytest.approx(before['point']['mean_log_loss_delta'])
    assert after['metrics']['point']['baseline_mae'] == 10 * before['point']['baseline_mae']
    assert after['metrics']['point']['baseline_rmse'] == 10 * before['point']['baseline_rmse']
    assert after['metrics']['interval']['candidate']['mean_normalized_width'] == before['interval']['candidate']['mean_normalized_width']
    assert after['metrics']['interval']['candidate']['mean_interval_score'] == 10 * before['interval']['candidate']['mean_interval_score']
    assert 'adjusted series is not an executable target' in after['limitations']


def test_canonical_order_and_output_isolation():
    packet = packet_with(3)
    result = evaluate(packet)
    packet['schedule'].reverse()
    for field in ('opportunities', 'forecast_bindings', 'outcome_bindings'):
        packet[field] = dict(reversed(list(packet[field].items())))
    assert evaluate(packet) == result
    original = deepcopy(packet)
    result['contract']['method_id'] = 'changed-output'
    result['rows'][0]['losses']['candidate_interval']['interval_score'] = -999
    result['limitations'].clear()
    assert packet == original


def test_unavailable_and_failure_states_cannot_smuggle_forecasts(packet):
    packet['opportunities']['synthetic-0'].update(disposition='issuance_failure', reason_code='synthetic_issuance_failed')
    rejected(packet, 'opportunity_state')


def test_resource_budgets_and_cycles(packet):
    oversized = deepcopy(packet); oversized['contract']['method_id'] = 'a' * 129
    rejected(oversized, 'resource_limit')
    deep = {}; child = deep
    for _ in range(10):
        child['next'] = {}; child = child['next']
    result = scoring.score_cohort(deep, review_at=REVIEW)
    assert result['reasons'] == ['resource_limit']
    cycle = {}; cycle['self'] = cycle
    assert scoring.score_cohort(cycle, review_at=REVIEW)['reasons'] == ['resource_limit']
    assert scoring.score_cohort([None] * 250001, review_at=REVIEW)['reasons'] == ['resource_limit']
    large = packet_with(1001)
    # Reference/schedule dates are authored and not exchange-calendar assertions.
    rejected(large, 'resource_limit', '2030-01-01T00:00:00Z')


def test_1000_complete_opportunities_fit_declared_resource_bound():
    packet = packet_with(1000)
    result = evaluate(packet, '2030-01-01T00:00:00Z')
    assert not result['invalid']
    assert result['counts']['scored'] == 1000


def test_subclasses_nonstring_keys_and_nonjson_objects_rejected(packet):
    class Derived(dict):
        pass
    rejected(Derived(packet), 'schema')
    packet[1] = 'bad-key'
    rejected(packet, 'schema')
    assert scoring.score_cohort(object(), review_at=REVIEW)['reasons'] == ['schema']


def test_numeric_guard_rejects_nonfinite_arithmetic_without_partial_output(packet, monkeypatch):
    # Defensive arithmetic failure, not unsupported real data admission.
    monkeypatch.setattr(scoring.math, 'log1p', lambda value: float('inf'))
    rejected(packet, 'numeric_overflow')


def test_budget_failure_is_order_independent_and_precedes_schema():
    deep = {}; child = deep
    for _ in range(10):
        child['next'] = {}; child = child['next']
    a = dict(deep=deep, invalid=object())
    b = dict(reversed(list(a.items())))
    assert scoring.score_cohort(a, review_at=REVIEW) == scoring.score_cohort(b, review_at=REVIEW)
    assert scoring.score_cohort(a, review_at=REVIEW)['reasons'] == ['resource_limit']


def test_invalid_forecast_time_and_baseline_reasons_are_sorted_independently():
    packet = packet_with(2)
    for opportunity in packet['opportunities'].values():
        opportunity['forecast'].update(reference_known_at=REVIEW, baseline_direction='down')
    seal(packet)
    first = evaluate(packet)
    packet['schedule'].reverse()
    packet['opportunities'] = dict(reversed(list(packet['opportunities'].items())))
    assert evaluate(packet) == first
    assert first['reasons'] == ['baseline_direction', 'forecast_time']


def test_strict_metadata_and_outcome_id_bindings(packet):
    outcome = packet['opportunities']['synthetic-0']['outcome']
    outcome['opportunity_id'] = 'another-opportunity'
    rejected(seal(packet), 'outcome_binding')


def test_prior_zero_requires_abstain_not_flat(packet):
    packet['opportunities']['synthetic-0']['forecast'].update(prior_close=100, baseline_direction='flat')
    rejected(seal(packet), 'baseline_direction')


def test_independent_direction_does_not_infer_from_point(packet):
    packet['opportunities']['synthetic-0']['forecast'].update(candidate_point=90, candidate_direction='up')
    result = evaluate(seal(packet))
    assert not result['invalid']
    assert result['rows'][0]['losses']['candidate_direction_hit'] is True
    assert result['metrics']['point']['candidate_mae'] == 20


def test_point_rmse_uses_same_rows_as_baseline_with_hand_computable_errors():
    packet = packet_with(2)
    first, second = packet['opportunities'].values()
    first['forecast']['candidate_point'] = 107
    second['forecast']['candidate_point'] = 106
    point = evaluate(seal(packet))['metrics']['point']
    assert point['paired_count'] == 2
    assert point['candidate_mae'] == 3.5
    assert point['candidate_rmse'] == pytest.approx(math.sqrt(12.5))
    assert point['baseline_mae'] == point['baseline_rmse'] == 10


def test_numeric_representation_changes_are_not_silently_resealed(packet):
    packet['opportunities']['synthetic-0']['forecast']['reference'] = 100.0
    rejected(packet, 'forecast_binding')


def test_equivalent_utc_precision_compares_instants_but_preserves_hash_strings(packet):
    outcome = packet['opportunities']['synthetic-0']['outcome']
    old = packet['outcome_bindings']['synthetic-0']
    outcome['close_at'] = '2026-10-10T20:00:00.000Z'
    result = evaluate(seal(packet), '2026-10-10T20:00:00.000Z')
    assert not result['invalid']
    assert packet['outcome_bindings']['synthetic-0'] != old


@pytest.mark.parametrize('field,value,reason', [('reference_session', '2026-02-30', 'timestamp'),
    ('reference_known_at', '2026-10-09T20:30:00-04:00', 'timestamp'),
    ('candidate_direction', 'sideways', 'opportunity_state'),
    ('interval_construction', 'verified', 'opportunity_state')])
def test_forecast_date_timezone_and_authored_enum_contract(packet, field, value, reason):
    packet['opportunities']['synthetic-0']['forecast'][field] = value
    rejected(seal(packet), reason)


def test_serialized_output_is_stable_after_reordering_every_input_map(packet):
    first = json.dumps(evaluate(packet), allow_nan=False)

    def reverse_maps(value):
        if type(value) is dict:
            return {key: reverse_maps(child) for key, child in reversed(list(value.items()))}
        if type(value) is list:
            return [reverse_maps(child) for child in value]
        return value

    assert json.dumps(evaluate(reverse_maps(packet)), allow_nan=False) == first
