"""Fictional supplied/XML fixtures only: no feeds, auth, models or downloads."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/stock-research'))
news = importlib.import_module('news')
NOW = 1800000000000
H = 'a' * 64


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('network forbidden in news fixture tests')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


def policy(source='fictional', **changes):
    return {'schema_version': 1, 'source_id': source, 'enabled': True,
            'endpoint': f'https://{source}.example.test/feed.xml',
            'source_url': f'https://{source}.example.test/rights',
            'rights_status': 'verified', 'polling_status': 'verified', 'known_at_ms': NOW - 100000,
            'evidence_hash': H, 'text_scopes': ['headline-only', 'full-permitted'],
            'poll_interval_ms': 300000, 'permitted_min_interval_ms': 300000,
            'max_age_ms': 86400000, **changes}


def relevance(**changes):
    return {'code': 'US.DEMO', 'security_id': 123, 'target_entity_id': 'issuer:fictional',
            'target_aspect': 'operations', 'sentiment_scope': 'issuer-operations',
            'relevance_kind': 'issuer_company', 'subject_identity': 'issuer:fictional',
            'status': 'verified', 'reason': None, 'evidence_hash': H,
            'known_at_ms': NOW - 10000, **changes}


def record(p=None, **changes):
    p = policy() if p is None else p
    raw = {'canonical_url': 'https://fictional.example.test/article/1',
           'event_id': 'reviewed:event-1', 'dedup_version': 'reviewed-v1',
           'dedup_evidence_hash': H, 'representative_evidence_hash': H,
           'headline': 'Fictional issuer opens facility', 'permitted_text': 'Fictional supplied evidence.',
           'text_scope': 'full-permitted', 'language': 'en',
           'publication_raw': '2027-01-15T07:59:00+00:00', 'publication_timezone': '+0000',
           'publication_at_ms': NOW - 60000, 'first_seen_at_ms': NOW - 50000,
           'retrieved_at_ms': NOW - 40000, 'revision_known_at_ms': NOW - 40000,
           'ingestion_at_ms': NOW - 30000, 'rights_known_at_ms': NOW - 100000,
           'dedup_known_at_ms': NOW - 20000, 'representative_known_at_ms': NOW - 10000,
           'age_anchor_at_ms': NOW - 60000, 'relevances': [relevance()], **changes}
    return news.normalize_supplied_news([raw], {'source_id': p['source_id'], 'source_url': p['source_url'],
                                               'source_receipt_hash': H}, p)[0]


def select(records, p=None, cutoff=NOW):
    return news.select_news_as_of(records, cutoff, policy() if p is None else p)


def rss(*, title='Fictional title', description='Fictional evidence', link='https://fictional.example.test/article/1',
        publication=None, count=1):
    publication = publication or datetime.fromtimestamp((NOW - 60000) / 1000, timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    item = f'<item><title>{title}</title><link>{link}</link><pubDate>{publication}</pubDate><description>{description}</description></item>'
    return ('<rss version="2.0"><channel>' + item * count + '</channel></rss>').encode()


def collect(responses, *, p=None, cache=None, now=NOW, mode='collect'):
    requests = []
    pending = iter(responses)
    def transport(request):
        requests.append(request)
        value = next(pending)
        if isinstance(value, Exception):
            raise value
        return value
    value = news.collect_configured_news([policy() if p is None else p], transport=transport,
                                         clock_ms=lambda: now, cache=cache, mode=mode)
    return value, requests


def generation(parent, records=None, receipts=None, offset=0):
    return news.append_cache_generation([record()] if records is None else records,
        [] if receipts is None else receipts, output_parent=parent,
        generated_at=datetime(2026, 10, 16, tzinfo=timezone.utc) + timedelta(seconds=offset))


def rewrite_artifact(folder, name, value):
    data = news.encoded(value)
    (folder / name).write_bytes(data)
    manifest = json.loads((folder / 'manifest.json').read_bytes())
    manifest['artifacts'][name].update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    (folder / 'manifest.json').write_bytes(news.encoded(manifest))


def test_contract_and_non_mutation():
    value = record()
    assert set(value) == news.RECORD_KEYS
    assert set(value['relevances'][0]) == news.RELEVANCE_KEYS
    before = copy.deepcopy(value)
    result = select([value])
    assert result['status'] == 'available'
    assert result['records'] == [value] and value == before
    assert result['cutoff_ms'] == NOW
    assert result['source_dispositions'][0]['status'] == 'permitted'
    assert result['forecast_use_allowed'] is False
    assert result['coverage']['complete_source_coverage'] is False
    result['records'][0]['headline'] = 'changed copy'
    assert value == before


@pytest.mark.parametrize('field', [k for k in news.MS_FIELDS if k not in {'publication_at_ms', 'first_seen_at_ms', 'age_anchor_at_ms'}])
def test_future_consumed_evidence_rejected(field):
    changes = {field: NOW + 1}
    if field in {'retrieved_at_ms', 'revision_known_at_ms'}:
        changes['ingestion_at_ms'] = NOW + 2
    assert select([record(**changes)])['rejected'][0]['reason'] == 'future-evidence'


@pytest.mark.parametrize('field', news.MS_FIELDS)
def test_missing_time_remains_unavailable(field):
    assert select([record(**{field: None})])['rejected'][0]['reason'] == 'required-time-unavailable'


@pytest.mark.parametrize('bad', [True, False, None, 0, -1, 1.0, '0', '-2', '1.0', 'x', [], 2**63])
def test_invalid_typed_security_id(bad):
    with pytest.raises(news.NewsError, match='invalid-relevance-id'):
        record(relevances=[relevance(security_id=bad)])


def test_exact_type_and_entity_aspect_scope_not_coerced_or_inverted():
    relations = [relevance(), relevance(security_id='123'), relevance(target_aspect='management'),
                 relevance(relevance_kind='manager_corporate'), relevance(relevance_kind='fund_product'),
                 relevance(relevance_kind='underlying_context'), relevance(relevance_kind='macro_context'),
                 relevance(sentiment_scope='fund-costs'), relevance(target_entity_id='fund:fictional')]
    result = select([record(relevances=relations)])
    assert len(result['records']) == len(relations)
    assert {type(r['relevances'][0]['security_id']) for r in result['records']} == {int, str}
    assert {r['relevances'][0]['relevance_kind'] for r in result['records']} == news.KINDS
    assert all('sentiment_score' not in r and len(r['relevances']) == 1 for r in result['records'])


@pytest.mark.parametrize('rel,reason', [(relevance(status='unavailable', reason='ambiguous actor'), 'relevance-unverified'),
    (relevance(known_at_ms=None), 'relevance-time-unavailable'), (relevance(known_at_ms=NOW+1), 'future-relevance')])
def test_partial_relevance_rejections_visible(rel, reason):
    rel['code'] = 'US.OTHER'
    result = select([record(relevances=[relevance(), rel])])
    assert len(result['records']) == 1
    rejected = result['rejected'][0]
    assert rejected['reason'] == reason and rejected['relevance'] == rel
    assert rejected['text_version_id'] == result['records'][0]['text_version_id']


def test_revision_as_of_and_same_time_conflict():
    original = record()
    later = record(headline='Revised fictional headline', revision_known_at_ms=NOW+10,
                   retrieved_at_ms=NOW+10, ingestion_at_ms=NOW+10)
    assert select([original, later])['records'] == [original]
    assert select([original, later], cutoff=NOW+20)['records'] == [later]
    conflict = record(headline='Conflicting revision')
    with pytest.raises(news.NewsError, match='conflicting-same-time-revision'):
        select([original, conflict])


def test_revision_freshness_anchor_cannot_change():
    changed = record(first_seen_at_ms=NOW-49000)
    with pytest.raises(news.NewsError, match='revision-freshness-anchor-changed'):
        select([record(), changed])
    assert select([record()], policy(max_age_ms=1))['records'] == []  # policy receipt mismatch is also explicit.
    p = policy(max_age_ms=100)
    assert select([record(p)], p)['rejected'][0]['reason'] == 'stale-event'


def test_cross_source_dedup_and_as_of_representative():
    a, b = policy('source-a'), policy('source-b')
    first, second = record(a), record(b, canonical_url='https://other.example.test/article/2', first_seen_at_ms=NOW-45000)
    result = select([second, first], [a, b])
    assert len(result['records']) == 1 and result['records'][0]['source_id'] == 'source-a'
    later_rep = record(a, representative_known_at_ms=NOW+1)
    result = select([second, later_rep], [a, b])
    assert result['records'][0]['source_id'] == 'source-b'
    assert result['rejected'][0]['reason'] == 'future-evidence'


def test_event_anchor_and_relevance_conflicts_rejected():
    second = record(canonical_url='https://other.example.test/article/2', age_anchor_at_ms=NOW-61000)
    with pytest.raises(news.NewsError, match='event-freshness-anchor-conflict'):
        select([record(), second])
    with pytest.raises(news.NewsError, match='conflicting-relevance'):
        select([record(relevances=[relevance(), relevance(evidence_hash='b'*64)])])


def test_selected_fanout_bounded_before_deepcopy(monkeypatch):
    monkeypatch.setattr(news, 'MAX_SELECTED', 2)
    with pytest.raises(news.NewsError, match='selected-row-budget'):
        select([record(relevances=[relevance(code=f'US.D{i}') for i in range(3)])])


def test_selected_expanded_text_budget():
    text = 'x' * 32000
    records = [record(canonical_url=f'https://fictional.example.test/{i}', event_id=f'event-{i}',
                      permitted_text=text, relevances=[relevance(code=f'US.D{j}') for j in range(100)]) for i in range(2)]
    with pytest.raises(news.NewsError, match='selected-text-budget'):
        select(records)


@pytest.mark.parametrize('change', [{'enabled':False}, {'rights_status':'unknown'}, {'polling_status':'unknown'}, {'known_at_ms':NOW+1}])
def test_disabled_or_unknown_policy_zero_calls(change):
    result, requests = collect([], p=policy(**change))
    assert not requests and result['receipts'][0]['status'] == 'disabled'


@pytest.mark.parametrize('mode', ['off','offline'])
def test_off_modes_zero_calls(mode):
    result, requests = collect([], mode=mode)
    assert not requests and result['receipts'][0]['reason'] == mode


def test_all_real_candidates_disabled():
    result = news.collect_configured_news(news.DEFAULT_SOURCES, clock_ms=lambda: NOW, mode='collect',
                                         transport=lambda _: pytest.fail('real source request'))
    assert len(result['receipts']) == 3 and all(r['status'] == 'disabled' for r in result['receipts'])


@pytest.mark.parametrize('changes', [{'poll_interval_ms':60000}, {'poll_interval_ms':1}, {'permitted_min_interval_ms':400000},
    {'endpoint':'http://fictional.example.test/feed'}, {'endpoint':'https://user:password@fictional.example.test/feed'},
    {'endpoint':'https://fictional.example.test/feed?token=private'}, {'text_scopes':[['nested']]},
    {'limits':{'response_bytes':news.MAX_RESPONSE+1}}, {'schema_version':True}, {'api_key':'fictional-private'}])
def test_invalid_policy_fails_before_transport(changes):
    with pytest.raises(news.NewsError):
        collect([], p=policy(**changes))


def test_explicit_sixty_second_permission_and_stricter_limits():
    p = policy(poll_interval_ms=60000, permitted_min_interval_ms=60000, limits={'response_bytes':100})
    result, requests = collect([news.NewsResponse(200, rss())], p=p)
    assert requests[0].max_bytes == 100
    assert result['receipts'][0]['reason'] == 'response-budget'


def test_success_request_contract_and_unannotated_feed_unavailable():
    result, requests = collect([news.NewsResponse(200, rss(), {'ETag':'"v1"'})])
    request = requests[0]
    assert request.timeout_seconds == 10 and request.max_bytes == news.MAX_RESPONSE
    assert set(dict(request.headers)) == {'Accept'}
    assert request.endpoint == policy()['endpoint']
    assert len(result['records']) == 1
    assert select(result['records'])['rejected'][0]['reason'] == 'verified-relevance-unavailable'
    assert result['records'][0]['age_anchor_at_ms'] == NOW-60000


def test_conditional_304_200_unchanged_and_changed_envelope_never_refresh():
    first, _ = collect([news.NewsResponse(200, rss(), {'ETag':'"v1"', 'Last-Modified':'Fri, 16 Oct 2026 00:00:00 GMT'})])
    cache = first['cache']
    second, requests = collect([news.NewsResponse(304)], cache=cache, now=NOW+300000)
    assert dict(requests[0].headers)['If-None-Match'] == '"v1"'
    assert 'If-Modified-Since' in dict(requests[0].headers)
    assert second['records'] == first['records']
    third, _ = collect([news.NewsResponse(200, rss())], cache=cache, now=NOW+600000)
    assert third['receipts'][0]['reason'] == 'unchanged' and third['records'] == first['records']
    different_body = rss().replace(b'<channel>',b'<channel><title>Changed feed envelope</title>')
    fourth, _ = collect([news.NewsResponse(200, different_body)], cache=cache, now=NOW+900000)
    assert fourth['records'] == first['records']


def test_changed_text_appends_revision_and_keeps_original_freshness():
    first, _ = collect([news.NewsResponse(200, rss())])
    second, _ = collect([news.NewsResponse(200, rss(title='Changed title'))], cache=first['cache'], now=NOW+300000)
    assert len(second['records']) == 2
    old, new = second['records']
    assert old['article_id'] == new['article_id'] and old['text_version_id'] != new['text_version_id']
    assert old['first_seen_at_ms'] == new['first_seen_at_ms'] == NOW
    assert old['age_anchor_at_ms'] == new['age_anchor_at_ms'] == NOW-60000
    assert new['revision_known_at_ms'] == NOW+300000


@pytest.mark.parametrize('status', [429,503])
@pytest.mark.parametrize('retry', ['900', 'invalid', 'Fri, 16 Oct 2037 00:00:00 GMT'])
def test_retry_after_visible_and_shared_cache_suppresses_attempt(status, retry):
    cache = news.empty_cache()
    first, requests = collect([news.NewsResponse(status, headers={'Retry-After':retry})], cache=cache)
    assert len(requests) == 1 and first['receipts'][0]['reason'] == 'retry-after'
    second, requests = collect([], cache=cache, now=NOW+300001 if retry=='900' else NOW+1)
    assert not requests
    assert second['receipts'][0]['reason'] in {'backoff','poll-not-due'}
    assert len(cache['attempts']) == 1


def test_exception_redacted_no_retry_and_attempt_retained():
    cache = news.empty_cache()
    result, requests = collect([RuntimeError('fictional-private-password-marker')], cache=cache)
    assert len(requests) == 1 and result['receipts'][0]['reason'] == 'transport-failure'
    assert 'fictional-private-password-marker' not in json.dumps(result)
    again, requests = collect([], cache=cache, now=NOW+1)
    assert not requests and len(cache['attempts']) == 1
    assert again['receipts'][0]['status'] == 'unavailable'


def test_total_attempt_and_source_caps_no_calls():
    cache = news.empty_cache()
    cache['attempts'] = [{'source_id':f's{i}', 'at_ms':NOW-100} for i in range(3)]
    result, requests = collect([], cache=cache)
    assert not requests and result['receipts'][0]['reason'] == 'request-budget'
    with pytest.raises(news.NewsError, match='source-budget'):
        news.collect_configured_news([policy(f's{i}') for i in range(4)], clock_ms=lambda:NOW,
            transport=lambda _:pytest.fail('budget request'), mode='collect')


@pytest.mark.parametrize('response,reason', [(news.NewsResponse(304),'invalid-response'),
    (news.NewsResponse(302, headers={'Location':'https://other.example.test'}),'http-error'),
    (news.NewsResponse(200,rss(),url='https://other.example.test'),'invalid-response'),
    (news.NewsResponse(200,rss(),headers={'ETag':'bad\r\nprivate'}),'invalid-response'),
    (news.NewsResponse(200,rss(),headers={'ETag':'arbitrary private exception'}),'invalid-feed'),
    (news.NewsResponse(500,b'fictional private provider error'),'http-error'),
    (news.NewsResponse(200,b'x'*(news.MAX_RESPONSE+1)),'response-budget')])
def test_bad_response_rejected_redacted_no_followup(response, reason):
    result, requests = collect([response])
    assert len(requests)==1 and result['receipts'][0]['reason']==reason
    assert not result['records']
    assert 'fictional private provider error' not in json.dumps(result)


@pytest.mark.parametrize('body', [b'<!DOCTYPE rss [<!ENTITY x "boom">]><rss/>',
    '<!DOCTYPE rss><rss/>'.encode('utf-16'), b'<rss>', b'<other/>',
    rss(count=2), rss(publication='2026-10-16'), rss(title='&lt;b&gt;HTML&lt;/b&gt;'),
    rss(link='https://fictional.example.test/a?api_key=private'), rss(title='x'*32769),
    b'<rss version="2.0"><channel><item><title>missing rest</title></item></channel></rss>'])
def test_unsafe_malformed_or_duplicate_xml_fails_first_response(body):
    result, requests = collect([news.NewsResponse(200,body)])
    assert len(requests)==1 and result['receipts'][0]['status']=='rejected'
    assert not result['records']


def test_atom_supported_and_no_enclosure_fetch():
    body = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Fictional</title>
    <link href="https://fictional.example.test/article/1"/><published>2027-01-15T07:59:00Z</published>
    <summary>Fictional text</summary><link rel="enclosure" href="https://ignored.example.test/file"/>
    </entry></feed>'''
    result, requests = collect([news.NewsResponse(200,body)])
    assert len(requests)==1 and len(result['records'])==1


@pytest.mark.parametrize('limit,value', [('articles',1),('article_text_bytes',10),('total_text_bytes',20),('cache_bytes',100)])
def test_stricter_source_input_budgets_reject_without_truncation(limit,value):
    p=policy(limits={limit:value})
    body = rss(count=2) if limit=='articles' else rss()
    result,_=collect([news.NewsResponse(200,body)],p=p)
    assert result['receipts'][0]['status']=='rejected' and result['records']==[]


def test_supplied_aggregate_text_budget():
    records = [record(canonical_url=f'https://fictional.example.test/{i}', permitted_text='x'*32000) for i in range(132)]
    with pytest.raises(news.NewsError,match='aggregate-text-budget'):
        select(records)


@pytest.mark.parametrize('changes', [{'content_hash':'b'*64},{'article_id':'b'*64},{'text_version_id':'b'*64},
    {'schema_version':True},{'source_id':'other'},{'policy_hash':'b'*64},{'headline':'x\n'},
    {'publication_at_ms':NOW+1000},{'rights_known_at_ms':True},{'text_scope':[]},
    {'relevances':[relevance(relevance_kind=[])]}])
def test_malformed_supplied_record_rejected(changes):
    with pytest.raises(news.NewsError):
        record(**changes)


def test_policy_and_source_receipt_binding():
    value=record()
    p=policy(evidence_hash='b'*64)
    assert select([value],p)['rejected'][0]['reason']=='policy-binding-mismatch'
    assert select([value],policy(enabled=False))['rejected'][0]['reason']=='source-policy-disabled'
    with pytest.raises(news.NewsError, match='source-receipt-mismatch'):
        news.normalize_supplied_news([],{'source_id':'other','source_url':policy()['source_url'],'source_receipt_hash':H},policy())


def test_private_immutable_generation_roundtrip_conditional_state(tmp_path):
    parent=tmp_path/'cache'
    result,_=collect([news.NewsResponse(200,rss(),{'ETag':'"v1"'})])
    first=generation(parent,result['records'],result['receipts'])
    before={p.name:p.read_bytes() for p in first.iterdir()}
    assert (os.stat(parent).st_mode&0o777)==0o700
    assert (os.stat(first).st_mode&0o777)==0o700
    assert all((os.stat(p).st_mode&0o777)==0o600 for p in first.iterdir())
    with pytest.raises(FileExistsError):
        generation(parent,result['records'],result['receipts'])
    generation(parent,result['records'],result['receipts'],offset=1)
    loaded=news.read_collection_cache(parent)
    assert loaded['records']==result['records'] and len(loaded['attempts'])==1
    assert loaded['sources']['fictional']['etag']=='"v1"'
    assert {p.name:p.read_bytes() for p in first.iterdir()}==before
    assert news.read_cache_generations(parent)==result['records']
    # Restored conditional/backoff state is effective, rather than merely serialized.
    again,requests=collect([],cache=loaded,now=NOW+1)
    assert not requests and again['receipts'][0]['reason']=='poll-not-due'


@pytest.mark.parametrize('field,bad', [('status','fictional-private-marker'),('reason',{'raw':'fictional-private-marker'}),
    ('source_id','account-id-private'),('checked_at_ms',True),('policy_hash','not-a-hash'),
    ('etag','unbounded provider exception'),('next_allowed_at_ms',[]),('body_hash','bad')])
def test_receipt_values_rejected_before_write(tmp_path,field,bad):
    result,_=collect([news.NewsResponse(200,rss())])
    receipt=result['receipts'][0]|{field:bad}
    with pytest.raises(news.NewsError):
        generation(tmp_path/'cache',result['records'],[receipt])
    assert not (tmp_path/'cache').exists()


def test_cache_paths_git_symlink_and_public_parent_rejected(tmp_path):
    with pytest.raises(news.NewsError,match='outside-repository'):
        generation(ROOT/'artifacts'/'fictional-news')
    target=tmp_path/'target';target.mkdir(mode=0o700)
    link=tmp_path/'link';link.symlink_to(target,target_is_directory=True)
    with pytest.raises(news.NewsError,match='unsafe-cache-path'):
        generation(link)
    public=tmp_path/'public';public.mkdir(mode=0o755)
    with pytest.raises(news.NewsError,match='cache-parent-permissions'):
        generation(public)
    assert news.read_cache_generations(tmp_path/'nonexistent')==[]
    assert not (tmp_path/'nonexistent').exists()


@pytest.mark.parametrize('name', ['news.json','receipts.json'])
def test_all_declared_artifact_hashes_verified(tmp_path,name):
    parent=tmp_path/'cache';folder=generation(parent)
    (folder/name).write_bytes(b'{}')
    with pytest.raises(news.NewsError,match='invalid-news-cache'):
        news.read_cache_generations(parent)


def test_cache_declared_size_guard_precedes_payload_read(tmp_path,monkeypatch):
    parent=tmp_path/'cache';folder=generation(parent)
    manifest=json.loads((folder/'manifest.json').read_bytes())
    manifest['artifacts']['news.json']['bytes']=news.MAX_CACHE+1
    (folder/'manifest.json').write_bytes(news.encoded(manifest))
    original=news._bounded_private_read
    calls=[]
    def bounded(path,cap):
        calls.append(path.name)
        return original(path,cap)
    monkeypatch.setattr(news,'_bounded_private_read',bounded)
    with pytest.raises(news.NewsError,match='invalid-news-cache'):
        news.read_cache_generations(parent)
    assert calls==['manifest.json']


def test_cache_read_aggregate_bytes_generation_cap_and_bad_payload(tmp_path,monkeypatch):
    parent=tmp_path/'cache';folder=generation(parent)
    monkeypatch.setattr(news,'MAX_GENERATIONS',1)
    generation(parent,offset=1)
    with pytest.raises(news.NewsError,match='invalid-news-cache'):
        news.read_cache_generations(parent)
    monkeypatch.setattr(news,'MAX_GENERATIONS',32)
    monkeypatch.setattr(news,'MAX_CACHE',100)
    with pytest.raises(news.NewsError,match='invalid-news-cache'):
        news.read_cache_generations(parent)
    monkeypatch.setattr(news,'MAX_CACHE',8*1024*1024)
    rewrite_artifact(folder,'news.json',{'schema_version':1,'records':{}})
    with pytest.raises(news.NewsError,match='invalid-news-cache'):
        news.read_cache_generations(parent)


def test_hash_valid_but_changed_same_revision_rejected(tmp_path):
    parent=tmp_path/'cache';generation(parent)
    folder=generation(parent,offset=1)
    modified=record();modified['relevances'][0]['reason']='changed after original receipt'
    rewrite_artifact(folder,'news.json',{'schema_version':1,'records':[modified]})
    with pytest.raises(news.NewsError,match='invalid-news-cache'):
        news.read_cache_generations(parent)


def test_availability_uses_response_observation_not_request_start():
    times=iter([NOW,NOW,NOW+5000])
    value=news.collect_configured_news([policy()],mode='collect',clock_ms=lambda:next(times),
        transport=lambda request:news.NewsResponse(200,rss()))
    record=value['records'][0]
    assert record['first_seen_at_ms']==record['retrieved_at_ms']==record['ingestion_at_ms']==NOW+5000
    assert value['cache']['sources']['fictional']['attempted_at_ms']==NOW
    assert select(value['records'])['rejected'][0]['reason']=='future-evidence'


@pytest.mark.parametrize('observation,reason', [(NOW-1,'invalid-response-clock'),(NOW+10001,'transport-timeout'),(True,'invalid-response-clock')])
def test_response_clock_rejection_preserves_attempt(observation,reason):
    times=iter([NOW,NOW,observation])
    cache=news.empty_cache()
    value=news.collect_configured_news([policy()],mode='collect',cache=cache,clock_ms=lambda:next(times),
        transport=lambda request:news.NewsResponse(200,rss()))
    assert value['receipts'][0]['reason']==reason and not value['records']
    assert cache['attempts']==[{'source_id':'fictional','at_ms':NOW}]


def test_failed_revised_feed_preserves_all_prior_bytes_and_validators():
    first,_=collect([news.NewsResponse(200,rss(),{'ETag':'"good"'})])
    before=copy.deepcopy(first['records'])
    result,_=collect([news.NewsResponse(200,b'<rss>bad',{'ETag':'"bad"'})],cache=first['cache'],now=NOW+300000)
    assert result['records']==before
    assert result['cache']['sources']['fictional']['etag']=='"good"'
    assert result['receipts'][0]['status']=='rejected'


def test_combined_selector_requires_one_matching_source_policy_per_record():
    a,b=policy('source-a'),policy('source-b')
    value=select([record(a),record(b)],a)
    assert len(value['records'])==1 and value['rejected'][0]['reason']=='source-policy-disabled'
    with pytest.raises(news.NewsError,match='invalid-source-id'):
        select([], [a,a])


def test_actual_article_and_serialized_selection_caps(monkeypatch):
    with pytest.raises(news.NewsError,match='article-budget'):
        select([record()]*(news.MAX_ARTICLES+1))
    value=record()
    # Input fits but expanded output (including policy/coverage/rejections) does not.
    monkeypatch.setattr(news,'MAX_CACHE',len(news.encoded([value]))+1)
    with pytest.raises(news.NewsError,match='selected-cache-budget'):
        select([value])


def test_header_only_rights_never_store_summary():
    p=policy(text_scopes=['headline-only'])
    result,_=collect([news.NewsResponse(200,rss(description='Fictional nonpermitted summary'))],p=p)
    assert result['records'][0]['permitted_text']==''
    assert result['records'][0]['text_scope']=='headline-only'


def test_many_sources_one_call_each_zero_same_run_retry():
    calls=[]
    policies=[policy(f'source-{i}') for i in range(3)]
    def transport(request):
        calls.append(request)
        return news.NewsResponse(503,headers={'Retry-After':'600'})
    value=news.collect_configured_news(policies,mode='collect',transport=transport,clock_ms=lambda:NOW)
    assert len(calls)==3 and len(value['cache']['attempts'])==3
    assert all(r['reason']=='retry-after' for r in value['receipts'])
    assert all(r.timeout_seconds==10 for r in calls)


def test_cache_malformed_receipts_and_symlink_artifacts_fail_closed(tmp_path):
    parent=tmp_path/'cache';folder=generation(parent)
    rewrite_artifact(folder,'receipts.json',[{'source_id':'fictional','status':{'raw':'private'}}])
    with pytest.raises(news.NewsError,match='invalid-news-cache'):
        news.read_cache_generations(parent)
    rewrite_artifact(folder,'receipts.json',[])
    raw=(folder/'news.json').read_bytes()
    (folder/'news.json').unlink()
    target=tmp_path/'raw.json';target.write_bytes(raw);target.chmod(0o600)
    (folder/'news.json').symlink_to(target)
    with pytest.raises(news.NewsError,match='invalid-news-cache'):
        news.read_cache_generations(parent)


def test_read_aggregate_text_enforced_across_generations(tmp_path,monkeypatch):
    parent=tmp_path/'cache'
    generation(parent,records=[record(permitted_text='x'*100)])
    generation(parent,records=[record(canonical_url='https://fictional.example.test/new',permitted_text='x'*100)],offset=1)
    original=news._record_budget
    def strict(records,limits=news.LIMITS):
        return original(records,limits|{'total_text_bytes':200})
    monkeypatch.setattr(news,'_record_budget',strict)
    with pytest.raises(news.NewsError,match='invalid-news-cache'):
        news.read_cache_generations(parent)


def test_three_separate_request_clocks_not_one_run_deadline():
    times=iter([NOW,NOW,NOW+5000,NOW+5000,NOW+10000,NOW+10000,NOW+15000])
    value=news.collect_configured_news([policy(f'source-{i}') for i in range(3)],mode='collect',clock_ms=lambda:next(times),
        transport=lambda request:news.NewsResponse(200,rss()))
    assert [r['first_seen_at_ms'] for r in value['records']]==[NOW+5000,NOW+10000,NOW+15000]
    assert [a['at_ms'] for a in value['cache']['attempts']]==[NOW,NOW+5000,NOW+10000]


def test_clock_exception_message_not_exposed():
    def broken():
        raise RuntimeError('fictional-private-clock-detail')
    with pytest.raises(news.NewsError,match='^invalid-clock$'):
        news.collect_configured_news([policy()],mode='collect',clock_ms=broken)


def test_rejection_fanout_is_bounded(monkeypatch):
    monkeypatch.setattr(news,'MAX_SELECTED',2)
    with pytest.raises(news.NewsError,match='rejection-row-budget'):
        select([record(relevances=[relevance(code=f'US.D{i}',status='unavailable') for i in range(3)])])


@pytest.mark.parametrize('changes',[{'publication_raw':'2027-01-15T07:58:00Z'}, {'publication_timezone':'+0100'}])
def test_original_publication_receipt_must_match_normalized_time(changes):
    with pytest.raises(news.NewsError,match='original-time-mismatch'):
        record(**changes)


def test_same_content_annotation_is_new_envelope_revision_with_as_of_cache_replay(tmp_path):
    # No new text/publication: later reviewed relevance/event evidence gets its own
    # evidence-envelope revision, preserving the unannotated prior information set.
    unannotated=record(event_id='article-only-event',relevances=[])
    annotated=record(event_id='reviewed:event-1',revision_known_at_ms=NOW+100,
                     ingestion_at_ms=NOW+100,dedup_known_at_ms=NOW+100,
                     representative_known_at_ms=NOW+100,relevances=[relevance(known_at_ms=NOW+100)])
    assert unannotated['content_hash']==annotated['content_hash']
    assert unannotated['text_version_id']!=annotated['text_version_id']
    for key in ('publication_at_ms','first_seen_at_ms','age_anchor_at_ms'):
        assert unannotated[key]==annotated[key]
    parent=tmp_path/'cache'
    original=generation(parent,records=[unannotated])
    before=(original/'news.json').read_bytes()
    generation(parent,records=[annotated],offset=1)
    both=news.read_cache_generations(parent)
    early=select(both)
    later=select(both,cutoff=NOW+100)
    assert early['records']==[] and early['coverage']['eligible_article_revisions']==1
    assert any(r['reason']=='future-evidence' for r in early['rejected'])
    assert any(r['reason']=='verified-relevance-unavailable' for r in early['rejected'])
    assert later['records']==[annotated]
    assert (original/'news.json').read_bytes()==before


def test_same_timestamp_annotation_change_is_conflict_not_an_overwrite():
    unannotated=record(relevances=[])
    annotated=record()
    assert unannotated['text_version_id']==annotated['text_version_id']
    with pytest.raises(news.NewsError,match='conflicting-same-time-revision'):
        select([unannotated,annotated])


def test_cache_writer_rejects_conflicting_envelopes_before_creating_generation(tmp_path):
    parent=tmp_path/'cache'
    with pytest.raises(news.NewsError,match='conflicting-same-time-revision'):
        generation(parent,records=[record(relevances=[]),record()])
    assert not parent.exists()
    with pytest.raises(news.NewsError,match='revision-freshness-anchor-changed'):
        generation(parent,records=[record(),record(first_seen_at_ms=NOW-49000)])
    assert not parent.exists()
