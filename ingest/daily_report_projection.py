"""Deterministic private quote overlay; no collection, publication or forecasts."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from importlib import import_module
import math
import os
from pathlib import Path
import re
import tempfile

from ingest.private_market_store import REPO, canonical, check_secrets, need, parse_aware, private, safe

GAPS = ['currency_unknown', 'session_unknown', 'adjustment_unknown', 'prior_close_unknown']
QUOTE_KEYS = {'price','volume','source_at','observed_at','ingested_at','known_at','cutoff',
              'origin','currency','session','adjustment','prior_close','gaps','provenance'}
EXCLUSIONS = {'source_time_unknown','source_time_after_cutoff','source_time_after_observation','price_unusable'}
REASONS = set(GAPS) | {'no_eligible_quote','no_returned_quote','no_available_attempts','same_time_conflict'}
PROVENANCE_KEYS = {'provider','connector','capture_authenticity','rights_status',
                   'attempt_id','raw_hash','semantic_hash','run_id'}


def epoch_time(milliseconds):
    return (datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=milliseconds)).isoformat(timespec='milliseconds')


def validate_observed_quote(quote, cutoff):
    """Strict optional schema3 point contract, shared by projection and validator."""
    need(isinstance(quote,dict) and set(quote)==QUOTE_KEYS)
    for key in ('price','volume'):
        value=quote[key]
        need(type(value) in (int,float) and math.isfinite(value) and value>=0
             and (key!='price' or value>0))
    need(all(quote[k] is None for k in ('currency','session','adjustment','prior_close')))
    need(quote['origin'] in ('synthetic','trusted-capture'))
    gaps=quote['gaps']
    need(isinstance(gaps,list) and 1<=len(gaps)<=16 and set(GAPS)<=set(gaps)
         and all(isinstance(g,str) and 0<len(g)<=256 for g in gaps))
    times={k:parse_aware(quote[k]) for k in ('source_at','observed_at','ingested_at','known_at','cutoff')}
    need(times['cutoff']==parse_aware(cutoff)
         and times['source_at']<=times['observed_at']<=times['ingested_at']<=times['known_at']<=times['cutoff'])
    provenance=quote['provenance']
    need(isinstance(provenance,dict) and set(provenance)==PROVENANCE_KEYS
         and provenance['provider']=='moomoo-rest' and provenance['connector']=='moomoo-rest-capture'
         and provenance['capture_authenticity']=='caller-supplied-unverified'
         and provenance['rights_status']=='unconfirmed'
         and isinstance(provenance['run_id'],str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',provenance['run_id']))
    need(all(isinstance(provenance[k],str) and re.fullmatch(r'[0-9a-f]{64}',provenance[k])
             for k in ('attempt_id','raw_hash','semantic_hash')))
    check_secrets(quote)


def project_report(store,template,universe,*,run_id,cutoff,expected_codes):
    """Pure mapping of an accepted template and explicit store selection."""
    def project():
        need(isinstance(template,dict) and template.get('schema_version')==3)
        check_secrets(template)
        validator=import_module('scripts.daily-market-brief.validate_report_json')
        keys,instruments=validator.validate_universe(Path('universe.json'),universe)
        need(universe['count_per_group']==5 and len(instruments)==50)
        config=template['watchlist_config']
        need(config['taxonomy_id']==universe['taxonomy_id'] and config['count_per_group']==5
             and [{k:g[k] for k in ('key','label','emoji')} for g in config['groups']]==
                 [{k:g[k] for k in ('key','label','emoji')} for g in universe['groups']])
        frozen=parse_aware(cutoff)
        need(parse_aware(template['metadata']['as_of'])==frozen
             and template['metadata']['date']==frozen.astimezone(timezone(timedelta(hours=8))).date().isoformat())
        expected=['US.'+ticker for (market,ticker) in instruments if market=='US']
        need(isinstance(expected_codes,list) and len(expected_codes)==len(set(expected_codes))
             and set(expected_codes)==set(expected))
        rows=template['forecasts']
        need(isinstance(rows,list) and len(rows)==50)
        symbols=[(r['market'],r['ticker']) for r in rows]
        need(len(set(symbols))==50 and set(symbols)==set(instruments))
        for row in rows:
            instrument=instruments[(row['market'],row['ticker'])]
            need(row['sector_category']==instrument['group'] and row['asset_type']==instrument['asset_type']
                 and row['country']==instrument['country'] and row['currency']==instrument['currency'])
            need(row.get('direction')=='unknown' and row.get('forecast_status')=='unavailable'
                 and row.get('confidence')=='unavailable'
                 and all(row.get(k) is None for k in ('estimated_mid_case_value','range_low_value','range_high_value')))
        selection=store.select_snapshots(run_id,cutoff,expected_codes)
        output=deepcopy(template)
        output['metadata']['private_draft']=True
        output['metadata']['quote_cutoff']=cutoff
        for row in output['forecasts']:
            row.pop('quote_provenance',None)
            row.update(current_price='Unavailable',current_price_value=None,quote_status='missing',
                       price_as_of='No verified reference quote at report cutoff',observed_quote=None)
            point=selection['quotes'].get('US.'+row['ticker']) if row['market']=='US' else None
            reasons=['MY_unattempted_unsupported']
            if point:
                need(isinstance(point['gap_reasons'],list) and set(point['gap_reasons'])<=REASONS
                     and set(point['excluded_counts'])<=EXCLUSIONS)
                reasons=[*point['gap_reasons'],*point['excluded_counts']]
                if point['quote'] is None:
                    if selection['attempt_status_counts']['failed']:reasons.append('collection_failed_attempt')
                    if selection['attempt_status_counts']['all-missing']:reasons.append('all_missing_attempt')
            row['data_gaps']=list(dict.fromkeys([*row.get('data_gaps',[]),*reasons]))
            if point and point['quote'] is not None:
                record=point['quote'];p=point['provenance']
                need(record['code']=='US.'+row['ticker'])
                quote=dict(price=record['price'],volume=record['volume'],source_at=epoch_time(p['source_ms']),
                    observed_at=p['observed_at'],ingested_at=p['ingested_at'],known_at=epoch_time(p['known_ms']),
                    cutoff=cutoff,origin=p['origin'],currency=None,session=None,adjustment=None,prior_close=None,
                    gaps=list(GAPS),provenance={k:p[k] for k in PROVENANCE_KEYS if k!='run_id'})
                quote['provenance']['run_id']=run_id
                validate_observed_quote(quote,cutoff)
                row['observed_quote']=quote
        return output
    return safe(project,category='projection-failed')


def write_private_draft(destination,report):
    """Atomic link publication inside an existing owned0700 private directory."""
    def write():
        path=Path(destination)
        need(path.is_absolute() and path==path.resolve() and not path.is_relative_to(REPO)
             and path.suffix=='.json'
             and not any(p.lower() in {'public','www','htdocs','artifacts','dist'} for p in path.parts))
        private(path.parent,directory=True)
        need(not path.exists() and not path.is_symlink())
        raw=(canonical(report)+'\n').encode()
        temporary=None
        try:
            fd,name=tempfile.mkstemp(prefix='.private-draft-',dir=path.parent);temporary=Path(name)
            with os.fdopen(fd,'wb') as stream:
                stream.write(raw);stream.flush();os.fchmod(stream.fileno(),0o400);os.fsync(stream.fileno())
            os.link(temporary,path,follow_symlinks=False)
            fd=os.open(path.parent,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
        finally:
            if temporary is not None:temporary.unlink()
    return safe(write,category='private-draft-failed')
