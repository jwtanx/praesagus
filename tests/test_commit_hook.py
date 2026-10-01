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
    message.write_text('Update daily report\n')
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
