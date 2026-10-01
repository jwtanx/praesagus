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


def test_explicit_decision_context_is_committed_only(repo):
    path = write_ticket(repo)
    data = json.loads(path.read_text())
    data['decision_context'] = {'purpose': 'User needs a readable explanation.',
        'approach': ['Use existing native disclosure.'], 'choices': ['Native details; external viewer.'],
        'findings': 'Recorded fixture finding.', 'tradeoffs': 'No dependency versus rich rendering.',
        'references': [{'label': 'Primary source', 'url': 'https://example.org/research'}]}
    path.write_text(json.dumps(data))
    sha = commit(repo, 'PRSG-1 Record decision context')
    data['decision_context']['purpose'] = 'Uncommitted reason must not appear'
    path.write_text(json.dumps(data))
    row = audit.build_audit(repo)['tickets'][0]
    context = row['decision_context']
    assert context['fields']['purpose'] == {'text': ['User needs a readable explanation.'], 'source': 'manifest'}
    assert context['references'] == [{'label': 'Primary source', 'url': 'https://example.org/research'}]
    assert context['spec_url'].startswith('https://github.com/jwtanx/praesagus/blob/'+sha+'/')
    assert 'Uncommitted reason' not in json.dumps(row)


def test_legacy_named_sections_and_markdown_only_update(repo):
    path = write_ticket(repo)
    md = path.with_name('PRSG-1-fixture.md')
    md.write_text(md.read_text()+'\n## Why the ticket is created?\nOriginal reason.\n\n## Approach\nRecorded proposal.\n\n## Choices and tradeoffs\nNative details over invented summaries.\n\n## Findings\nOfficial [source](https://example.org/primary).\n')
    first = commit(repo, 'PRSG-1 Explain legacy plan')
    before = audit.build_audit(repo)['tickets'][0]
    assert before['decision_context']['fields']['purpose']['text'] == ['Original reason.']
    md.write_text(md.read_text().replace('Original reason.', 'New committed reason.'))
    second = commit(repo, 'Update Markdown explanation only')
    md.write_text(md.read_text().replace('New committed reason.', 'Dirty explanation.'))
    row = audit.build_audit(repo)['tickets'][0]
    assert row['decision_context']['fields']['purpose']['text'] == ['New committed reason.']
    assert row['decision_context']['fields']['choices']['text'] == row['decision_context']['fields']['tradeoffs']['text']
    assert row['decision_context']['references'] == [{'label': 'source', 'url': 'https://example.org/primary'}]
    assert row['spec_url'].startswith('https://github.com/jwtanx/praesagus/blob/'+second+'/')
    assert row['history'][0]['commit']['sha'] == first
    assert row['history'][0]['decision_context']['fields']['purpose']['text'] == ['Original reason.']
    assert row['history'][-1]['decision_context'] == row['decision_context']


def test_missing_context_does_not_invent_objective_reason(repo):
    write_ticket(repo)
    commit(repo, 'Create plan')
    context = audit.build_audit(repo)['tickets'][0]['decision_context']
    assert all(value['text'] == [] for value in context['fields'].values())


@pytest.mark.parametrize('bad', [None, 'rationale', {'purpose': 1}, {'choices': ['valid', None]},
                                      {'references': 'url'}, {'references': [{'label': 'bad', 'url': None}]}])
def test_malformed_context_fails_visibly_and_clears_stale_current_context(repo, bad):
    path = write_ticket(repo)
    data = json.loads(path.read_text())
    data['decision_context'] = {'purpose': 'Old accepted wording'}
    path.write_text(json.dumps(data))
    commit(repo, 'Create context')
    data['decision_context'] = bad
    path.write_text(json.dumps(data))
    commit(repo, 'PRSG-1 Invalid context')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['status'] == 'inconsistent'
    assert 'decision_context' not in row
    assert row['history'][0]['decision_context']['fields']['purpose']['text'] == ['Old accepted wording']


def test_removal_clears_current_context(repo):
    path = write_ticket(repo)
    data = json.loads(path.read_text()); data['decision_context'] = {'purpose': 'Historical reason'}
    path.write_text(json.dumps(data)); commit(repo, 'Create plan')
    path.unlink(); commit(repo, 'Remove metadata')
    row = audit.build_audit(repo)['tickets'][0]
    assert row['status'] == 'removed' and 'decision_context' not in row


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'http://example.org', 'https://user:secret@example.org',
    'https://example.org/\nunsafe', 'https://example.org/%0Aunsafe', 'https://example.org/%7Funsafe',
    'https://example.org/back\\slash', 'https://[invalid'])
def test_decision_reference_safety(url):
    assert audit.safe_reference(url) is None


def test_prsg27_legacy_boundary_and_limits_are_preserved():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(audit.read_blob(root, 'HEAD', 'plans/2026-10-01/PRSG-27.harness.json'))
    context = audit.extract_context(manifest, audit.read_blob(root, 'HEAD', manifest['spec_path']), 'https://github.com/jwtanx/praesagus')
    purpose = '\n'.join(context['fields']['purpose']['text'])
    assert 'pure standard-library calculations' in purpose
    assert 'No return forecasts' in purpose
    assert 'caller' in '\n'.join(context['fields']['findings']['text'])



def test_explicit_fields_override_legacy_without_erasing_unspecified_fields(repo):
    path = write_ticket(repo)
    data = json.loads(path.read_text());data['decision_context'] = {'purpose': 'Explicit authored reason.',
        'references': [{'label': 'Unsafe', 'url': 'https://user:secret@example.org'}, {'label': 'Safe', 'url': 'https://example.org/source'}]}
    path.write_text(json.dumps(data))
    md = path.with_name('PRSG-1-fixture.md');md.write_text(md.read_text()+'\n## Why the ticket is created?\nLegacy reason.\n\n## Approach\nLegacy proposal.\n')
    commit(repo, 'PRSG-1 Record hybrid context')
    context = audit.build_audit(repo)['tickets'][0]['decision_context']
    assert context['fields']['purpose']['text'] == ['Explicit authored reason.']
    assert context['fields']['approach']['text'] == ['Legacy proposal.']
    assert context['references'] == [{'label': 'Safe', 'url': 'https://example.org/source'}]


@pytest.mark.parametrize('url', ['https://@example.org', 'https://example.org:bad'])
def test_empty_userinfo_or_invalid_port_reference_rejected(url):
    assert audit.safe_reference(url) is None
