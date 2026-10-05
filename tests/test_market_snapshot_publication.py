"""Synthetic projection and permission-gate tests; no live API or Keychain access."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

import pytest

from ingest.daily_report_projection import (NEWS_KEYWORDS, RIGHTS_FIELDS, RIGHTS_USES,
    project_public_market_snapshot, validate_market_snapshot)

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('publish_market_snapshot',ROOT/'scripts/daily-market-brief/publish_market_snapshot.py')
publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)
projection_spec=importlib.util.spec_from_file_location('projection_fixture',ROOT/'tests/test_daily_report_projection.py')
fixture_module=importlib.util.module_from_spec(projection_spec);projection_spec.loader.exec_module(fixture_module)

@pytest.fixture
def capture(tmp_path):
    store,_,universe,_=fixture_module.inputs.__wrapped__(tmp_path)
    return store,universe

def rights(**changes):
    now=datetime.now(timezone.utc)
    result={'schema_version':1,'provider':'moomoo-rest','authority':'synthetic fixture authority',
      'markets':['US'],'fields':sorted(RIGHTS_FIELDS),'uses':sorted(RIGHTS_USES),
      'evidence_url':'https://example.test/permission','verified_by':'synthetic reviewer',
      'verified_at':(now-timedelta(minutes=1)).isoformat(),'expires_at':(now+timedelta(days=1)).isoformat()}
    result.update(changes);return result

def selected_store(store,universe,*,attempts=(),news=()):
    codes=['US.'+item['ticker'] for group in universe['groups'] for item in group['instruments'] if item['market']=='US']
    selection=store.select_snapshots('synthetic','2026-10-02T00:00:00Z',codes)
    selection['quotes']['US.SPY']['provenance']['origin']='trusted-capture'
    class SyntheticStore:
        def select_snapshots(self,*args):return selection
        def attempts(self,*args,**kwargs):return list(attempts)
        def query(self,*args,**kwargs):return list(news)
    return SyntheticStore()

def test_private_projection_preserves_50_rows_and_fails_closed(capture):
    store,universe=capture
    # The fixture explicitly models the existing worker's trusted-capture label; no API is called.
    snapshot=project_public_market_snapshot(selected_store(store,universe),universe,run_id='synthetic',cutoff='2026-10-02T00:00:00Z')
    assert len(snapshot['quotes'])==50
    assert sum(q['market']=='US' for q in snapshot['quotes'])==30
    assert sum(q['market']=='MY' and q['status']=='unsupported' for q in snapshot['quotes'])==20
    assert sum(q['status']=='selected' for q in snapshot['quotes'])==1
    assert [q['keyword'] for q in snapshot['news_queries']]==list(NEWS_KEYWORDS)
    validate_market_snapshot(snapshot,require_rights=False)
    with pytest.raises(ValueError):validate_market_snapshot(snapshot,require_rights=True)

def test_permitted_synthetic_snapshot_is_allowlisted_and_news_states_distinct(capture):
    store,universe=capture;now=datetime.now(timezone.utc)
    attempts=[{'run_id':'synthetic','kind':'news','query':{'symbol':'SPY'},'status':'successful-empty'},
      {'run_id':'synthetic','kind':'news','query':{'symbol':'QQQ'},'status':'failed'}]
    snapshot=project_public_market_snapshot(selected_store(store,universe,attempts=attempts),universe,
      run_id='synthetic',cutoff='2026-10-02T00:00:00Z',rights_evidence=rights(),publication_time=now.isoformat())
    assert snapshot['rights']['status']=='verified'
    assert [q['status'] for q in snapshot['news_queries']]==['empty','unavailable']
    validate_market_snapshot(snapshot,require_rights=True)
    serialized=__import__('json').dumps(snapshot)
    assert all(value not in serialized for value in ('run_id','attempt_id','raw_hash','semantic_hash','private_path'))

@pytest.mark.parametrize('change',[{'markets':['MY']},{'fields':['quote.price']},
    {'uses':['public-website-display']},{'expires_at':'2000-01-01T00:00:00Z'}])
def test_rights_gate_rejects_insufficient_or_expired_evidence(capture,change):
    store,universe=capture
    with pytest.raises(ValueError):project_public_market_snapshot(store,universe,run_id='synthetic',
        cutoff='2026-10-02T00:00:00Z',rights_evidence=rights(**change))

def test_rights_record_locator_is_explicit_private_and_outside_repo(tmp_path):
    path=tmp_path/'rights.json';path.write_text('{}');path.chmod(0o600)
    assert publisher.read_rights_evidence(path)=={}
    with pytest.raises(ValueError):publisher.read_rights_evidence(ROOT/'AGENTS.md')

def test_public_cli_requires_rights_locator():
    with pytest.raises(SystemExit) as error:publisher.main(['--root','/private/store','--run-id','synthetic',
        '--cutoff','2026-10-02T00:00:00Z','--public-output','/tmp/2026-10-02.json'])
    assert error.value.code==2
