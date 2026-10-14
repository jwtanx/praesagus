"""Offline AI role discovery and ticket-contract regressions; no app/provider calls."""
import copy
import importlib.util
import json
from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ai_role_ticket_validator', ROOT / 'scripts/planning/validate_ticket.py')
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def ticket():
    return json.loads((ROOT / 'plans/2026-10-01/PRSG-1.harness.json').read_text())


def test_role_discovery_preserves_existing_configuration():
    config = json.loads((ROOT / 'agent-operations/roles.json').read_text())
    roles = config['roles']
    assert config['schema_version'] == 1
    assert config['timezone'] == 'Asia/Kuala_Lumpur'
    assert len({item['role'] for item in roles}) == len(roles) == 4
    by_role = {item['role']: item for item in roles}
    expected = {
        'Lead': (None, None, ['lead-daily-planning', 'lead-coordination', 'resource-recovery']),
        'Trader': ('gpt-6.1-sol', 'medium', ['trader-daily-report']),
        'Engineer': (None, None, []),
        'AI Engineer': (None, None, []),
    }
    assert by_role.keys() == expected.keys()
    for role, (model, effort, schedules) in expected.items():
        entry = by_role[role]
        assert (entry['model'], entry['reasoning_effort'], entry['schedules']) == (model, effort, schedules)
        prompt = ROOT / entry['startup_prompt']
        assert prompt.is_file() and prompt.resolve().is_relative_to(ROOT)
    assert by_role['AI Engineer']['startup_prompt'] == 'agent-operations/startup-prompts/ai-engineer.md'


@pytest.mark.parametrize('role', ['AI Engineer', 'Lead', 'Engineer', 'Trader', 'Researcher', 'Consultant'])
def test_new_and_historical_ticket_owners_remain_valid(role):
    item = ticket()
    item['owner'] = item['tags']['owner_role'] = role
    assert validator.validate(item, ROOT) == 'PRSG-1'


def test_unknown_ai_role_and_mismatched_owner_rejected():
    item = ticket()
    item['owner'] = item['tags']['owner_role'] = 'AI Researcher'
    with pytest.raises(ValueError, match='unknown tag: owner_role'):
        validator.validate(item, ROOT)
    item['tags']['owner_role'] = 'AI Engineer'
    with pytest.raises(ValueError, match='owner and owner_role must match'):
        validator.validate(item, ROOT)


def test_ai_owner_does_not_bypass_lead_completion_gate():
    item = copy.deepcopy(ticket())
    item['owner'] = item['tags']['owner_role'] = 'AI Engineer'
    item['status'] = 'complete'
    item['review'] = {'status': 'pending'}
    with pytest.raises(ValueError, match='complete needs'):
        validator.validate(item, ROOT)


def test_skill_discovery_resolves_canonical_resources():
    skill = ROOT / 'skills/ai-engineer'
    discovery = ROOT / '.agents/skills/ai-engineer'
    assert discovery.is_symlink()
    assert discovery.resolve() == skill.resolve()
    text = (discovery / 'SKILL.md').read_text()
    frontmatter = yaml.safe_load(text.split('---', 2)[1])
    assert frontmatter['name'] == 'ai-engineer'
    assert isinstance(frontmatter['description'], str) and frontmatter['description'].strip()
    interface = yaml.safe_load((skill / 'agents/openai.yaml').read_text())
    assert interface['interface']['display_name'] == 'AI Engineer'
    assert '$ai-engineer' in interface['interface']['default_prompt']
    assert interface.get('policy', {}).get('allow_implicit_invocation', True)
    # Resolve links from the canonical file, as discovery may enter via a symlink.
    for path in [skill / 'SKILL.md', skill / 'references/model-evidence.md']:
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
            resource = (path.parent / target.split('#', 1)[0]).resolve()
            assert resource.is_relative_to(ROOT) and resource.is_file(), target
