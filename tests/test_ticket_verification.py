from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/planning'))
import verify_ticket as runner


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args]).decode().strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.email', 'test@example.org')
    git(tmp_path, 'config', 'user.name', 'Test')
    (tmp_path / 'owned').write_text('original')
    (tmp_path / 'other').write_text('original')
    (tmp_path / 'plans/2026-10-01').mkdir(parents=True)
    spec = 'plans/2026-10-01/PRSG-15-test.md'
    (tmp_path / spec).write_text('- [ ] PRSG-15-D1: Verified\n')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'baseline')
    command = {'argv': [sys.executable, '-c', 'pass'], 'cwd': '.'}
    manifest = dict(schema_version=1, ticket_key='PRSG-15', created_on='2026-10-01',
                    timezone='Asia/Kuala_Lumpur', spec_path=spec, objective='Test',
                    status='in_progress', owner='Lead', reviewer='Lead', scope_status='accepted',
                    base_sha=git(tmp_path, 'rev-parse', 'HEAD'), allowed_paths=['owned', spec],
                    protected_paths=['protected/'], tags=dict(type='feature', modules=['harness'],
                    owner_role='Lead', priority='P1', effort_size='XS',
                    effort_person_days={'low': 0.1, 'high': 0.2}, impact='medium'),
                    checks=[dict(id='test', kind='command', status='pending', evidence=[], **command)],
                    acceptance=[dict(id='PRSG-15-D1', description='Verified', check_ids=['test'],
                    status='pending', evidence=[])], review={'status': 'pending', 'evidence': []})
    return tmp_path, manifest, [command]


def test_pass_and_hash(repo):
    root, m, policy = repo
    (root / 'owned').write_text('changed')
    result = runner.verify(root, m, policy)
    assert result['status'] == 'passed'
    assert result['changed_paths'] == ['owned']
    assert len(result['manifest_sha256']) == 64
    assert m['status'] == 'in_progress'


def test_baseline_is_exact(repo):
    root, m, policy = repo
    (root / 'other').write_text('user')
    prior = runner.baseline(root, m['base_sha'])
    (root / 'owned').write_text('change')
    assert runner.verify(root, m, policy, prior)['excluded_baseline_paths'] == ['other']
    (root / 'other').write_text('new changes')
    with pytest.raises(ValueError, match='pre-existing'):
        runner.verify(root, m, policy, prior)


def test_baseline_cannot_hide_owned(repo):
    root, m, policy = repo
    (root / 'owned').write_text('change')
    with pytest.raises(ValueError, match='ticket-owned'):
        runner.verify(root, m, policy, runner.baseline(root, m['base_sha']))


def test_baseline_detects_index_only_change(repo):
    root, m, policy = repo
    (root / 'other').write_text('prior')
    prior = runner.baseline(root, m['base_sha'])
    git(root, 'add', 'other')
    with pytest.raises(ValueError, match='pre-existing'):
        runner.verify(root, m, policy, prior)


@pytest.mark.parametrize('mode', ['untracked', 'staged', 'rename', 'deleted'])
def test_scope_rejection(repo, mode):
    root, m, policy = repo
    if mode == 'untracked':
        (root / 'new').write_text('new')
    elif mode == 'staged':
        (root / 'other').write_text('staged')
        git(root, 'add', 'other')
        (root / 'other').write_text('original')
    elif mode == 'rename':
        git(root, 'mv', 'owned', 'other-destination')
    else:
        (root / 'other').unlink()
    with pytest.raises(ValueError, match='outside ticket scope'):
        runner.verify(root, m, policy)


def test_manual_remains_pending(repo):
    root, m, policy = repo
    m['checks'].append(dict(id='review', kind='manual', status='passed', evidence=['claimed']))
    result = runner.verify(root, m, policy)
    assert result['status'] == 'needs_attention'
    assert result['checks'][-1]['status'] == 'manual_review_required'


def test_unapproved_no_execution(repo):
    root, m, policy = repo
    m['checks'][0]['argv'] = ['sh', '-c', 'touch owned']
    with pytest.raises(ValueError, match='unapproved'):
        runner.verify(root, m, policy)
    assert (root / 'owned').read_text() == 'original'


def test_failed_and_mutating_check(repo):
    root, m, policy = repo
    command = {'argv': [sys.executable, '-c', "from pathlib import Path; Path('owned').write_text('mutated'); raise SystemExit(2)"], 'cwd': '.'}
    m['checks'][0].update(command)
    result = runner.verify(root, m, [command])
    assert result['status'] == 'needs_attention'
    assert not result['worktree_unchanged']
    assert result['checks'][0]['exit_code'] == 2


def test_symlink_escape(repo):
    root, m, policy = repo
    (root / 'owned').unlink()
    (root / 'owned').symlink_to(root.parent / 'outside')
    with pytest.raises(ValueError, match='escapes'):
        runner.verify(root, m, policy)


def test_timeout_kills_process_group(repo, monkeypatch):
    root, m, policy = repo
    killed = []
    class Process:
        pid = 12345
        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired('fixture', timeout)
            return -9
    monkeypatch.setattr(runner.subprocess, 'Popen', lambda *a, **kw: Process())
    monkeypatch.setattr(runner.os, 'killpg', lambda pid, sig: killed.append((pid, sig)))
    result = runner.run_command(root, m['checks'][0], policy)
    assert result['status'] == 'timeout'
    assert killed == [(12345, runner.signal.SIGKILL)]


def test_output_not_persisted(repo):
    root, m, policy = repo
    command = {'argv': [sys.executable, '-c', "print('private-fixture-marker')"], 'cwd': '.'}
    m['checks'][0].update(command)
    result = runner.verify(root, m, [command])
    assert 'private-fixture-marker' not in str(result)
    assert result['checks'][0]['output_bytes'] > 0


def test_invalid_base_rejected(repo):
    root, m, policy = repo
    m['base_sha'] = '0' * 40
    with pytest.raises(subprocess.CalledProcessError):
        runner.verify(root, m, policy)
