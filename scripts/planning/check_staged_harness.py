"""Check harness filenames and ticket keys in the staged Git index only."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def check_staged_harness(root):
    paths = subprocess.check_output([
        'git', '-C', str(root), 'diff', '--cached', '--no-renames',
        '--name-only', '--diff-filter=ACMR', '-z',
    ]).split(b'\0')
    for raw_path in filter(None, paths):
        path = raw_path.decode('utf-8', errors='surrogateescape')
        if not path.endswith('.harness.json'):
            continue
        name = Path(path).name
        if not re.fullmatch(r'PRSG-(0|[1-9][0-9]*)\.harness\.json', name):
            raise ValueError('Harness filename must be PRSG-N.harness.json: ' + repr(path))
        staged = subprocess.check_output(['git', '-C', str(root), 'show', ':' + path])
        try:
            data = json.loads(staged)
        except (ValueError, UnicodeError):
            raise ValueError('Staged harness is not valid JSON: ' + repr(path)) from None
        if not isinstance(data, dict) or data.get('ticket_key') != name.removesuffix('.harness.json'):
            raise ValueError('Staged harness ticket_key must match its filename: ' + repr(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, required=True)
    args = parser.parse_args()
    try:
        check_staged_harness(args.repo_root)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
