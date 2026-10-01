"""Build a reproducible, committed-only ticket audit from full first-parent Git history."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote, unquote, urlsplit

PLAN = re.compile(r'^plans/\d{4}-\d{2}-\d{2}/(PRSG-[1-9][0-9]*)\.harness\.json$')
KEY = re.compile(r'^(PRSG-(?:0|[1-9][0-9]*)) ')
STATES = {'planned', 'in_progress', 'review', 'complete', 'blocked'}
_spec = importlib.util.spec_from_file_location('audit_ticket_validator', Path(__file__).with_name('validate_ticket.py'))
_validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validator)


def git(root, *args, optional=False):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    if result.returncode:
        if optional:
            return None
        raise ValueError('Git audit read failed: ' + result.stderr.decode(errors='replace').strip())
    return result.stdout.decode('utf-8')


CONTEXT_FIELDS = ('purpose', 'approach', 'choices', 'findings', 'tradeoffs')
SECTION_NAMES = {
    'purpose': {'why the ticket is created?', 'objective', 'objective and boundary', 'objective and interfaces', 'problem', 'user need'},
    'approach': {'approach', 'decision', 'scope and decision', 'accepted scope', 'implementation plan'},
    'choices': {'choices', 'options', 'choices and tradeoffs'},
    'findings': {'findings', 'research findings', 'decision and research review', 'evidence and limits', 'evidence and limitations', 'limitations', 'engineer handoff evidence'},
    'tradeoffs': {'tradeoffs', 'choices and tradeoffs', 'scope and non-goals', 'safety and scope', 'frozen scope and handoff'},
}


def safe_reference(value):
    if not isinstance(value, str) or re.search(r'[\s\\\x00-\x1f\x7f]', unquote(value)):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme == 'https' and parsed.hostname and parsed.username is None and parsed.password is None:
            parsed.port  # Reject malformed ports without restricting valid HTTPS ports.
            return value
    except ValueError:
        pass
    return None


def context_values(value):
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError('Decision context requires text or a list of nonblank text')
    return values


def extract_context(manifest, spec_text, spec_url):
    """Preserve named source sections verbatim; never infer unrecorded decisions."""
    sections = []
    heading, body = None, []
    fenced = False
    for line in spec_text.splitlines():
        if re.match(r'^\s*(```|~~~)', line):
            fenced = not fenced
        match = re.match(r'^#{2,6}\s+(.+?)\s*#*$', line) if not fenced else None
        if match:
            if heading is not None:
                sections.append((heading, '\n'.join(body).strip()))
            heading, body = match[1].strip().lower(), []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        sections.append((heading, '\n'.join(body).strip()))
    explicit = manifest.get('decision_context', {})
    if not isinstance(explicit, dict):
        raise ValueError('decision_context must be an object')
    result = {'fields': {}, 'references': [], 'spec_url': spec_url,
              'review_status': manifest['review'].get('status'),
              'scope_status': manifest.get('scope_status')}
    for field in CONTEXT_FIELDS:
        if field in explicit:
            values, source = context_values(explicit[field]), 'manifest'
        else:
            values = [content for name, content in sections if name in SECTION_NAMES[field] and content]
            source = 'named specification sections'
        result['fields'][field] = {'text': values, 'source': source if values else None}
    refs = explicit.get('references', [])
    if not isinstance(refs, list) or any(not isinstance(ref, dict) or not isinstance(ref.get('label'), str) or not ref['label'].strip() or not isinstance(ref.get('url'), str) for ref in refs):
        raise ValueError('decision references require label and URL')
    candidates = list(refs)
    for field in result['fields'].values():
        for value in field['text']:
            candidates.extend({'label': label, 'url': url} for label, url in re.findall(r'\[([^\]\n]+)\]\((https://[^\s<>]+?)\)', value))
            candidates.extend({'label': 'Recorded source', 'url': url.rstrip('.,;')} for url in re.findall(r'https://[^\s<>\)]+', value))
    seen = set()
    for ref in candidates:
        url = safe_reference(ref['url'])
        if url and url not in seen:
            seen.add(url)
            result['references'].append({'label': ref['label'], 'url': url})
    return result


def progress(manifest):
    items = manifest.get('acceptance', [])
    return {'done': sum(item.get('status') == 'done' for item in items), 'total': len(items)}


def validate_snapshot(data, key):
    if not isinstance(data, dict) or data.get('schema_version') != 1 or data.get('ticket_key') != key:
        raise ValueError('Invalid ticket manifest: ' + key)
    if data.get('status') not in STATES or not isinstance(data.get('objective'), str):
        raise ValueError('Invalid ticket status/objective: ' + key)
    for field in ('tags', 'review'):
        if not isinstance(data.get(field), dict):
            raise ValueError('Invalid ticket ' + field + ': ' + key)
    for field in ('acceptance', 'checks'):
        if not isinstance(data.get(field), list) or not all(isinstance(row, dict) for row in data[field]):
            raise ValueError('Invalid ticket ' + field + ': ' + key)
        ids = [row.get('id') for row in data[field]]
        if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
            raise ValueError('Invalid/duplicate '+field+' IDs: '+key)
    spec = data.get('spec_path')
    if not isinstance(spec, str) or not re.fullmatch(r'plans/\d{4}-\d{2}-\d{2}/'+re.escape(key)+r'-[a-z0-9-]+\.md', spec):
        raise ValueError('Invalid ticket specification path: ' + key)
    if data['status'] == 'complete':
        checks = {row.get('id'): row for row in data['checks']}
        if not data['acceptance'] or data['review'].get('status') != 'accepted' or not evidence(data['review'].get('evidence')):
            raise ValueError('Completion requires reviewed evidence: ' + key)
        for item in data['acceptance']:
            refs = item.get('check_ids')
            if item.get('status') != 'done' or not evidence(item.get('evidence')) or not isinstance(refs, list) or not refs:
                raise ValueError('Completion requires all acceptance evidence: ' + key)
            if any(not isinstance(ref, str) or ref not in checks or checks[ref].get('status') != 'passed' or not evidence(checks[ref].get('evidence')) for ref in refs):
                raise ValueError('Completion requires passed checks: ' + key)
    return data


def evidence(value):
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def validate_committed_contract(root, manifest, spec_text, sha):
    # Replay the existing authoritative gates against that commit's own Markdown,
    # not today's working tree. These temporary files are validation fixtures only.
    with tempfile.TemporaryDirectory(prefix='praesagus-audit-') as temporary:
        folder = Path(temporary)
        path = folder / manifest['spec_path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(spec_text, encoding='utf-8')
        _validator.validate(manifest, folder)
    if manifest.get('base_sha') is not None:
        git(root, 'cat-file', '-e', manifest['base_sha']+'^{commit}')
        git(root, 'merge-base', '--is-ancestor', manifest['base_sha'], sha)


def read_blob(root, sha, path):
    # Distinguish an absent path from a corrupt/unreadable Git object.
    if not git(root, 'ls-tree', '--full-tree', sha, '--', path).strip():
        return None
    return git(root, 'show', sha+':'+path)


def invalid_checkpoint(records, key, commit, paths, error, manifest_path=None):
    """Retain failed metadata as visible history; never promote it to completion."""
    if key not in records:
        records[key] = {'ticket_key': key, 'title': 'Unvalidated ticket metadata',
            'description': 'Review the linked commit to resolve the ticket contract.',
            'tags': {}, 'created_on': commit['committed_at'][:10], 'spec_url': None,
            'history': []}
    row = records[key]
    row.update(status='inconsistent', updated_at=commit['committed_at'], completion_commit=None,
               progress={'done': 0, 'total': 0}, checks=[], acceptance=[], review={}, validation_error=error)
    row.pop('decision_context', None)
    if manifest_path:
        row['manifest_path'] = manifest_path
    row['history'].append({'commit': commit, 'kind': 'validation_failed', 'paths': paths,
        'status': 'inconsistent', 'validation_error': error, 'progress': {'done': 0, 'total': 0},
        'checks': [], 'acceptance': [], 'review': {}})


def repository_url(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or parsed.hostname != 'github.com' or parsed.username or parsed.password or parsed.query or parsed.fragment or not re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?', parsed.path):
        raise ValueError('repository-url must be an HTTPS github.com owner/repository URL')
    return value.rstrip('/')


def build_audit(root, url='https://github.com/jwtanx/praesagus', ref='HEAD'):
    root = Path(root)
    url = repository_url(url)
    if git(root, 'rev-parse', '--is-shallow-repository').strip() != 'false':
        raise ValueError('Full Git history required; fetch with fetch-depth: 0')
    head = git(root, 'rev-parse', '--verify', '--end-of-options', ref+'^{commit}').strip()
    if not re.fullmatch(r'[0-9a-f]{40}', head):
        raise ValueError('Invalid resolved Git commit')
    records = {}
    for sha in git(root, 'rev-list', '--first-parent', '--reverse', head).splitlines():
        subject, committed_at, parents = git(root, 'show', '-s', '--format=%s%n%cI%n%P', sha).split('\n', 2)
        parents = parents.strip().split()
        args = ('diff', '--name-only', '-z', '--no-renames', parents[0], sha) if parents else (
            'diff-tree', '--root', '-r', '--no-commit-id', '--name-only', '-z', '--no-renames', sha)
        paths = [path for path in git(root, *args).split('\0') if path]
        manifests = [path for path in paths if PLAN.fullmatch(path)]
        prefix = KEY.match(subject)
        if not manifests and not prefix and not any(path.endswith('.md') and path.startswith('plans/') for path in paths):
            continue
        commit = {'sha': sha, 'subject': subject, 'committed_at': committed_at, 'url': url+'/commit/'+sha}
        touched = set()
        for path in manifests:
            key = PLAN.fullmatch(path)[1]
            raw = read_blob(root, sha, path)
            previous = records.get(key)
            if raw is None:
                if previous:
                    previous.pop('decision_context', None)
                    previous['status'] = 'removed'
                    previous['completion_commit'] = None
                    previous['updated_at'] = committed_at
                    previous['history'].append({'commit': commit, 'kind': 'plan_removed', 'paths': paths,
                        'status': 'removed', 'progress': previous['progress'], 'checks': [], 'acceptance': [], 'review': {}})
                    touched.add(key)
                continue
            try:
                manifest = validate_snapshot(json.loads(raw), key)
            except (ValueError, TypeError, KeyError) as exc:
                invalid_checkpoint(records, key, commit, paths, str(exc), path)
                touched.add(key)
                continue
            if previous and previous.get('manifest_path') and previous['manifest_path'] != path and previous['status'] != 'removed':
                raise ValueError('Duplicate live ticket key: '+key)
            spec_text = read_blob(root, sha, manifest['spec_path'])
            try:
                if spec_text is None:
                    raise ValueError('Specification missing at checkpoint: '+manifest['spec_path'])
                validate_committed_contract(root, manifest, spec_text, sha)
                context = extract_context(manifest, spec_text, url+'/blob/'+sha+'/'+quote(manifest['spec_path'], safe='/'))
            except (ValueError, TypeError, KeyError) as exc:
                invalid_checkpoint(records, key, commit, paths, str(exc), path)
                touched.add(key)
                continue
            heading = re.search(r'^#\s+(.+)$', spec_text, re.M)
            title = re.sub(r'^'+re.escape(key)+r'\s*[—–-]\s*', '', heading[1]) if heading else manifest['objective']
            history = previous['history'] if previous else []
            complete = manifest['status'] == 'complete'
            kind = 'completed' if complete and (not previous or previous['status'] != 'complete') else ('progress_updated' if previous else 'plan_created')
            snapshot = {'commit': commit, 'kind': kind, 'paths': paths, 'status': manifest['status'],
                'progress': progress(manifest), 'checks': manifest['checks'], 'acceptance': manifest['acceptance'],
                'review': manifest['review'], 'manifest': manifest, 'decision_context': context,
                'spec_url': url+'/blob/'+sha+'/'+quote(manifest['spec_path'], safe='/')}
            history.append(copy.deepcopy(snapshot))
            records[key] = {'ticket_key': key, 'title': title, 'description': manifest['objective'],
                'status': manifest['status'], 'tags': manifest['tags'], 'created_on': manifest.get('created_on', ''),
                'updated_at': committed_at, 'spec_url': url+'/blob/'+sha+'/'+quote(manifest['spec_path'], safe='/'),
                'manifest_path': path, 'progress': progress(manifest), 'checks': manifest['checks'],
                'acceptance': manifest['acceptance'], 'review': manifest['review'], 'history': history, 'decision_context': context,
                'completion_commit': commit if kind == 'completed' else (previous.get('completion_commit') if previous and complete else None)}
            touched.add(key)
        # Committed Markdown progress is auditable even without a JSON state change.
        for key, ticket in list(records.items()):
            if key in touched:
                continue
            spec_path = next((event['manifest']['spec_path'] for event in reversed(ticket['history']) if 'manifest' in event), None)
            if spec_path in paths:
                text = read_blob(root, sha, spec_path)
                last_manifest = next((event['manifest'] for event in reversed(ticket['history']) if 'manifest' in event), None)
                if text is None and ticket['status'] != 'removed':
                    invalid_checkpoint(records, key, commit, paths, 'Specification removed without matching metadata update')
                    touched.add(key)
                    continue
                if text is not None:
                    if ticket['status'] != 'removed' and last_manifest:
                        try:
                            current_raw = read_blob(root, sha, ticket['manifest_path'])
                            if current_raw is None:
                                raise ValueError('Current manifest missing')
                            last_manifest = validate_snapshot(json.loads(current_raw), key)
                            validate_committed_contract(root, last_manifest, text, sha)
                            ticket['decision_context'] = extract_context(last_manifest, text, url+'/blob/'+sha+'/'+quote(spec_path, safe='/'))
                        except (ValueError, TypeError, KeyError) as exc:
                            invalid_checkpoint(records, key, commit, paths, str(exc))
                            touched.add(key)
                            continue
                    heading = re.search(r'^#\s+(.+)$', text, re.M)
                    if heading:
                        ticket['title'] = re.sub(r'^'+re.escape(key)+r'\s*[—–-]\s*', '', heading[1])
                    ticket['spec_url'] = url+'/blob/'+sha+'/'+quote(spec_path, safe='/')
                    recovered = ticket['status'] == 'inconsistent' and last_manifest is not None
                    if recovered:
                        ticket.update(status=last_manifest['status'], progress=progress(last_manifest),
                            checks=last_manifest['checks'], acceptance=last_manifest['acceptance'], review=last_manifest['review'])
                        ticket.pop('validation_error', None)
                        if ticket['status'] == 'complete':
                            ticket['completion_commit'] = commit
                ticket['updated_at'] = committed_at
                kind = ('completed' if recovered and ticket['status'] == 'complete' else 'progress_recovered' if recovered else 'spec_updated') if text is not None else 'spec_removed'
                ticket['history'].append({'commit': commit, 'kind': kind, 'paths': paths,
                    'status': ticket['status'], 'progress': ticket['progress'], 'checks': ticket['checks'],
                    'acceptance': ticket['acceptance'], 'review': ticket['review'], 'spec_url': ticket['spec_url'],
                    'decision_context': ticket.get('decision_context')})
                touched.add(key)
        if prefix and prefix[1] not in touched:
            key = prefix[1]
            if key not in records:
                records[key] = {'ticket_key': key, 'title': 'Shared workflow activity' if key == 'PRSG-0' else subject[len(key)+1:],
                    'description': 'Commit activity only; no accepted ticket manifest has been recorded.',
                    'status': 'activity_only', 'tags': {}, 'created_on': committed_at[:10],
                    'updated_at': committed_at, 'spec_url': None, 'progress': {'done': 0, 'total': 0},
                    'checks': [], 'acceptance': [], 'review': {}, 'history': [], 'completion_commit': None}
            ticket = records[key]
            ticket['updated_at'] = committed_at
            ticket['history'].append({'commit': commit, 'kind': 'delivery_commit', 'paths': paths,
                'status': ticket['status'], 'progress': ticket['progress'], 'checks': [], 'acceptance': [], 'review': {}})
    return {'schema_version': 1, 'repository_url': url, 'head_sha': head,
        'generated_from': 'committed first-parent manifest checkpoints and recognized PRSG commit activity',
        'limitations': ['Uncommitted work is excluded. Side-branch intermediate checkpoints (including merged branches) are not replayed; the first-parent merge snapshot is recorded.',
            'Legacy Markdown-only plans without manifests and non-prefixed code commits without recognized metadata changes cannot be assigned automatically.',
            'Event paths are entire commit context, not proof of ticket-owned scope. Recorded evidence is not independent proof of tests or deployment.',
            'Invalid metadata/checklist checkpoints are retained as inconsistent with commit links; later valid corrections restore state without hiding the failure. Git read errors/shallow history fail the build.',
            'Source history is not a tamper-proof compliance archive.'],
        'tickets': sorted(records.values(), key=lambda row: int(row['ticket_key'].split('-')[1]))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--repository-url', default='https://github.com/jwtanx/praesagus')
    parser.add_argument('--ref', default='HEAD')
    parser.add_argument('--output', type=Path, default=Path('artifacts/tickets/audit.json'))
    args = parser.parse_args()
    audit = build_audit(args.repo_root, args.repository_url, args.ref)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f"Ticket audit: {len(audit['tickets'])} tickets at {audit['head_sha']} -> {args.output}")


if __name__ == '__main__':
    main()
