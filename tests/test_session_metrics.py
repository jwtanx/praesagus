"""Synthetic controls only; scheduled dates are fixtures, not exchange calendars."""
import copy
from datetime import date, timedelta
import math

import pytest

from harness.session_metrics import calculate_session_metrics


def fixture(count=25, **changes):
    sessions = [(date(2026, 9, 1) + timedelta(days=i)).isoformat() for i in range(count)]
    identity = dict(instrument='SYNTH-US', venue='TEST-US', currency='USD', adjustment_basis='unadjusted')
    bars = [dict(**identity, session=session, interval='1d', session_type='regular', completed=True,
                 completed_at=session+'T16:00:00Z', available_at=session+'T16:01:00Z', known_at=session+'T16:02:00Z',
                 open=100, high=110, low=90, close=100, volume=100,
                 source_version='synthetic-v1', provenance_ref='fixture:'+session, action_status='clear',
                 shortened_session=False, halted=False, reopening=False) for session in sessions]
    envelope = dict(schema_version=1, origin='synthetic', **identity, exchange_timezone='UTC',
                    source_vintage_selection=dict(method='caller-selected synthetic vintage', reference='fixture:selection'),
                    expected_sessions=sessions, target_sessions=sessions[-3:], bars=bars,
                    decision_cutoff='2026-10-01T00:00:00Z')
    envelope.update(changes)
    return envelope


def last(envelope):
    return calculate_session_metrics(envelope)['rows'][-1]


def test_formulas_and_ordinary_falling_controls_preserved_without_mutation():
    data = fixture()
    data['bars'][-1].update(open=104, close=106, high=108, low=102, volume=200)
    data['bars'][-2].update(open=100, close=100, high=100, low=100)
    data['bars'][-3].update(open=99, close=98, high=100, low=97)
    original = copy.deepcopy(data)
    result = calculate_session_metrics(data)
    assert data == original
    assert len(result['rows']) == 3
    falling, ordinary, rising = result['rows']
    assert falling['metrics']['close_return'] == pytest.approx(-.02)
    assert ordinary['metrics']['intraday'] == 0
    assert rising['metrics'] == pytest.approx(dict(gap=.04, close_return=.06,
                                                 intraday=106/104-1, range=.06, relative_volume=2))
    assert rising['status'] == 'ok'
    assert rising['provenance']['current'] == data['bars'][-1]['provenance_ref']
    assert rising['volume_baseline']['valid_count'] == 20
    assert rising['volume_baseline']['median_volume'] == 100


def test_volume_window_is_twenty_scheduled_sessions_excluding_current_and_future():
    data = fixture(count=30)
    target = data['expected_sessions'][24]
    data['target_sessions'] = [target]
    for index, bar in enumerate(data['bars']):
        bar['volume'] = 100 if 4 <= index < 24 else 999999
    data['bars'][24]['volume'] = 200
    row = last(data)
    assert row['metrics']['relative_volume'] == 2
    assert row['volume_baseline']['scheduled_sessions'] == data['expected_sessions'][4:24]
    assert len(row['provenance']['volume_baseline']) == 20
    assert data['bars'][24]['provenance_ref'] not in row['provenance']['volume_baseline']
    assert data['bars'][25]['provenance_ref'] not in row['provenance']['volume_baseline']


@pytest.mark.parametrize('history,available', [(14, False), (15, True), (20, True)])
def test_minimum_volume_history(history, available):
    data = fixture(count=history+1)
    row = last(data)
    assert row['volume_baseline']['valid_count'] == history
    assert (row['metrics']['relative_volume'] is not None) is available
    if not available:
        assert row['reasons']['relative_volume'] == ['insufficient_volume_history']


def test_missing_rows_do_not_expand_volume_window_to_older_valid_history():
    data = fixture(count=30)
    del data['bars'][9:15]  # Six missing inside final twenty scheduled sessions.
    row = last(data)
    assert row['volume_baseline']['valid_count'] == 14
    assert row['metrics']['relative_volume'] is None


def test_zero_volume_median_is_unavailable_not_division_error():
    data = fixture()
    for bar in data['bars'][:-1]:
        bar['volume'] = 0
    row = last(data)
    assert row['metrics']['relative_volume'] is None
    assert row['reasons']['relative_volume'] == ['zero_median_volume']
    assert row['status'] == 'partial'


def test_even_volume_median_and_finite_overflow_result():
    data = fixture(count=21)
    for index, bar in enumerate(data['bars'][:-1]):
        bar['volume'] = 100 if index < 10 else 200
    assert last(data)['volume_baseline']['median_volume'] == 150
    data['bars'][-1]['open'] = 5e-324
    data['bars'][-1]['low'] = 5e-324
    row = last(data)
    assert row['metrics']['intraday'] is None
    assert row['reasons']['intraday'] == ['nonfinite_calculation']
    assert all(value is None or math.isfinite(value) for value in row['metrics'].values())


def test_missing_immediate_prior_never_uses_stale_close():
    data = fixture()
    data['bars'][-3]['close'] = 109
    del data['bars'][-2]
    row = last(data)
    for metric in ('gap', 'close_return', 'range'):
        assert row['metrics'][metric] is None
        assert row['reasons'][metric] == ['missing_prior_expected_session']
    assert row['metrics']['intraday'] == 0
    assert row['provenance']['prior'] is None


def test_missing_target_and_first_session_remain_rows():
    data = fixture(count=3)
    data['target_sessions'] = data['expected_sessions']
    del data['bars'][1]
    rows = calculate_session_metrics(data)['rows']
    assert len(rows) == 3
    assert rows[0]['reasons']['gap'] == ['no_prior_expected_session']
    assert rows[1]['status'] == 'unavailable'
    assert all(value is None for value in rows[1]['metrics'].values())
    assert rows[1]['reasons']['intraday'] == ['missing_target_bar']


@pytest.mark.parametrize('field', ['completed_at', 'available_at', 'known_at'])
def test_future_target_rejected_from_calculation_but_preserved(field):
    data = fixture()
    # Cutoff within the same exchange-local session permits completion-date validation.
    data['decision_cutoff'] = data['expected_sessions'][-1]+'T16:01:30Z'
    if field == 'completed_at':
        data['bars'][-1].update(completed_at=data['expected_sessions'][-1]+'T17:00:00Z')
    elif field == 'available_at':
        data['bars'][-1]['available_at'] = data['expected_sessions'][-1]+'T17:00:00Z'
    row = last(data)
    assert row['status'] == 'unavailable'
    assert all(value is None for value in row['metrics'].values())
    reason = {'completed_at':'future_completion','available_at':'future_availability','known_at':'future_knowledge'}[field]
    assert reason in row['reasons']['intraday']


def test_future_prior_knowledge_cannot_enter_price_or_volume_baseline():
    data = fixture()
    data['bars'][-2]['known_at'] = '2026-10-02T00:00:00Z'
    row = last(data)
    assert row['metrics']['gap'] is None
    assert 'prior_future_knowledge' in row['reasons']['gap']
    assert row['volume_baseline']['valid_count'] == 19
    assert data['bars'][-2]['provenance_ref'] not in row['provenance']['volume_baseline']


@pytest.mark.parametrize('field,value,reason', [('action_status','split','action_split'),
    ('action_status','dividend','action_dividend'),('action_status','other','action_other'),
    ('action_status','uncertain','action_uncertain'),('shortened_session',True,'shortened_session'),
    ('halted',True,'halted'),('reopening',True,'reopening')])
def test_target_uncertainty_quarantines_all_metrics(field, value, reason):
    data = fixture()
    data['bars'][-1][field] = value
    row = last(data)
    assert row['status'] == 'quarantined'
    assert all(value is None for value in row['metrics'].values())
    assert row['reasons']['gap'] == [reason]


def test_prior_action_quarantines_affected_comparisons_and_excludes_volume():
    data = fixture()
    data['bars'][-2]['action_status'] = 'uncertain'
    row = last(data)
    assert row['status'] == 'quarantined'
    assert row['metrics']['close_return'] is None
    assert row['metrics']['intraday'] == 0
    assert row['metrics']['relative_volume'] == 1
    assert row['volume_baseline']['valid_count'] == 19


def test_clear_comparable_adjusted_fixture_can_calculate():
    data = fixture(adjustment_basis='caller-comparable-adjusted')
    for bar in data['bars']:
        bar['adjustment_basis'] = data['adjustment_basis']
    assert last(data)['status'] == 'ok'


def test_incomplete_bar_is_unavailable():
    data = fixture()
    data['bars'][-1]['completed'] = False
    assert last(data)['reasons']['gap'] == ['incomplete_bar']


@pytest.mark.parametrize('field,value', [('open',0),('close',-1),('high',99),('low',101),
    ('volume',-1),('volume',float('nan')),('open',float('inf')),('open',True),('close','100'),
    ('currency','MYR'),('instrument','SYNTH-OTHER'),('venue','OTHER'),('adjustment_basis','split-adjusted'),
    ('interval','snapshot'),('session_type','extended'),('completed',None),('action_status',None),
    ('halted',None),('source_version',''),('provenance_ref',''),('known_at',None),
    ('available_at','2026-09-25T16:01:00'),('completed_at','2026-09-24T16:00:00Z')])
def test_malformed_bar_rejects_envelope(field, value):
    data = fixture()
    data['bars'][-1][field] = value
    with pytest.raises(ValueError):
        calculate_session_metrics(data)


@pytest.mark.parametrize('duplicate', ['identical','conflicting','older-vintage'])
def test_multiple_session_versions_rejected_without_revision_selection(duplicate):
    data = fixture()
    extra = dict(data['bars'][-1])
    if duplicate == 'conflicting':
        extra['close'] = 101
    if duplicate == 'older-vintage':
        extra['source_version'] = 'synthetic-v0'
    data['bars'].append(extra)
    with pytest.raises(ValueError, match='resolve conflicting source vintages'):
        calculate_session_metrics(data)


def test_out_of_order_bars_rejected():
    data = fixture()
    data['bars'][0], data['bars'][1] = data['bars'][1], data['bars'][0]
    with pytest.raises(ValueError, match='ordered unique'):
        calculate_session_metrics(data)


@pytest.mark.parametrize('changes', [dict(origin='live'),dict(schema_version=True),dict(schema_version=2),
    dict(source_vintage_selection=None),dict(exchange_timezone='invalid'),dict(bars=None),
    dict(expected_sessions=[]),dict(target_sessions=[]),dict(decision_cutoff=None),
    dict(decision_cutoff='2026-10-01T00:00:00'),dict(target_sessions=['2027-01-01'])])
def test_malformed_envelope_rejected(changes):
    with pytest.raises(ValueError):
        calculate_session_metrics(fixture(**changes))


def test_synthetic_my_timezone_provenance():
    data = fixture(exchange_timezone='Asia/Kuala_Lumpur', instrument='SYNTH-MY', currency='MYR', venue='TEST-MY')
    for bar in data['bars']:
        for field in ('instrument','currency','venue'):
            bar[field] = data[field]
        for field in ('completed_at','available_at','known_at'):
            bar[field] = bar[field].replace('Z','+08:00')
    result = calculate_session_metrics(data)
    assert result['identity']['currency'] == 'MYR'
    assert result['exchange_timezone'] == 'Asia/Kuala_Lumpur'
    assert result['rows'][-1]['status'] == 'ok'


@pytest.mark.parametrize('field', ['expected_sessions', 'target_sessions'])
def test_duplicate_or_out_of_order_schedule_rejected(field):
    data = fixture()
    data[field][0], data[field][1] = data[field][1], data[field][0]
    with pytest.raises(ValueError, match='ordered and unique'):
        calculate_session_metrics(data)
    data = fixture()
    data[field].append(data[field][-1])
    with pytest.raises(ValueError, match='ordered and unique'):
        calculate_session_metrics(data)


def test_all_missing_target_rows_preserved():
    result = calculate_session_metrics(fixture(bars=[]))
    assert len(result['rows']) == 3
    assert all(row['status'] == 'unavailable' for row in result['rows'])


def test_documented_example_replayed():
    from pathlib import Path
    documentation = (Path(__file__).resolve().parents[1] / 'harness/SESSION_METRICS.md').read_text()
    code = documentation.split('```python\n')[1].split('```')[0]
    exec(compile(code, 'synthetic session metrics example', 'exec'), {})



def test_noncalendar_iso_dates_and_unhashable_action_rejected():
    data = fixture(expected_sessions=['2026-W01-1'])
    with pytest.raises(ValueError):
        calculate_session_metrics(data)
    data = fixture()
    data['bars'][-1]['action_status'] = []
    with pytest.raises(ValueError, match='action_status'):
        calculate_session_metrics(data)
