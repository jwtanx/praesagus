"""Explicit private draft only; no collection, publication or scheduling."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from ingest.daily_report_projection import project_report, write_private_draft
from ingest.private_market_store import PrivateMarketStore, decode
from validate_report_json import validate_report, validate_universe


def main(argv=None):
    class PrivateParser(argparse.ArgumentParser):
        def error(self,message):self.exit(2,'Private draft arguments invalid.\n')
    parser=PrivateParser(description=__doc__)
    for key in ('root','template','universe','run-id','cutoff','expected-codes','output'):
        parser.add_argument('--'+key,required=True)
    args=parser.parse_args(argv)
    failed=False
    try:
        def read(path):
            with open(path,'rb') as stream:raw=stream.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:raise ValueError()
            return decode(raw)
        template=read(args.template);universe=read(args.universe);expected=read(args.expected_codes)
        keys,instruments=validate_universe(Path(args.universe),universe)
        context=(universe['effective_from'],keys,instruments,universe['taxonomy_id'],universe['groups'])
        validate_report(Path(args.template),template,context)
        result=project_report(PrivateMarketStore(args.root),template,universe,run_id=args.run_id,
                              cutoff=args.cutoff,expected_codes=expected)
        validate_report(Path(args.template),result,context)
        write_private_draft(args.output,result)
    except Exception:failed=True
    if failed:
        print('Private draft failed; no provider or private-path details emitted.',file=sys.stderr);return 1
    print(json.dumps({'private_draft_written':True}));return 0


if __name__=='__main__':raise SystemExit(main())
