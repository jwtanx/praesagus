"""Offline planning-contract regressions; no provider calls or command execution."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
module_spec = importlib.util.spec_from_file_location('ticket_validator', ROOT / 'scripts/planning/validate_ticket.py')
validator = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(validator)


def manifest():
    return json.loads((ROOT / 'plans/2026-10-01/PRSG-1.harness.json').read_text())


@pytest.mark.parametrize('path', sorted((ROOT / 'plans/2026-10-01').glob('*.harness.json')))
def test_checked_in_manifests(path):
    assert validator.validate(json.loads(path.read_text()), ROOT).startswith('PRSG-')


@pytest.mark.parametrize('path', ['../secret', '/tmp/secret', 'backend/*.py', 'backend/../secret', 'backend\\secret', 'backend-other/main.py', 'AGENTS.md'])
def test_reject_unsafe_or_out_of_scope_path(path):
    with pytest.raises(ValueError):
        validator.validate(manifest(), ROOT, [path])


@pytest.mark.parametrize('field,value', [('type', 'unknown'), ('modules', ['backend', 'backend']), ('modules', ['unknown']), ('owner_role', 'Researcher'), ('priority', 'urgent'), ('effort_person_days', {'low': 2, 'high': 1}), ('effort_person_days', {'low': 1, 'high': float('inf')})])
def test_reject_bad_tags(field, value):
    item = manifest()
    item['tags'][field] = value
    with pytest.raises(ValueError):
        validator.validate(item, ROOT)


def acceptance_fixture(tmp_path, status='done'):
    """Control lifecycle state without editing the live ticket's evidence/spec."""
    item = manifest()
    item['checks'] = [{'id': 'synthetic', 'kind': 'manual',
                       'description': 'Controlled acceptance evidence',
                       'status': 'passed', 'evidence': ['Synthetic passing check']}]
    item['acceptance'] = [{'id': 'PRSG-1-D1', 'description': 'Controlled acceptance',
                          'check_ids': ['synthetic'], 'status': status,
                          'evidence': ['Synthetic acceptance evidence']}]
    item['review'] = {'status': 'accepted', 'evidence': ['Synthetic reviewed fixture']}
    item['status'] = 'complete' if status == 'done' else 'review'
    spec = tmp_path / item['spec_path']
    spec.parent.mkdir(parents=True)
    mark = '[x]' if status == 'done' else '[ ]'
    spec.write_text(f"- {mark} PRSG-1-D1: Controlled acceptance\n")
    assert validator.validate(item, tmp_path) == 'PRSG-1'
    return item


def test_complete_needs_evidence_and_review(tmp_path):
    item = acceptance_fixture(tmp_path)
    item['status'] = 'complete'
    item['review'] = {'status': 'pending', 'evidence': []}
    with pytest.raises(ValueError, match='complete needs'):
        validator.validate(item, tmp_path)


@pytest.mark.parametrize('status', ['passed', 'failed'])
@pytest.mark.parametrize('has_empty_evidence', [False, True], ids=['absent', 'empty'])
def test_check_pass_needs_evidence(status, has_empty_evidence):
    item = manifest()
    # Standalone synthetic check cannot invalidate completed live acceptance refs.
    check = {**item['checks'][0], 'id': 'synthetic-evidence-check', 'status': status}
    item['checks'].append(check)
    if has_empty_evidence:
        check['evidence'] = []
    else:
        check.pop('evidence', None)
    with pytest.raises(ValueError, match='needs evidence'):
        validator.validate(item, ROOT)


@pytest.mark.parametrize('status', ['passed', 'failed'])
def test_terminal_check_with_evidence_is_valid(status):
    item = manifest()
    item['checks'].append({**item['checks'][0], 'id': 'synthetic-evidence-check',
                           'status': status, 'evidence': ['Frozen synthetic check result']})
    assert validator.validate(item, ROOT) == 'PRSG-1'


@pytest.mark.parametrize('spec_status', ['pending', 'done'])
def test_checklist_sync(tmp_path, spec_status):
    item = acceptance_fixture(tmp_path, spec_status)
    item['acceptance'][0]['status'] = 'done' if spec_status == 'pending' else 'pending'
    with pytest.raises(ValueError, match='checklist mismatch'):
        validator.validate(item, tmp_path)


def test_protected_overlap():
    item = manifest()
    item['allowed_paths'].append('skills/example.md')
    with pytest.raises(ValueError, match='overlaps'):
        validator.validate(item, ROOT)


def test_symlink_escape(tmp_path):
    item = manifest()
    spec = tmp_path / item['spec_path']
    spec.parent.mkdir(parents=True)
    spec.write_text((ROOT / item['spec_path']).read_text())
    (tmp_path / 'backend').symlink_to(ROOT.parent, target_is_directory=True)
    with pytest.raises(ValueError, match='escapes'):
        validator.validate(copy.deepcopy(item), tmp_path)


def test_prefix_boundary():
    assert validator.matches('backend/main.py', ['backend/'])
    assert not validator.matches('backend-other/main.py', ['backend/'])


def test_valid_supplied_path():
    assert validator.validate(manifest(), ROOT, ['backend/catalyst_services.py']) == 'PRSG-1'


@pytest.mark.parametrize('role', ['Lead', 'Engineer', 'Trader', 'Researcher', 'Consultant'])
def test_active_and_historical_owner_roles(role):
    item = manifest()
    item['owner'] = item['tags']['owner_role'] = role
    assert validator.validate(item, ROOT) == 'PRSG-1'
