#!/usr/bin/env python3
"""Prepare current fixed50 from verified private store; never collect or approve."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ingest.private_forecast_refresh import io_private, run


def main(argv=None):
    try:
        if sys.version_info < (3, 11):
            raise ValueError()
        parser = io_private.Parser(description=__doc__)
        parser.add_argument('--config', required=True)
        parser.add_argument('--offline', action='store_true', required=True)
        args = parser.parse_args(argv)
        summary = run(args.config)
        print(json.dumps(summary))
        return 0 if summary['status'] == 'ready' else 2
    except Exception:
        print(json.dumps(dict(status='failed', reason='private-refresh-unavailable')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
