"""Ticket audit replays real temporary Git history, not working-tree guesses."""
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location('ticket_audit', Path(__file__).resolve().parents[1] / 'scripts/planning/build_ticket_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def commit(root, title):
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org',
        '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', title)
    return git(root, 'rev-parse', 'HEAD')


def write_ticket(root, status='planned', key='PRSG-1'):
    folder = root / 'plans/2026-10-01'
    folder.mkdir(parents=True, exist_ok=True)
    spec_path = f'plans/2026-10-01/{key}-fixture.md'
    complete = status == 'complete'
    (root / spec_path).write_text(f'# {key} — Fixture ticket\n\nDescription.\n- '+('[x]' if complete else '[ ]')+f' {key}-D1: Acceptance.\n')
    data = {'schema_version': 1, 'ticket_key': key, 'created_on': '2026-10-01', 'spec_path': spec_path,
        'objective': 'Searchable fixture description', 'status': status,
        'timezone': 'Asia/Kuala_Lumpur', 'owner': 'Lead', 'reviewer': 'Lead', 'scope_status': 'accepted',
        'base_sha': git(root, 'rev-parse', 'HEAD') if status != 'planned' else None,
        'allowed_paths': [spec_path, f'plans/2026-10-01/{key}.harness.json'], 'protected_paths': ['backend/'],
        'tags': {'type': 'feature', 'modules': ['harness'], 'owner_role': 'Lead', 'priority': 'P1',
                 'effort_size': 'S', 'effort_person_days': {'low': 1, 'high': 2}, 'impact': 'high'},
        'checks': [{'id': 'unit', 'kind': 'manual', 'status': 'passed' if complete else 'pending', 'evidence': ['pytest passed'] if complete else []}],
        'acceptance': [{'id': key+'-D1', 'description': 'Acceptance', 'status': 'done' if complete else 'pending', 'check_ids': ['unit'], 'evidence': ['Reviewed'] if complete else []}],
        'review': {'status': 'accepted' if complete else 'pending', 'evidence': ['Lead accepted'] if complete else []}}
    path = folder / (key+'.harness.json')
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, 'init', '-q')
    (tmp_path / 'README.md').write_text('Fixture repository')
    commit(tmp_path, 'Baseline')
    return tmp_path


def test_progress_completion_links_and_uncommitted_exclusion(repo):
    path = write_ticket(repo)
    first = commit(repo, 'Create plans before ticket prefixes')
    write_ticket(repo, 'in_progress')
    second = commit(repo, 'PRSG-1 Start work')
    write_ticket(repo, 'complete')
    final = commit(repo, 'PRSG-1 Complete reviewed feature')
    write_ticket(repo, 'blocked')  # dirty changes must not contaminate the published audit
    result = audit.build_audit(repo)
    row = result['tickets'][0]
    assert row['status'] == 'complete' and row['progress'] == {'done': 1, 'total': 1}
    assert [e['commit']['sha'] for e in row['history']] == [first, second, final]
    assert row['completion_commit']['sha'] == final
    assert row['completion_commit']['url'].endswith('/commit/'+final)
    assert row['spec_url'].endswith('/blob/'+final+'/plans/2026-10-01/PRSG-1-fixture.md')
    assert row['history'][0]['status'] == 'planned'
    assert row['history'][0]['acceptance'][0]['status'] == 'pending'
    assert row['history'][-1]['review']['evidence'] == ['Lead accepted']
    assert audit.build_audit(repo) == result  # reproducible; no wall-clock value


def test_prefix_only_delivery_does_not_mark_complete(repo):
    write_ticket(repo)
    commit(repo, 'Create plan')
    (repo / 'implementation.txt').write_text('Feature code')
    sha = commit(repo, 'PRSG-1 Deliver implementation')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['status'] == 'planned' and row['completion_commit'] is None
    assert row['history'][-1]['kind'] == 'delivery_commit'
    assert row['history'][-1]['commit']['sha'] == sha


def test_removed_ticket_retains_history(repo):
    path = write_ticket(repo)
    first = commit(repo, 'Create plan')
    path.unlink()
    removed = commit(repo, 'Remove plan metadata')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['status'] == 'removed'
    assert [e['commit']['sha'] for e in row['history']] == [first, removed]
    assert row['history'][-1]['kind'] == 'plan_removed'


def test_shared_activity_is_not_completed_ticket(repo):
    (repo / 'readme.md').write_text('Setup')
    commit(repo, 'PRSG-0 Set up workflow')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['ticket_key'] == 'PRSG-0' and row['status'] == 'activity_only'
    assert row['completion_commit'] is None


def test_complete_removed_clears_current_completion(repo):
    path = write_ticket(repo, 'complete')
    completed = commit(repo, 'PRSG-1 Complete')
    path.unlink()
    commit(repo, 'PRSG-1 Remove metadata')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['completion_commit'] is None and row['status'] == 'removed'
    assert row['history'][0]['commit']['sha'] == completed


def test_reopen_then_complete_again(repo):
    write_ticket(repo, 'complete')
    first = commit(repo, 'PRSG-1 Complete')
    write_ticket(repo, 'in_progress')
    commit(repo, 'PRSG-1 Reopen')
    assert audit.build_audit(repo)['tickets'][0]['completion_commit'] is None
    write_ticket(repo, 'complete')
    last = commit(repo, 'PRSG-1 Complete fix')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['completion_commit']['sha'] == last
    assert [e['commit']['sha'] for e in row['history'] if e['kind'] == 'completed'] == [first, last]


@pytest.mark.parametrize('bad', ['blank-evidence', 'duplicate-checks', 'unchecked-spec', 'spec-regression', 'missing-spec'])
def test_strict_completed_snapshot(repo, bad):
    path = write_ticket(repo, 'complete')
    spec_path = path.with_name('PRSG-1-fixture.md')
    if bad in {'spec-regression', 'missing-spec'}:
        commit(repo, 'PRSG-1 Complete')
    if bad == 'blank-evidence':
        data = json.loads(path.read_text())
        data['review']['evidence'] = ['   ']
        path.write_text(json.dumps(data))
    elif bad == 'duplicate-checks':
        data = json.loads(path.read_text())
        data['checks'] *= 2
        path.write_text(json.dumps(data))
    elif bad == 'missing-spec':
        spec_path.unlink()
    else:
        spec_path.write_text(spec_path.read_text().replace('[x]', '[ ]'))
    commit(repo, 'PRSG-1 Invalid contract')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['status'] == 'inconsistent' and row['completion_commit'] is None
    assert row['history'][-1]['kind'] == 'validation_failed'


def test_markdown_progress_recorded(repo):
    path = write_ticket(repo)
    commit(repo, 'Create plan')
    spec_path = path.with_name('PRSG-1-fixture.md')
    spec_path.write_text('# PRSG-1 — Updated title\n\nAdded validation observations.\n- [ ] PRSG-1-D1: Acceptance.\n')
    commit(repo, 'Update delivery notes')
    ticket = audit.build_audit(repo)['tickets'][0]
    assert ticket['history'][-1]['kind'] == 'spec_updated'
    assert ticket['title'] == 'Updated title'


@pytest.mark.parametrize('bad', ['broken-json', 'fake-completion'])
def test_malformed_history_retained_visibly(repo, bad):
    path = write_ticket(repo, 'complete')
    if bad == 'broken-json':
        path.write_text('{bad')
    else:
        data = json.loads(path.read_text())
        data['review']['evidence'] = []
        path.write_text(json.dumps(data))
    commit(repo, 'PRSG-1 Bad metadata')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['status'] == 'inconsistent' and row['validation_error']
    assert row['completion_commit'] is None


def test_correction_preserves_failed_checkpoint(repo):
    path = write_ticket(repo, 'complete')
    path.write_text('{bad')
    failed = commit(repo, 'PRSG-1 Invalid metadata')
    write_ticket(repo, 'complete')
    fixed = commit(repo, 'PRSG-1 Correct metadata')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['status'] == 'complete' and row['completion_commit']['sha'] == fixed
    assert row['history'][0]['commit']['sha'] == failed
    assert row['history'][0]['kind'] == 'validation_failed'


def test_markdown_edit_cannot_hide_invalid_current_manifest(repo):
    path = write_ticket(repo, 'complete')
    commit(repo, 'PRSG-1 Complete')
    path.write_text('{bad')
    commit(repo, 'PRSG-1 Break metadata')
    md = path.with_name('PRSG-1-fixture.md')
    md.write_text(md.read_text()+'\nAdditional notes.\n')
    commit(repo, 'PRSG-1 Add notes')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['status'] == 'inconsistent' and row['completion_commit'] is None


def test_markdown_regression_recovery_keeps_failed_history(repo):
    path = write_ticket(repo, 'complete')
    commit(repo, 'PRSG-1 Complete')
    md = path.with_name('PRSG-1-fixture.md')
    valid = md.read_text()
    md.write_text(valid.replace('[x]', '[ ]'))
    failed = commit(repo, 'PRSG-1 Regress checklist')
    md.write_text(valid)
    restored = commit(repo, 'PRSG-1 Restore checklist')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['status'] == 'complete' and row['completion_commit']['sha'] == restored
    assert any(e['kind'] == 'validation_failed' and e['commit']['sha'] == failed for e in row['history'])


def test_merge_records_imported_snapshot_not_hidden_branch_steps(repo):
    write_ticket(repo)
    first = commit(repo, 'Create plan')
    main = git(repo, 'branch', '--show-current')
    git(repo, 'checkout', '-qb', 'feature')
    write_ticket(repo, 'in_progress')
    hidden = commit(repo, 'PRSG-1 Branch progress')
    write_ticket(repo, 'complete')
    commit(repo, 'PRSG-1 Branch completion')
    git(repo, 'checkout', '-q', main)
    git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org',
        '-c', 'core.hooksPath=/dev/null', 'merge', '--no-ff', '-qm', 'PRSG-1 Merge delivery', 'feature')
    merged = git(repo, 'rev-parse', 'HEAD')
    result = audit.build_audit(repo)
    assert [e['commit']['sha'] for e in result['tickets'][0]['history']] == [first, merged]
    assert hidden not in [e['commit']['sha'] for e in result['tickets'][0]['history']]
    assert any('including merged branches' in note for note in result['limitations'])


def test_shallow_history_rejected(repo, tmp_path_factory):
    write_ticket(repo)
    commit(repo, 'Create plan')
    clone = tmp_path_factory.mktemp('shallow') / 'repo'
    subprocess.run(['git', 'clone', '-q', '--depth=1', repo.as_uri(), str(clone)], check=True)
    with pytest.raises(ValueError, match='Full Git history'):
        audit.build_audit(clone)


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'https://user:pass@github.com/a/b', 'https://example.org/a/b', 'https://github.com/a/b?x=1'])
def test_unsafe_repository_link(url):
    with pytest.raises(ValueError):
        audit.repository_url(url)
