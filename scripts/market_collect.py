"""Explicit manual private collector; no scheduler, projection or public export."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest.market_collector import collect, worker_main, MAX_INPUT
from ingest.private_market_store import PrivateMarketStore, decode


def main(argv=None):
    args_in = sys.argv[1:] if argv is None else argv
    if args_in == ['--worker']:
        return worker_main(sys.stdin.buffer, sys.stdout.buffer)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True);p.add_argument('--plan', required=True)
    p.add_argument('--credential-directory', required=True);p.add_argument('--app-key-name', required=True)
    p.add_argument('--run-id', required=True)
    a = p.parse_args(args_in)
    failed = False
    try:
        with open(a.plan, 'rb') as f:raw = f.read(MAX_INPUT+1)
        if len(raw)>MAX_INPUT:raise ValueError()
        plan = decode(raw)
        store = PrivateMarketStore(a.root)
        outcomes = collect(store, plan, {'directory': a.credential_directory, 'app_key_name': a.app_key_name}, run_id=a.run_id)
    except Exception:failed = True
    if failed:
        print('Private collector failed; no provider or private-path details emitted.', file=sys.stderr);return 1
    print(json.dumps({'run_id':a.run_id,'outcomes':[{'job_id':o.job_id,'status':o.status,'attempt_id':o.attempt_id,'failure':o.failure} for o in outcomes]}))
    return 0 if outcomes and all(o.failure is None and o.status in ('success','partial','successful-empty','all-missing') for o in outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
