"""Exercise the actual portable commit-msg hook without changing Git config."""
from pathlib import Path
import subprocess

import pytest

HOOK = Path(__file__).resolve().parents[1] / '.githooks/commit-msg'


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
