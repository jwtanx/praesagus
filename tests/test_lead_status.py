import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('lead_status', Path(__file__).resolve().parents[1] / 'skills/lead/scripts/status.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
NOW = datetime(2026, 10, 1, 15, tzinfo=timezone.utc)


def data(used=11):
    return dict(schema_version=2, sampled_at=NOW.isoformat(), windows={
        'five_hour': dict(usedPercent=used, windowDurationMins=300, resetsAt=NOW.timestamp()+3600),
        'weekly': dict(usedPercent=11, windowDurationMins=10080, resetsAt=NOW.timestamp()+86400)})


@pytest.mark.parametrize('used,level,expected', [
    (11, 29, 'ready'), (98, 29, 'checkpoint_pause_until_reset'),
    (99, 5, 'save_remove_lead_schedules'), (11, 0, 'save_remove_lead_schedules'),
    (11, 8, 'save_remove_lead_schedules'), (99, 8, 'save_remove_lead_schedules'),
    (11, 7, 'save_remove_lead_schedules'), (11, 9, 'ready'),
    (95, 20, 'checkpoint_before_new_work'), (97.9, 20, 'checkpoint_before_new_work')])
def test_thresholds(used, level, expected):
    assert probe.evaluate(data(used), f'{level}%; charging;', NOW)['action'] == expected


@pytest.mark.parametrize('changes', [
    {'usedPercent': None}, {'usedPercent': True}, {'usedPercent': float('nan')},
    {'usedPercent': -1}, {'usedPercent': 101}, {'windowDurationMins': 10080},
    {'sampled_at': '2026-10-01T14:54:59+00:00'},
    {'sampled_at': '2026-10-01T15:01:00+00:00'}, {'sampled_at': '2026-10-01T15:00:00'},
    {'resetsAt': NOW.timestamp()-1}])
def test_invalid_usage_stops(changes):
    payload = data()
    if 'sampled_at' in changes:
        payload.update(changes)
    else:
        payload['windows']['five_hour'].update(changes)
    assert probe.evaluate(payload, '29%; discharging;', NOW)['action'] == 'unknown_stop_new_work'


def test_absent_usage_is_unknown_not_full():
    assert probe.evaluate({}, '29%; discharging;', NOW)['five_hour_remaining_percent'] is None


@pytest.mark.parametrize('text', ['', 'no battery', '101%;', '5%; 20%;'])
def test_unparseable_battery_stops(text):
    assert probe.evaluate(data(), text, NOW)['action'] == 'unknown_stop_new_work'


def test_unknown_usage_still_protects_low_battery():
    assert probe.evaluate({}, '8%; charging;', NOW)['action'] == 'save_remove_lead_schedules'


@pytest.mark.parametrize('five,weekly,action', [
    (20,98,'checkpoint_pause_until_reset'), (98,20,'checkpoint_pause_until_reset'),
    (98,98,'checkpoint_pause_until_reset'), (20,95,'checkpoint_before_new_work'),
    (95,20,'checkpoint_before_new_work'), (20,94.9,'ready'), (20,97.9,'checkpoint_before_new_work')])
def test_both_window_thresholds(five,weekly,action):
    payload=data(five);payload['windows']['weekly']['usedPercent']=weekly
    result=probe.evaluate(payload,'29%; charging;',NOW)
    assert result['action']==action and result['weekly_remaining_percent']==100-weekly


def test_latest_constraining_reset_ceiling_plus_120():
    payload=data(98);payload['windows']['weekly'].update(usedPercent=99,resetsAt=NOW.timestamp()+86400.25)
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['constraining_windows']==['five_hour','weekly']
    assert result['recovery_epoch']==int(NOW.timestamp())+86521 and result['recovery_status']=='ready'
    assert result['reset_epoch']==NOW.timestamp()+3600
    assert result['weekly_reset_epoch']==NOW.timestamp()+86400.25


def test_only_constraining_reset_used():
    result=probe.evaluate(data(98),'29%;',NOW)
    assert result['constraining_windows']==['five_hour']
    assert result['recovery_epoch']==NOW.timestamp()+3720


@pytest.mark.parametrize('reset',[None,True,float('nan'),float('inf'),NOW.timestamp(),NOW.timestamp()-1,1e100,'tomorrow'])
@pytest.mark.parametrize('name',['five_hour','weekly'])
def test_low_percentage_preserved_without_valid_reset(name,reset):
    payload=data();payload['windows'][name].update(usedPercent=98,resetsAt=reset)
    result=probe.evaluate(payload,'29%;',NOW)
    assert result[name+'_remaining_percent']==2 and result['action']=='checkpoint_pause_until_reset'
    assert result['recovery_epoch'] is None and result['recovery_status']=='blocked'
    assert name+'_reset_unknown' in result['blockers']


def test_missing_reset_preserves_low():
    payload=data();payload['windows']['weekly']['usedPercent']=98
    del payload['windows']['weekly']['resetsAt']
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['weekly_remaining_percent']==2 and result['recovery_epoch'] is None


@pytest.mark.parametrize('used',[None,True,float('nan'),float('inf'),-1,101,'98'])
def test_invalid_weekly_percent_unknown(used):
    payload=data();payload['windows']['weekly']['usedPercent']=used
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['weekly_remaining_percent'] is None and result['action']=='unknown_stop_new_work'
    assert result['recovery_status']=='blocked'


@pytest.mark.parametrize('duration',[True,300,10080.0,None,'10080'])
def test_wrong_weekly_duration_unknown(duration):
    payload=data();payload['windows']['weekly']['windowDurationMins']=duration
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['weekly_remaining_percent'] is None and result['recovery_status']=='blocked'


@pytest.mark.parametrize('used',[11,95,98])
def test_legacy_flat_never_ready(used):
    payload=dict(usedPercent=used,windowDurationMins=300,resetsAt=NOW.timestamp()+3600,sampled_at=NOW.isoformat())
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['five_hour_remaining_percent']==100-used and result['weekly_remaining_percent'] is None
    assert result['action']!='ready' and result['recovery_epoch'] is None
    assert result['recovery_status']=='blocked'


@pytest.mark.parametrize('change',[{'schema_version':1},{'schema_version':True},{'schema_version':3},
    {'usedPercent':98},{'windows':[]},{'windows':{'monthly':{}}}])
def test_mixed_or_unknown_schema_rejected(change):
    payload=data();payload.update(change)
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['five_hour_remaining_percent'] is None and result['weekly_remaining_percent'] is None
    assert result['action']=='unknown_stop_new_work'


@pytest.mark.parametrize('level',[0,5,8])
def test_battery_precedence_blocks_recovery(level):
    payload=data();payload['windows']['weekly']['usedPercent']=98
    result=probe.evaluate(payload,f'{level}%; charging;',NOW)
    assert result['action']=='save_remove_lead_schedules' and result['constraining_windows']==['weekly']
    assert result['recovery_epoch'] is None and result['recovery_status']=='blocked' and 'battery_low' in result['blockers']


def test_unknown_battery_keeps_low_usage_but_blocks_recovery():
    result=probe.evaluate(data(98),'unavailable',NOW)
    assert result['action']=='checkpoint_pause_until_reset' and result['five_hour_remaining_percent']==2
    assert result['recovery_epoch'] is None and 'battery_unknown' in result['blockers']


def test_unknown_nonconstraining_window_blocks_recovery():
    payload=data(98);del payload['windows']['weekly']
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['action']=='checkpoint_pause_until_reset' and result['recovery_epoch'] is None
    assert 'weekly_usage_unknown' in result['blockers']


def test_healthy_missing_reset_stops_work():
    payload=data();del payload['windows']['weekly']['resetsAt']
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['weekly_remaining_percent']==89 and result['action']=='unknown_stop_new_work'


def test_checkpoint_still_visible_with_incomplete_metadata():
    payload=data(95);del payload['windows']['weekly']
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['action']=='checkpoint_before_new_work' and result['recovery_status']=='blocked'


def test_fresh_sample_boundary_and_healthy_no_recovery():
    payload=data();payload['sampled_at']='2026-10-01T14:55:00+00:00'
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['action']=='ready' and result['blockers']==[]
    assert result['recovery_status']=='not_required' and result['recovery_epoch'] is None


def test_huge_integer_invalid_reset_does_not_erase_other_low_window():
    payload=data(98);payload['windows']['weekly']['resetsAt']=10**1000
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['five_hour_remaining_percent']==2 and result['action']=='checkpoint_pause_until_reset'
    assert result['weekly_remaining_percent']==89 and result['recovery_status']=='blocked'


def test_huge_integer_percentage_is_unknown_without_erasing_other_window():
    payload=data(98);payload['windows']['weekly']['usedPercent']=10**1000
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['five_hour_remaining_percent']==2 and result['weekly_remaining_percent'] is None
    assert result['action']=='checkpoint_pause_until_reset'


def test_legacy_low_missing_reset_stays_visible():
    payload=dict(usedPercent=98,windowDurationMins=300,sampled_at=NOW.isoformat())
    result=probe.evaluate(payload,'29%;',NOW)
    assert result['five_hour_remaining_percent']==2 and result['reset_epoch'] is None
    assert result['action']=='checkpoint_pause_until_reset' and result['recovery_status']=='blocked'
