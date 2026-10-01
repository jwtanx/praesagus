import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('lead_status', Path(__file__).resolve().parents[1] / 'skills/lead/scripts/status.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
NOW = datetime(2026, 10, 1, 15, tzinfo=timezone.utc)


def data(used=11):
    return dict(usedPercent=used, windowDurationMins=300,
                resetsAt=NOW.timestamp()+3600, sampled_at=NOW.isoformat())


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
    payload.update(changes)
    assert probe.evaluate(payload, '29%; discharging;', NOW)['action'] == 'unknown_stop_new_work'


def test_absent_usage_is_unknown_not_full():
    assert probe.evaluate({}, '29%; discharging;', NOW)['five_hour_remaining_percent'] is None


@pytest.mark.parametrize('text', ['', 'no battery', '101%;', '5%; 20%;'])
def test_unparseable_battery_stops(text):
    assert probe.evaluate(data(), text, NOW)['action'] == 'unknown_stop_new_work'


def test_unknown_usage_still_protects_low_battery():
    assert probe.evaluate({}, '8%; charging;', NOW)['action'] == 'save_remove_lead_schedules'
