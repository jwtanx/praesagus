#!/usr/bin/env python3
"""Explicit online released collection or offline current fixed50 export."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from ingest import private_forecast_pipeline as pipeline


def main(argv=None):
    try:
        if sys.version_info < (3,11): raise ValueError()
        p=pipeline.io.Parser(description=__doc__)
        modes=p.add_mutually_exclusive_group(required=True)
        modes.add_argument('--online',action='store_true');modes.add_argument('--offline',action='store_true')
        p.add_argument('--config',required=True);p.add_argument('--release')
        args=p.parse_args(argv)
        if args.online:
            if not args.release: raise ValueError()
            summary,status=pipeline.execute(args.config,args.release)
        else:
            if args.release: raise ValueError()
            summary=pipeline.run_offline(args.config)
            status=0 if summary['status']=='ready' else 2
        print(json.dumps(summary));return status
    except Exception:
        print(json.dumps(dict(status='failed',reason='private-pipeline-unavailable')));return 1


if __name__=='__main__':raise SystemExit(main())
