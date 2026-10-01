import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

spec = importlib.util.spec_from_file_location('monthly_calendar', Path(__file__).resolve().parents[1] / 'scripts/daily-market-brief/monthly_calendar.py')
calendar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calendar)


def event(**changes):
    row = dict(event_id='jobs-us-2026-09', date='2026-10-02', kind='event',
               title='Payrolls', time='20:30 MYT', summary='Scheduled release', details='September jobs',
               sources=[{'label': 'BLS', 'url': 'https://www.bls.gov/schedule/'}],
               status='scheduled', change_reason='Initial schedule')
    row.update(changes)
    return row


def initial():
    return calendar.append_events(None, [event()], '2026-10', '2026-10-01T08:00:00+08:00')


def test_month_initialization_and_repeat_noop():
    old = initial()
    assert calendar.append_events(old, [event()], '2026-10', '2026-10-02T08:00:00+08:00') == old
    assert calendar.append_events(old, [], '2026-10', '2026-10-02T08:00:00+08:00') == old


def test_cancellation_appends_reason_and_preserves_old():
    old = initial()
    new = calendar.append_events(old, [event(status='cancelled', change_reason='Official cancellation notice')], '2026-10', '2026-10-02T08:00:00+08:00')
    assert new['entries'][0] == old['entries'][0]
    assert new['entries'][1]['revision'] == 2
    assert new['entries'][1]['status'] == 'cancelled'
    assert len(old['entries']) == 1


@pytest.mark.parametrize('change', ['delete', 'rewrite', 'metadata'])
def test_reject_history_mutation(change):
    old = initial()
    new = copy.deepcopy(old)
    if change == 'delete':
        new['entries'] = []
    elif change == 'rewrite':
        new['entries'][0]['title'] = 'Changed old title'
    else:
        new['notes'] = [{'text': 'changed'}]
    with pytest.raises(ValueError, match='append-only|metadata'):
        calendar.validate_calendar(new, old)


@pytest.mark.parametrize('changes', [{'status': 'cancelled', 'change_reason': ''}, {'date': '2026-11-02'}, {'sources': []}, {'sources': [{'url': 'javascript:bad'}]}, {'date': 'not-a-date'}])
def test_invalid_event(changes):
    with pytest.raises(ValueError):
        calendar.append_events(None, [event(**changes)], '2026-10', '2026-10-01T08:00:00+08:00')


def test_reject_future_rewrite_with_old_availability():
    with pytest.raises(ValueError, match='availability'):
        calendar.append_events(initial(), [event(time='21:00', change_reason='Official reschedule')], '2026-10', '2026-09-30T08:00:00+08:00')


def test_reject_naive_availability():
    with pytest.raises(ValueError, match='timezone'):
        calendar.append_events(None, [event()], '2026-10', '2026-10-01T08:00:00')


def test_reject_duplicate_ids():
    with pytest.raises(ValueError, match='duplicate'):
        calendar.append_events(None, [event(), event()], '2026-10', '2026-10-01T08:00:00+08:00')


def test_cli_initializes_once_and_rejects_invalid_update(tmp_path):
    payload = tmp_path / 'input.json'
    payload.write_text(json.dumps({'events': [event()]}))
    command = [sys.executable, str(Path(calendar.__file__)), '--month', '2026-10',
               '--input', str(payload), '--recorded-at', '2026-10-01T08:00:00+08:00',
               '--directory', str(tmp_path / 'calendar')]
    assert subprocess.run(command, capture_output=True).returncode == 0
    saved = tmp_path / 'calendar/2026-10.json'
    original = saved.read_bytes()
    repeat = subprocess.run(command, capture_output=True)
    assert repeat.returncode == 0 and b'No calendar changes' in repeat.stdout
    assert saved.read_bytes() == original
    payload.write_text(json.dumps({'events': [event(status='cancelled', change_reason='')]}))
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert saved.read_bytes() == original


@pytest.mark.parametrize('country', ['us', '', 'USA', None, 123])
def test_invalid_country_code(country):
    with pytest.raises(ValueError, match='country'):
        calendar.append_events(None, [event(country=country)], '2026-10', '2026-10-01T08:00:00+08:00')


def test_country_classification_is_append_only():
    old = initial()
    updated = calendar.append_events(old, [event(country='US', change_reason='Explicit country classification')], '2026-10', '2026-10-01T09:00:00+08:00')
    assert updated['entries'][0] == old['entries'][0]
    assert updated['entries'][1]['country'] == 'US'


def test_checked_in_calendar_has_both_countries_through_month_end():
    data = json.loads((Path(calendar.__file__).resolve().parents[2] / 'artifacts/financial-calendar/2026-10.json').read_text())
    calendar.validate_calendar(data)
    latest = {row['event_id']: row for row in data['entries']}
    for country in ('US', 'MY'):
        rows = [row for row in latest.values() if row.get('country') == country]
        assert any(row['date'] >= '2026-10-29' for row in rows)
        assert all(row['sources'] for row in rows)
