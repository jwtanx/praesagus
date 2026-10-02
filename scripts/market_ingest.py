"""Offline synthetic fixture ingestion and read-only cutoff queries only."""
import argparse
import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors.moomoo_rest import ReadRequest, ReadResponse
from ingest.private_market_store import PrivateMarketStore, MarketStoreError, MAX_RAW, need


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    fixture = sub.add_parser('ingest-fixture');fixture.add_argument('--fixture', required=True)
    query = sub.add_parser('query');query.add_argument('--kind', choices=['snapshot', 'news'], required=True)
    query.add_argument('--cutoff', required=True);query.add_argument('--mode', choices=['strict', 'observation-known'], default='strict')
    query.add_argument('--limit', type=int, default=1000)
    attempts = sub.add_parser('attempts');attempts.add_argument('--cutoff', required=True);attempts.add_argument('--limit', type=int, default=1000)
    args = parser.parse_args(argv)
    failed = False
    try:
        if args.command == 'init':
            PrivateMarketStore(args.root, create=True);result = {'initialized': True}
        else:
            store = PrivateMarketStore(args.root)
            if args.command == 'ingest-fixture':
                with open(args.fixture, 'rb') as f:raw = f.read(MAX_RAW * 2 + 1)
                need(len(raw) <= MAX_RAW * 2)
                fixture = json.loads(raw)
                need(isinstance(fixture, dict) and set(fixture) == {'schema_version', 'origin', 'run_id', 'observed_at', 'ingested_at', 'method', 'path', 'query', 'request_body_base64', 'http_status', 'response_body_base64'}
                     and type(fixture['schema_version']) is int and fixture['schema_version'] == 1 and fixture['origin'] == 'synthetic')
                body = base64.b64decode(fixture['request_body_base64'], validate=True)
                response = base64.b64decode(fixture['response_body_base64'], validate=True)
                attempt = store.ingest(ReadRequest(fixture['method'], fixture['path'], fixture['query'], body, {}, 1),
                    ReadResponse(fixture['http_status'], response), run_id=fixture['run_id'], observed_at=fixture['observed_at'], ingested_at=fixture['ingested_at'], origin='synthetic')
                result = {'attempt_id': attempt.attempt_id, 'status': attempt.status, 'added': attempt.added}
            elif args.command == 'query':result = store.query(args.kind, args.cutoff, mode=args.mode, limit=args.limit)
            else:result = store.attempts(args.cutoff, limit=args.limit)
    except Exception:
        failed = True
    if failed:
        print('Private market operation failed; no provider/path details emitted.', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
