"""Exercise the actual portable commit-msg hook without changing Git config."""
from pathlib import Path
import subprocess

import pytest

HOOK = Path(__file__).resolve().parents[1] / '.githooks/commit-msg'


@pytest.fixture(autouse=True)
def isolated_repository(tmp_path, monkeypatch):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize('paths,allowed', [
    (['artifacts/daily-market-brief/report.json'], True),
    (['artifacts/daily-market-brief/nested/odd\nname.json'], True),
    (['artifacts/daily-market-brief/report.json', 'backend/main.py'], False),
    (['artifacts/daily-market-brief-other/report.json'], False),
    (['artifacts/other/report.json'], False),
    ([], False),
])
def test_report_only_exemption(tmp_path, paths, allowed):
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('{}')
        subprocess.run(['git', 'add', '--', path], check=True)
    message = tmp_path / 'message'
    message.write_text('[REPORT] 20261001 Refresh daily report\n')
    result = subprocess.run(['sh', str(HOOK), str(message)], capture_output=True)
    assert (result.returncode == 0) == allowed


@pytest.mark.parametrize('source,destination', [
    ('backend/old.json', 'artifacts/daily-market-brief/new.json'),
    ('artifacts/daily-market-brief/old.json', 'backend/new.json'),
])
def test_cross_boundary_rename_not_exempt(tmp_path, source, destination):
    old = tmp_path / source
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text('{}')
    subprocess.run(['git', 'add', '.'], check=True)
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-qm', 'Baseline'], check=True)
    new = tmp_path / destination
    new.parent.mkdir(parents=True, exist_ok=True)
    old.rename(new)
    subprocess.run(['git', 'add', '-A'], check=True)
    message = tmp_path / 'message'
    message.write_text('Move report\n')
    assert subprocess.run(['sh', str(HOOK), str(message)], capture_output=True).returncode != 0


@pytest.mark.parametrize('subject', ['PRSG-0 Add harness', 'PRSG-1 Add inbox', 'PRSG-123 Fix bug'])
def test_accept_ticket_subject(tmp_path, subject):
    message = tmp_path / 'message'
    message.write_text(subject + '\n\nDetailed body.\n')
    assert subprocess.run(['sh', str(HOOK), str(message)], capture_output=True).returncode == 0


@pytest.mark.parametrize('subject', ['', 'feat: add inbox', 'PRSG-xxx description', 'PRSG-01 description', 'PRSG-1', 'PRSG-1 ', 'PRSG-1  ', 'PRSG-1\tdescription', 'prefix PRSG-1 description', 'prsg-1 description'])
def test_reject_invalid_subject(tmp_path, subject):
    message = tmp_path / 'message'
    message.write_text(subject + '\n')
    result = subprocess.run(['sh', str(HOOK), str(message)], capture_output=True)
    assert result.returncode != 0
    assert b'PRSG-<number>' in result.stderr


def test_missing_message():
    assert subprocess.run(['sh', str(HOOK)], capture_output=True).returncode != 0


def run_hook(tmp_path, subject='PRSG-14 Validate harness filenames'):
    message = tmp_path / 'message'
    message.write_text(subject + '\n')
    return subprocess.run(['sh', str(HOOK), str(message)], capture_output=True)


def stage_harness(tmp_path, name, contents):
    target = tmp_path / 'plans/2026-10-01' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(contents)
    subprocess.run(['git', 'add', '--', str(target)], check=True)
    return target


@pytest.mark.parametrize('name,key,allowed', [
    ('PRSG-10.harness.json', 'PRSG-10', True),
    ('PRSG-11.harness.json', 'PRSG-11', True),
    ('PRSG-0.harness.json', 'PRSG-0', True),
    ('PRSG-11-dashboard-readability.harness.json', 'PRSG-11', False),
    ('PRSG-01.harness.json', 'PRSG-01', False),
    ('PRSG11.harness.json', 'PRSG-11', False),
    ('PRSG-11\n-extra.harness.json', 'PRSG-11', False),
    ('PRSG-11.harness.json', 'PRSG-10', False),
])
def test_staged_harness_filename_and_key(tmp_path, name, key, allowed):
    import json
    stage_harness(tmp_path, name, json.dumps({'ticket_key': key}))
    result = run_hook(tmp_path)
    assert (result.returncode == 0) == allowed
    if not allowed:
        assert b'Harness filename' in result.stderr or b'ticket_key' in result.stderr


@pytest.mark.parametrize('contents', ['{broken', '[]', 'null', '{}'])
def test_invalid_staged_harness(tmp_path, contents):
    stage_harness(tmp_path, 'PRSG-11.harness.json', contents)
    assert run_hook(tmp_path).returncode != 0


def test_hook_checks_index_not_unstaged_contents(tmp_path):
    target = stage_harness(tmp_path, 'PRSG-11.harness.json', '{"ticket_key":"PRSG-11"}')
    target.write_text('{broken')
    assert run_hook(tmp_path).returncode == 0
    subprocess.run(['git', 'add', '--', str(target)], check=True)
    target.write_text('{"ticket_key":"PRSG-11"}')
    assert run_hook(tmp_path).returncode != 0


def test_rename_old_harness_to_canonical(tmp_path):
    target = stage_harness(tmp_path, 'PRSG-11-description.harness.json', '{"ticket_key":"PRSG-11"}')
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-qm', 'Baseline'], check=True)
    target.rename(target.with_name('PRSG-11.harness.json'))
    subprocess.run(['git', 'add', '-A'], check=True)
    assert run_hook(tmp_path).returncode == 0


def test_deleted_obsolete_harness_does_not_block(tmp_path):
    target = stage_harness(tmp_path, 'PRSG-11-description.harness.json', '{}')
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-qm', 'Baseline'], check=True)
    target.unlink()
    subprocess.run(['git', 'add', '-A'], check=True)
    assert run_hook(tmp_path).returncode == 0


@pytest.mark.parametrize('subject,allowed', [
    ('[REPORT] 20261001 Morning report', True),
    ('[REPORT] 20240229', True),
    ('[REPORT] 20260229', False),
    ('[REPORT] 20261301', False),
    ('Update daily report', False),
    ('PRSG-1 Update daily report', False),
])
def test_report_title_rule_preserved(tmp_path, subject, allowed):
    target = tmp_path / 'artifacts/daily-market-brief/report.json'
    target.parent.mkdir(parents=True)
    target.write_text('{}')
    subprocess.run(['git', 'add', '.'], check=True)
    assert (run_hook(tmp_path, subject).returncode == 0) == allowed
