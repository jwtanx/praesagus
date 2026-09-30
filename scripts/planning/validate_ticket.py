"""Validate a ticket manifest and explicitly supplied changed paths (no writes)."""
import argparse
from datetime import date
import json
import math
from pathlib import Path
import re


def relative_path(value, prefix=False):
    if not isinstance(value, str) or not value or value.startswith('/') or '\\' in value:
        raise ValueError('paths must be nonempty repository-relative POSIX paths')
    trimmed = value[:-1] if prefix and value.endswith('/') else value
    if any(part in {'', '.', '..'} for part in trimmed.split('/')) or any(c in value for c in '*?[]:'):
        raise ValueError('unsafe path or glob: ' + value)
    return value


def matches(path, rules):
    return any(path == rule or (rule.endswith('/') and path.startswith(rule)) for rule in rules)


def evidence(value):
    return isinstance(value, list) and bool(value) and all(isinstance(s, str) and s.strip() for s in value)


def validate(manifest, root, changed=()):
    if not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1:
        raise ValueError('schema_version must be 1')
    required = {'ticket_key', 'tags', 'created_on', 'timezone', 'spec_path', 'objective', 'status', 'owner',
                'reviewer', 'scope_status', 'base_sha', 'allowed_paths', 'protected_paths', 'checks', 'acceptance', 'review'}
    if not required <= manifest.keys():
        raise ValueError('missing manifest fields: ' + ', '.join(sorted(required - manifest.keys())))
    key = manifest['ticket_key']
    if not isinstance(key, str) or not re.fullmatch(r'PRSG-[1-9][0-9]*', key):
        raise ValueError('invalid ticket key')
    day = manifest['created_on']
    if not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise ValueError('created_on must be YYYY-MM-DD')
    date.fromisoformat(day)
    if manifest['timezone'] != 'Asia/Kuala_Lumpur':
        raise ValueError('planning timezone must be Asia/Kuala_Lumpur')
    for field in ('objective', 'owner', 'reviewer'):
        if not isinstance(manifest[field], str) or not manifest[field].strip():
            raise ValueError(field + ' is required')
    tags = manifest['tags']
    vocab = {'type': {'feature', 'bug', 'spike', 'refactor', 'chore', 'docs', 'test', 'skill'},
             'owner_role': {'Lead', 'Engineer', 'Researcher', 'Consultant'},
             'priority': {'P0', 'P1', 'P2', 'P3'},
             'effort_size': {'XS', 'S', 'M', 'L', 'XL'},
             'impact': {'low', 'medium', 'medium-high', 'high'}}
    if not isinstance(tags, dict):
        raise ValueError('tags must be an object')
    for field, values in vocab.items():
        if not isinstance(tags.get(field), str) or tags[field] not in values:
            raise ValueError('unknown tag: ' + field)
    modules = tags.get('modules')
    known_modules = {'backend', 'frontend', 'connectors', 'financial-data', 'market-research',
                     'alerting', 'observability', 'harness', 'skills', 'infra', 'docs'}
    if not isinstance(modules, list) or not modules or not all(isinstance(m, str) and m in known_modules for m in modules) or len(set(modules)) != len(modules):
        raise ValueError('modules need unique known values')
    if tags['owner_role'] != manifest['owner']:
        raise ValueError('owner and owner_role must match')
    effort = tags.get('effort_person_days')
    if not isinstance(effort, dict) or any(type(effort.get(k)) not in (int, float) or not math.isfinite(effort[k]) or effort[k] <= 0 for k in ('low', 'high')) or effort['low'] > effort['high']:
        raise ValueError('effort needs finite positive low/high range')
    root = Path(root).resolve()
    spec = relative_path(manifest['spec_path'])
    if not spec.startswith('plans/' + day + '/' + key + '-') or not spec.endswith('.md'):
        raise ValueError('spec path must match creation date and ticket key')
    if not (root / spec).resolve().is_relative_to(root) or not (root / spec).is_file():
        raise ValueError('spec missing or escapes repository')
    if manifest['status'] not in {'planned', 'in_progress', 'review', 'complete', 'blocked'}:
        raise ValueError('unknown ticket status')
    if manifest['scope_status'] not in {'provisional', 'accepted'}:
        raise ValueError('unknown scope status')
    base = manifest['base_sha']
    if base is not None and (not isinstance(base, str) or not re.fullmatch(r'[0-9a-f]{40}', base)):
        raise ValueError('base_sha must be resolved SHA or null')
    if manifest['status'] in {'in_progress', 'review', 'complete'} and (manifest['scope_status'] != 'accepted' or base is None):
        raise ValueError('active tickets need accepted scope and frozen base_sha')
    for field in ('allowed_paths', 'protected_paths'):
        if not isinstance(manifest[field], list) or not manifest[field]:
            raise ValueError(field + ' must be nonempty list')
        for rule in manifest[field]:
            relative_path(rule, prefix=True)
            if not (root / rule).resolve().is_relative_to(root):
                raise ValueError('scope path escapes repository: ' + rule)
    for allowed in manifest['allowed_paths']:
        for protected in manifest['protected_paths']:
            if matches(allowed, [protected]) or matches(protected, [allowed]):
                raise ValueError('allowed/protected scope overlaps: ' + allowed)
    checks = manifest['checks']
    if not isinstance(checks, list) or not checks:
        raise ValueError('checks must be nonempty')
    check_map = {}
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get('id'), str) or not check['id'].strip() or check['id'] in check_map:
            raise ValueError('checks need unique nonempty IDs')
        if check.get('kind') not in {'command', 'manual'} or check.get('status') not in {'pending', 'passed', 'failed'}:
            raise ValueError('unknown check kind/status')
        if check['kind'] == 'command':
            argv = check.get('argv')
            if not isinstance(argv, list) or not argv or not all(isinstance(s, str) and s for s in argv):
                raise ValueError('commands need argv arrays')
            cwd = check.get('cwd')
            if cwd != '.':
                relative_path(cwd)
            if not (root / cwd).resolve().is_relative_to(root):
                raise ValueError('command cwd escapes repository')
        if check['status'] != 'pending' and not evidence(check.get('evidence')):
            raise ValueError('run check needs evidence')
        check_map[check['id']] = check
    acceptance = manifest['acceptance']
    if not isinstance(acceptance, list) or not acceptance:
        raise ValueError('acceptance must be nonempty')
    ids = set()
    spec_text = (root / spec).read_text(encoding='utf-8')
    for item in acceptance:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not re.fullmatch(re.escape(key) + r'-D[1-9][0-9]*', item['id']) or item['id'] in ids:
            raise ValueError('acceptance IDs must be unique ticket checklist IDs')
        ids.add(item['id'])
        if not isinstance(item.get('description'), str) or not item['description'].strip():
            raise ValueError('acceptance needs description')
        refs = item.get('check_ids')
        if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref in check_map for ref in refs):
            raise ValueError('acceptance references missing checks')
        if item.get('status') not in {'pending', 'done'}:
            raise ValueError('unknown acceptance status')
        mark = '[x]' if item['status'] == 'done' else '[ ]'
        if '- ' + mark + ' ' + item['id'] + ':' not in spec_text:
            raise ValueError('Markdown/JSON checklist mismatch: ' + item['id'])
        if item['status'] == 'done' and (not evidence(item.get('evidence')) or any(check_map[r]['status'] != 'passed' for r in refs)):
            raise ValueError('done acceptance needs passed checks and evidence')
    review = manifest['review']
    if not isinstance(review, dict) or review.get('status') not in {'pending', 'accepted'}:
        raise ValueError('unknown review status')
    if review['status'] == 'accepted' and not evidence(review.get('evidence')):
        raise ValueError('accepted review needs evidence')
    if manifest['status'] == 'complete' and (review['status'] != 'accepted' or any(a['status'] != 'done' for a in acceptance)):
        raise ValueError('complete needs all acceptance done and Lead review')
    for value in changed:
        path = relative_path(value)
        if not (root / path).resolve().is_relative_to(root):
            raise ValueError('changed path escapes repository')
        if matches(path, manifest['protected_paths']) or not matches(path, manifest['allowed_paths']):
            raise ValueError('changed path outside ticket scope: ' + path)
    return key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--changed-file', action='append', default=[])
    args = parser.parse_args()
    try:
        key = validate(json.loads(args.manifest.read_text()), args.repo_root, args.changed_file)
        print(key + ': manifest and supplied paths valid (evidence still requires review)')
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print('ERROR: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
