"""Manual pre-cutoff US collection to private draft; no publication or scheduling."""
import argparse
from importlib import import_module
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from ingest.daily_report_projection import project_report, write_private_draft
from ingest.market_collector import collect, job_digest, utc_now, validate_locator
from ingest.private_market_store import REPO, PrivateMarketStore, decode, need, parse_aware, private, safe

validator=import_module('scripts.daily-market-brief.validate_report_json')
FATAL_FAILURES={'storage-failed','cleanup-failed','clock-order'}


def read_json(path):
    with open(path,'rb') as stream:raw=stream.read(4*1024*1024+1)
    need(len(raw)<=4*1024*1024)
    return decode(raw)


def preflight_output(destination):
    path=Path(destination)
    need(path.is_absolute() and path==path.resolve() and not path.is_relative_to(REPO)
         and path.suffix=='.json'
         and not any(p.lower() in {'public','www','htdocs','artifacts','dist'} for p in path.parts)
         and not path.exists() and not path.is_symlink())
    private(path.parent,directory=True)


def run_quote_report(*,root,template_path,universe_path,locator,run_id,cutoff,window_start,
                     output,collector=collect,wall=utc_now):
    def run():
        start=parse_aware(window_start);end=parse_aware(cutoff);first=parse_aware(wall())
        need(start<=first<end and start<end)
        need(isinstance(run_id,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',run_id))
        validate_locator(locator);preflight_output(output)
        template=read_json(template_path);universe=read_json(universe_path)
        keys,instruments=validator.validate_universe(Path(universe_path),universe)
        codes=['US.'+ticker for (market,ticker) in instruments if market=='US']
        need(len(codes)==30 and len(instruments)==50 and universe['count_per_group']==5)
        context=(universe['effective_from'],keys,instruments,universe['taxonomy_id'],universe['groups'])
        validator.validate_report(Path(template_path),template,context)
        store=PrivateMarketStore(root)
        # Identifier-only read prevents ambiguous reuse, including post-cutoff old runs.
        with store._connection(readonly=True) as db:
            need(db.execute('SELECT 1 FROM runs WHERE id=?',(run_id,)).fetchone() is None)
        project_report(store,template,universe,run_id=run_id,cutoff=cutoff,expected_codes=codes)
        current=parse_aware(wall());need(first<=current and start<=current<end)
        history_end=end.astimezone(ZoneInfo('America/New_York')).date().isoformat()
        history=[{'code':code,'end':history_end} for code in codes]
        outcomes=collector(store,{'schema_version':1,'codes':codes,'history':history,'news':[]},locator,
                           run_id=run_id,wall=wall,job_seconds=5.0,run_seconds=300.0)
        expected_jobs=[{'kind':'snapshot','codes':codes},
                       *({'kind':'history',**item} for item in history)]
        need(isinstance(outcomes,list) and len(outcomes)==len(expected_jobs)
             and [item.job_id for item in outcomes]==[job_digest(job) for job in expected_jobs])
        need(not any(o.status=='not-persisted' or o.failure in FATAL_FAILURES for o in outcomes))
        selection=store.select_snapshots(run_id,cutoff,codes)
        # A nominal successful collector result without cutoff-available storage is degraded.
        draft=project_report(store,template,universe,run_id=run_id,cutoff=cutoff,expected_codes=codes)
        validator.validate_report(Path(template_path),draft,context)
        write_private_draft(output,draft)
        coverage=selection['coverage']
        us_selected=coverage['selected']['count']
        trend_counts={key:sum(row['moomoo_trend']['signal']==key for row in draft['forecasts'] if row['market']=='US')
                      for key in ('bullish','bearish','neutral','unavailable')}
        degraded=(us_selected!=30 or any(o.status!='success' or o.failure is not None for o in outcomes)
                  or trend_counts['unavailable']>0)
        return dict(private_draft_written=True,status='degraded' if degraded else 'us-coverage-complete',
                    expected_us=30,selected_us=us_selected,unselected_us=30-us_selected,
                    conflicted_us=coverage['conflicted']['count'],unsupported_my=20,
                    available_attempt_status_counts=selection['attempt_status_counts'],
                    trend_signal_counts=trend_counts,trend_end_date=history_end)
    return safe(run,category='daily-quote-report-failed')


def main(argv=None,*,collector=collect,wall=utc_now):
    class PrivateParser(argparse.ArgumentParser):
        def error(self,message):self.exit(2,'Daily quote report arguments invalid.\n')
    parser=PrivateParser(description=__doc__)
    for key in ('root','template','universe','credential-directory','app-key-name','run-id','cutoff','window-start','output'):
        parser.add_argument('--'+key,required=True)
    args=parser.parse_args(argv)
    failed=False
    try:
        result=run_quote_report(root=args.root,template_path=args.template,universe_path=args.universe,
            locator={'directory':args.credential_directory,'app_key_name':args.app_key_name},
            run_id=args.run_id,cutoff=args.cutoff,window_start=args.window_start,output=args.output,
            collector=collector,wall=wall)
    except Exception:failed=True
    if failed:
        print('Daily quote report failed; no provider or private-path details emitted.',file=sys.stderr);return 1
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='us-coverage-complete' else 1


if __name__=='__main__':raise SystemExit(main())
