"""Read-only configured-role selection and linked workflow contract regressions."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SELECTOR = ROOT / 'skills/spawn/scripts/resolve_role.py'
SPEC = importlib.util.spec_from_file_location('spawn_role_selector', SELECTOR)
selector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selector)


def config():
    return json.loads((ROOT / 'agent-operations/roles.json').read_text())


@pytest.mark.parametrize('alias', ['ai-engineer', 'ai_engineer', 'ai engineer', 'AI Engineer', ' Ai_Engineer '])
def test_ai_aliases_adopt_only_the_caller(alias):
    assert selector.resolve_request(alias, config()) == {
        'roles': ['AI Engineer'], 'destination_mode': 'current-chat', 'caller_is_coordinator': False}


@pytest.mark.parametrize('role', ['Lead', 'Trader', 'Engineer'])
def test_existing_single_roles_remain_distinct(role):
    result = selector.resolve_request(role.lower(), config())
    assert result['roles'] == [role]
    assert result['destination_mode'] == 'current-chat'
    assert not result['caller_is_coordinator']


def test_all_uses_entire_configured_set_in_order():
    value = config()
    result = selector.resolve_request('all', value)
    assert result['roles'] == [entry['role'] for entry in value['roles']]
    assert 'AI Engineer' in result['roles'] and 'Designer' not in result['roles']
    assert result['destination_mode'] == 'new-chat' and result['caller_is_coordinator']
    # Selection follows config, not a hardcoded three/four-role list or app inventory.
    extended = copy.deepcopy(value)
    extended['roles'].append({'role': 'Test Specialist', 'startup_prompt': 'test-startup.md', 'schedules': []})
    assert selector.resolve_request('all', extended)['roles'][-1] == 'Test Specialist'


def test_fresh_single_is_explicit_and_leaves_caller_coordinating():
    assert selector.resolve_request('ai-engineer', config(), fresh=True) == {
        'roles': ['AI Engineer'], 'destination_mode': 'new-chat', 'caller_is_coordinator': True}
    with pytest.raises(ValueError, match='explicit boolean'):
        selector.resolve_request('ai-engineer', config(), fresh='yes')


@pytest.mark.parametrize('role_request', ['', 'ai', 'researcher', 'Designer', 'Engineer and Trader', 'all but lead', 'AI/Engineer'])
def test_unknown_ambiguous_or_combined_requests_fail_closed(role_request):
    with pytest.raises(ValueError):
        selector.resolve_request(role_request, config())


def test_normalized_configuration_collisions_are_rejected():
    value = config()
    value['roles'].append({**value['roles'][-1], 'role': 'ai_engineer'})
    with pytest.raises(ValueError, match='ambiguous'):
        selector.resolve_request('all', value)


@pytest.mark.parametrize('prompt', ['/tmp/startup.md', '../startup.md', 'agent-operations/../startup.md', 'x\\startup.md'])
def test_selector_rejects_unsafe_configured_startup_paths(prompt):
    value = config()
    value['roles'][-1]['startup_prompt'] = prompt
    with pytest.raises(ValueError, match='safe repository-relative'):
        selector.resolve_request('all', value)


def test_cli_defaults_work_from_other_directory_without_state_mutation(tmp_path):
    before = (ROOT / 'agent-operations/roles.json').read_bytes()
    result = subprocess.run([sys.executable, str(SELECTOR), 'ai', 'engineer'], cwd=tmp_path,
                            capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)['roles'] == ['AI Engineer']
    assert (ROOT / 'agent-operations/roles.json').read_bytes() == before
    assert list(tmp_path.iterdir()) == []
    bad = subprocess.run([sys.executable, str(SELECTOR), 'ai'], cwd=tmp_path,
                         capture_output=True, text=True)
    assert bad.returncode == 2 and not bad.stdout


def test_discovery_and_changed_guidance_resolve_real_config_and_references():
    canonical = ROOT / 'skills/spawn'
    assert (ROOT / '.agents/skills/spawn').resolve() == canonical
    for role in config()['roles']:
        assert (ROOT / role['startup_prompt']).is_file()
    for relative in ['AGENTS.md', 'agent-operations/README.md', 'skills/spawn/SKILL.md',
                     'skills/spawn/references/transfer.md', 'skills/praesagus-project-lead/SKILL.md',
                     'skills/praesagus-implementation/SKILL.md']:
        path = ROOT / relative
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
            if '://' not in target:
                resource = (path.parent / target.split('#', 1)[0]).resolve()
                assert resource.is_relative_to(ROOT) and resource.is_file(), (relative, target)
