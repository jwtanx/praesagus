"""Offline ticket verification. Explicit policy approval is required to run commands."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile

from validate_ticket import validate, matches


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def fingerprint(root, path):
    index = hashlib.sha256(git(root, 'ls-files', '--stage', '-z', '--', path)).hexdigest()
    target = root / path
    if target.is_symlink():
        return 'symlink:' + os.readlink(target) + ':' + index
    if not target.exists():
        return 'deleted:' + index
    if not target.is_file():
        raise ValueError('unsupported changed object: ' + path)
    return hashlib.sha256(target.read_bytes()).hexdigest() + ':' + str(target.stat().st_mode & 0o777) + ':' + index


def snapshot(root, base):
    git(root, 'merge-base', '--is-ancestor', base, 'HEAD')
    paths = set()
    for args in [('diff', '--no-renames', '--name-only', '-z', base),
                 ('diff', '--cached', '--no-renames', '--name-only', '-z', base),
                 ('ls-files', '--others', '--exclude-standard', '-z')]:
        paths.update(p.decode('utf-8') for p in git(root, *args).split(b'\0') if p)
    return {p: fingerprint(root, p) for p in sorted(paths)}


def baseline(root, base):
    return {'schema_version': 1, 'base_sha': base,
            'head_sha': git(root, 'rev-parse', 'HEAD').decode().strip(),
            'paths': snapshot(root, base)}


def run_command(root, check, approved):
    contract = {'argv': check['argv'], 'cwd': check['cwd']}
    if contract not in approved:
        return {'id': check['id'], 'status': 'unapproved'}
    # Do not persist stdout/stderr: tests can print sensitive values.
    timeout = 120
    with tempfile.TemporaryFile() as out:
        proc = subprocess.Popen(check['argv'], cwd=root / check['cwd'],
                                stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
            status = 'passed' if code == 0 else 'failed'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            code, status = None, 'timeout'
        out.seek(0)
        digest = hashlib.sha256()
        size = 0
        for block in iter(lambda: out.read(65536), b''):
            digest.update(block)
            size += len(block)
    return {'id': check['id'], 'status': status, 'exit_code': code,
            'timeout_seconds': timeout, 'output_bytes': size, 'output_sha256': digest.hexdigest()}


def verify(root, manifest, approved, prior=None):
    validate(manifest, root)
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    if manifest['scope_status'] != 'accepted' or not manifest['base_sha']:
        raise ValueError('verification requires accepted frozen scope')
    before = snapshot(root, manifest['base_sha'])
    excluded = {}
    if prior is not None:
        if prior.get('schema_version') != 1 or prior.get('base_sha') != manifest['base_sha']:
            raise ValueError('baseline does not match frozen base')
        for path, value in prior['paths'].items():
            if matches(path, manifest['allowed_paths']):
                raise ValueError('baseline cannot exclude ticket-owned path: ' + path)
            if before.get(path) != value:
                raise ValueError('pre-existing change moved or disappeared: ' + path)
            excluded[path] = value
    changed = sorted(set(before) - set(excluded))
    validate(manifest, root, changed)
    # Reject before executing ANY check if its command is not approved.
    for check in manifest['checks']:
        if check['kind'] == 'command' and {'argv': check['argv'], 'cwd': check['cwd']} not in approved:
            raise ValueError('unapproved command: ' + check['id'])
    results = []
    for check in manifest['checks']:
        if check['kind'] == 'manual':
            results.append({'id': check['id'], 'status': 'manual_review_required'})
        else:
            results.append(run_command(root, check, approved))
    after = snapshot(root, manifest['base_sha'])
    head_after = git(root, 'rev-parse', 'HEAD').decode().strip()
    passed = before == after and head == head_after and all(r['status'] == 'passed' for r in results)
    return {'schema_version': 1, 'ticket_key': manifest['ticket_key'],
            'verified_at': datetime.now(timezone.utc).isoformat(),
            'head_sha': head, 'head_unchanged': head == head_after,
            'base_sha': manifest['base_sha'], 'manifest_sha256': hashlib.sha256(
                json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            'changed_paths': changed, 'excluded_baseline_paths': sorted(excluded),
            'worktree_fingerprints': before, 'checks': results,
            'worktree_unchanged': before == after,
            'status': 'passed' if passed else 'needs_attention',
            'limitations': 'Not a filesystem sandbox. Approved commands execute repository code. '
                            'Ignored files are not inventoried. Manual evidence is never auto-accepted.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ticket')
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--capture-baseline', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    try:
        found = list((root / 'plans').glob('*/' + args.ticket + '.harness.json'))
        if len(found) != 1:
            raise ValueError('ticket must resolve to exactly one manifest')
        manifest = json.loads(found[0].read_text())
        validate(manifest, root)
        output = args.output.resolve()
        if output.is_relative_to(root) or output.exists():
            raise ValueError('output must be a new file outside repository')
        if args.capture_baseline:
            result = baseline(root, manifest['base_sha'])
            # Ticket metadata must exist to resolve the ticket, but stays in the
            # verified change set rather than being treated as unrelated work.
            result['paths'].pop(manifest['spec_path'], None)
            result['paths'].pop(str(found[0].relative_to(root)), None)
            # Capture before ticket edits. Never ignore ticket-owned paths.
            if any(matches(p, manifest['allowed_paths']) for p in result['paths']):
                raise ValueError('capture baseline before ticket-owned edits')
            code = 0
        else:
            policy = json.loads((root / 'harness/verification_policy.json').read_text())
            result = verify(root, manifest, policy['commands'],
                            json.loads(args.baseline.read_text()) if args.baseline else None)
            code = 0 if result['status'] == 'passed' else 1
        with output.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
        print(str(output))
        return code
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        print('ERROR: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
