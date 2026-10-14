#!/usr/bin/env python3
"""Read-only role selection; does not create chats, transfer ownership or authorize work."""
import argparse
import json
from pathlib import Path, PurePosixPath


def normalize(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('role must be a nonempty name')
    return ' '.join(value.casefold().replace('-', ' ').replace('_', ' ').split())


def resolve_request(request, config, *, fresh=False):
    """Resolve exact normalized names from configuration, never app chat titles."""
    if not isinstance(config, dict) or type(config.get('schema_version')) is not int or config['schema_version'] != 1:
        raise ValueError('role configuration schema_version must be 1')
    if type(fresh) is not bool:
        raise ValueError('fresh mode must be explicit boolean')
    entries = config.get('roles')
    if not isinstance(entries, list) or not entries:
        raise ValueError('role configuration needs a nonempty roles list')
    by_name = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('role entries must be objects')
        canonical = entry.get('role')
        name = normalize(canonical)
        if name == 'all' or name in by_name:
            raise ValueError('ambiguous or reserved configured role: ' + canonical)
        prompt = entry.get('startup_prompt')
        if (not isinstance(prompt, str) or not prompt or '\\' in prompt
                or PurePosixPath(prompt).is_absolute()
                or any(part in {'', '.', '..'} for part in prompt.split('/'))):
            raise ValueError('startup prompt must be a safe repository-relative path')
        schedules = entry.get('schedules')
        if (not isinstance(schedules, list)
                or not all(isinstance(value, str) and value.strip() for value in schedules)
                or len(set(schedules)) != len(schedules)):
            raise ValueError('role schedules need unique nonempty names')
        by_name[name] = canonical
    name = normalize(request)
    if name != 'all' and name not in by_name:
        raise ValueError('unknown role; select an exact configured role or all')
    roles = list(by_name.values()) if name == 'all' else [by_name[name]]
    # fresh=True represents an explicitly requested mode, not inferred permission.
    return {'roles': roles, 'destination_mode': 'new-chat' if fresh or name == 'all' else 'current-chat',
            'caller_is_coordinator': bool(fresh or name == 'all')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', nargs='+', help='configured role name or all')
    parser.add_argument('--fresh', action='store_true', help='select only when the human explicitly requests a fresh chat')
    parser.add_argument('--config', type=Path,
                        default=Path(__file__).resolve().parents[3] / 'agent-operations/roles.json')
    args = parser.parse_args()
    try:
        result = resolve_request(' '.join(args.role), json.loads(args.config.read_text()), fresh=args.fresh)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, 'ERROR: ' + str(exc) + '\n')
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
