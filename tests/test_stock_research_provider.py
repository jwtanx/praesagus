"""Offline fictional REST fixtures. No credentials, Keychain, network or orders."""
import copy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import ssl
import sys
import traceback
from urllib.parse import parse_qs

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/stock-research'))
provider = importlib.import_module('provider')
contracts = importlib.import_module('contracts')
config = importlib.import_module('config')
from connectors.moomoo_rest import ReadRequest, ReadResponse, RESTError
from connectors.moomoo_rest_live import SecureReadTransport, LiveReadError

NOW = int(datetime(2026, 10, 15, tzinfo=timezone.utc).timestamp() * 1000)
BAR_TIME = int(datetime(2026, 10, 14, 4, tzinfo=timezone.utc).timestamp() * 1000)
CLOSE_TIME = BAR_TIME + 16 * 3600000
PRICE = {'simple_property': {'name': 2201}}
SORT = {'direction': 2, **PRICE}


def envelope(data, *, pagination=None, ret_code=0):
    value = {'ret_code': ret_code, 'ret_msg': 'fictional-private-provider-text', 'data': data}
    if pagination is not None:
        value['pagination'] = pagination
    return ReadResponse(200, json.dumps(value).encode())


def screen_row(identity='US.DEMO', value='25000', *, tag=2):
    return {'code': identity, 'name': 'Fictional instrument', 'results': [
        {'simple_property_result': {'property': {'name': 2201},
         'res': {'result_type': tag, {1: 'dval', 2: 'ival', 3: 'sval'}[tag]: value}, 'value': 'untrusted-formatted'}}]}


def screen_page(rows=None, *, more=False, cursor='-1', total=None):
    rows = [screen_row()] if rows is None else rows
    return envelope({'items': rows}, pagination={'total': len(rows) if total is None else total,
                                               'has_more': more, 'next_key': cursor})


def client(responses=(), **settings):
    pending = iter(responses)
    requests, signatures = [], []
    def transport(request):
        requests.append(request)
        return next(pending)
    def sign(value):
        signatures.append(value)
        return b'fictional-signature'
    item = provider.ResearchProvider(api_key='fictional-api-key', signer=sign, transport=transport,
        clock_ms=lambda: NOW, nonce_factory=lambda: 'fixture-nonce',
        config=config.ProviderConfig(**({'screen_limit': 2, 'max_pages': 3} | settings)))
    return item, requests, signatures


def snapshot(**changes):
    return {'code': 'US.DEMO', 'name': 'Fictional', 'update_time': CLOSE_TIME,
            'data_date': '2026-10-14', 'last_price': 25.1, 'volume': 1000, 'turnover': 25100,
            'equity_valid': True, **changes}


def bar(**changes):
    return {'date': 20261014, 'time_key': BAR_TIME, 'time_zone': -240,
            'open': 25.0, 'high': 27.0, 'low': 24.0, 'close': 26.0,
            'volume': 12345, 'turnover': 100000, **changes}


def history_page(rows=None, **changes):
    return envelope({'kline_list': [bar()] if rows is None else rows, 'volume_precision': 2, **changes})


def history(item, **changes):
    return item.history('US.DEMO', start='2026-10-14', end='2026-10-14', **changes)


def screen(item):
    return item.screen(retrieve_queries=[PRICE], sort=SORT)


def assert_private(error):
    rendered = str(error) + repr(error) + ''.join(traceback.format_exception(error))
    assert error.__context__ is None
    for secret in ('fictional-api-key', 'fictional-signature', 'fictional-private-provider-text'):
        assert secret not in rendered


def test_documented_simple_price_fixture_and_exact_signing_bytes():
    item, requests, signed = client([screen_page()])
    batch = screen(item)
    field = batch.rows[0]['fields'][0]
    assert field.value == 25 and field.unit == 'price' and field.raw_value == '25000'
    assert batch.status == 'success' and batch.retrieved_at_ms == NOW
    request = requests[0]
    expected = '\n'.join((str(NOW), 'POST', provider.SCREEN, '', hashlib.sha256(request.body).hexdigest())).encode()
    assert signed == [expected]
    assert json.loads(request.body)['screen_queries'] == [{'simple_field_query': {'simple_field': 1, 'screen_value_list': [2]}}]
    assert 'fictional-api-key' not in repr(request) + repr(item) + repr(batch)


def test_top_level_opaque_cursor_preserves_frozen_query_and_order():
    pages = [screen_page(more=True, cursor='opaque /+==', total=2),
             screen_page([screen_row('US.OTHER')], total=2)]
    item, requests, _ = client(pages)
    result = screen(item)
    first, second = map(lambda request: json.loads(request.body), requests)
    assert second.pop('next_key') == 'opaque /+==' and second == first
    assert [row['code'] for row in result.rows] == ['US.DEMO', 'US.OTHER']
    assert result.pages == 2


@pytest.mark.parametrize('case', ['repeated', 'empty', 'duplicate', 'oversized', 'nested-pagination', 'changed-total'])
def test_screen_page_failures_are_visible_and_bounded(case):
    first = screen_page(more=True, cursor='cursor', total=2)
    second = screen_page([screen_row('US.OTHER')], more=True, cursor='cursor', total=2)
    if case == 'empty':
        first = screen_page([], more=True, cursor='cursor', total=2)
    elif case == 'duplicate':
        second = screen_page([screen_row()], total=2)
    elif case == 'oversized':
        first = screen_page([screen_row('US.A'), screen_row('US.B'), screen_row('US.C')])
    elif case == 'nested-pagination':
        value = json.loads(first.body);value['data']['pagination'] = value.pop('pagination')
        first = ReadResponse(200, json.dumps(value).encode())
    elif case == 'changed-total':
        second = screen_page([screen_row('US.OTHER')], total=3)
    item, requests, _ = client([first, second])
    with pytest.raises(RESTError) as caught:
        screen(item)
    assert len(requests) <= 2
    assert_private(caught.value)


def test_screen_exhaustion_and_page_cap_never_claim_complete_coverage():
    item, _, _ = client([screen_page(total=2)])
    assert screen(item).reason == 'reported-total-incomplete'
    item, requests, _ = client([screen_page(more=True, cursor='next', total=2)], max_pages=1)
    batch = screen(item)
    assert batch.status == 'truncated' and batch.reason == 'page-budget' and len(requests) == 1


@pytest.mark.parametrize('mutation', ['missing', 'descriptor', 'order', 'bool', 'decimal', 'formatted-only', 'wrong-type'])
def test_screen_typed_value_missingness_and_rejections(mutation):
    row = screen_row()
    wrapper = row['results'][0]['simple_property_result']
    if mutation in ('missing', 'formatted-only'):
        wrapper['res'].pop('ival')
    elif mutation == 'descriptor':
        wrapper['property']['name'] = 2301
    elif mutation == 'order':
        row['results'].append(copy.deepcopy(row['results'][0]))
    elif mutation == 'bool':
        wrapper['res']['ival'] = True
    elif mutation == 'decimal':
        wrapper['res']['ival'] = '25,000'
    elif mutation == 'wrong-type':
        wrapper['res'] = {'sval': '25000', 'result_type': 3}
    item, _, _ = client([screen_page([row])])
    if mutation in ('missing', 'formatted-only'):
        field = screen(item).rows[0]['fields'][0]
        assert field.value is None and field.reason == 'typed-value-missing'
    else:
        with pytest.raises(RESTError):
            screen(item)


def test_known_simple_scaling_and_unknown_string_factor():
    wrapper = screen_row()['results'][0]
    wrapper['simple_property_result']['property']['name'] = 2301
    result = contracts.screen_field(wrapper, {'simple_property': {'name': 2301}})
    assert result.value == 25 and result.unit == 'market_cap'
    text_wrapper = screen_row(value='Fictional sector text', tag=3)['results'][0]
    text_wrapper['simple_property_result']['property']['name'] = 9999
    result = contracts.screen_field(text_wrapper, {'simple_property': {'name': 9999}})
    assert result.value is None and result.raw_value == 'Fictional sector text'
    assert result.reason == 'factor-unit-unverified'


@pytest.mark.parametrize('factor', [3102, 3104, 3105])
def test_cumulative_factors_cannot_be_requested_or_scaled_as_simple_fields(factor):
    wrapper = screen_row()['results'][0]
    wrapper['simple_property_result']['property']['name'] = factor
    with pytest.raises(RESTError, match='factor-family-mismatch'):
        contracts.screen_field(wrapper, {'simple_property': {'name': factor}})
    item, requests, signed = client()
    with pytest.raises(RESTError, match='factor-family-mismatch'):
        item.screen(retrieve_queries=[{'simple_property': {'name': factor}}], sort=SORT)
    assert not requests and not signed


def test_reviewed_cumulative_request_does_not_assume_unknown_response_shape():
    query = {'cumulative_property': {'name': 3105, 'days': 20, 'period_average': True}}
    row = screen_row();row['results'] = [{'unverified_provider_wrapper': {'value': '999999'}}]
    item, requests, _ = client([screen_page([row])])
    batch = item.screen(retrieve_queries=[query], sort={'direction': 2, **query})
    assert json.loads(requests[0].body)['retrieve_queries'] == [query]
    field = batch.rows[0]['fields'][0]
    assert field.value is None and field.raw_value is None and field.unit == 'average_turnover'
    assert field.reason == 'cumulative-response-shape-unverified'


@pytest.mark.parametrize('codes', [[], ['US.DEMO', 'US.DEMO'], ['HK.TEST'], ['US.DEMO/../../accounts'], ['US.A'] * 401])
def test_code_requests_reject_before_signing_or_transport(codes):
    item, requests, signed = client()
    with pytest.raises(RESTError):
        item.snapshots(codes)
    assert not requests and not signed


def test_basic_partial_identity_is_not_etf_strategy_or_fundamental_period():
    row = {'code': 'US.DEMO', 'name': 'Fictional trust', 'stock_type': 'ETF', 'exchange': 'NYSE',
           'suspension': False, 'listing_date': BAR_TIME, 'stock_id': '12345'}
    item, _, _ = client([envelope({'basic_list': [row]})])
    result = item.basicinfo(['US.DEMO', 'US.OTHER'])
    assert result.status == 'partial' and result.missing_codes == ('US.OTHER',)
    assert result.rows[0]['sector'] is None and result.rows[0]['fundamental_period'] is None
    assert 'signed_leverage' not in result.rows[0]
    assert result.rows[0]['stock_id'] == '12345'


@pytest.mark.parametrize('rows', [[snapshot(code='US.OTHER')], [snapshot(), snapshot()]])
def test_unrequested_or_duplicate_snapshot_rejected(rows):
    item, _, _ = client([envelope({'snapshot_list': rows})])
    with pytest.raises(RESTError):
        item.snapshots(['US.DEMO'])


def test_snapshot_units_and_native_counts_stay_separate_from_patterns():
    item, _, _ = client([envelope({'snapshot_list': [snapshot(native_bullish_count=42, change_rate=5)]})])
    result = item.snapshots(['US.DEMO']).rows[0]
    assert result['last_price'] == 25.1 and result['turnover'] == 25100
    assert result['currency'] is None and result['native_bullish_count'] is None
    assert result['native_bearish_count'] is None and result['source_at_ms'] == CLOSE_TIME
    assert result['observation_kind'] == 'live-snapshot-not-completed-bar'


@pytest.mark.parametrize('change', [{'update_time': NOW + 1}, {'last_price': True}, {'last_price': -1},
                                  {'volume': float('nan')}, {'equity_valid': 1}, {'data_date': '2026-11-01'}])
def test_snapshot_future_malformed_and_invalid_flags(change):
    item, _, _ = client([envelope({'snapshot_list': [snapshot(**change)]})])
    if 'last_price' in change:
        batch=item.snapshots(['US.DEMO'])
        assert batch.status=='partial' and not batch.rows
        assert batch.metadata['rejected_row_count']==1 and batch.reason=='snapshot-rows-rejected'
        return
    with pytest.raises(RESTError):
        item.snapshots(['US.DEMO'])


@pytest.mark.parametrize('field',['open_price','high_price','low_price','last_price','prev_close_price'])
@pytest.mark.parametrize('bad',[0,-1,True,'invalid'])
def test_numeric_snapshot_row_quarantine_keeps_healthy_and_absent_distinct(field,bad):
    rows=[snapshot(code='US.GOOD'),snapshot(code='US.BAD',**{field:bad})]
    item,requests,signatures=client([envelope({'snapshot_list':rows})])
    batch=item.snapshots(['US.GOOD','US.BAD','US.ABSENT'])
    assert [r['code'] for r in batch.rows]==['US.GOOD'] and batch.missing_codes==('US.ABSENT',)
    assert batch.status=='partial' and batch.reason=='snapshot-rows-rejected'
    meta=batch.metadata
    assert (meta['raw_rows_received'],meta['accepted_rows'],meta['rejected_row_count'],meta['missing_row_count'])==(2,1,1,1)
    evidence=meta['rejected_rows'][0]
    assert set(evidence)=={'code','ordinal','reason','source','source_payload_hash','row_sha256','requested_at_ms','retrieved_at_ms','known_at_ms'}
    assert evidence['code']=='US.BAD' and evidence['ordinal']==1 and evidence['reason']=='invalid-numeric-field'
    assert evidence['source_payload_hash']==batch.rows[0]['revision_vintage'] and evidence['known_at_ms']==NOW
    assert evidence['row_sha256']==hashlib.sha256(json.dumps(rows[1],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert len(requests)==len(signatures)==1 and item.budgets['rows_used']==2


@pytest.mark.parametrize('fatal',[{'suspension':1},{'equity_valid':'yes'},{'trust_valid':None},
    {'update_time':NOW+1},{'data_date':'2026-11-01'}])
def test_bad_numeric_row_cannot_hide_same_row_non_numeric_fatal_error(fatal):
    item,_,_=client([envelope({'snapshot_list':[snapshot(open_price=0,**fatal)]})])
    with pytest.raises(RESTError):item.snapshots(['US.DEMO'])


@pytest.mark.parametrize('later',[snapshot(code='US.BAD'),snapshot(code='US.UNREQUESTED')])
def test_bad_numeric_row_cannot_hide_later_identity_failure(later):
    item,_,_=client([envelope({'snapshot_list':[snapshot(code='US.BAD',open_price=0),later]})])
    with pytest.raises(RESTError,match='unrequested-or-duplicate-code'):item.snapshots(['US.BAD','US.GOOD'])


def test_all_rejected_vs_absent_and_rejection_byte_limit(monkeypatch):
    item,_,_=client([envelope({'snapshot_list':[snapshot(open_price=0,high_price=0)]})])
    batch=item.snapshots(['US.DEMO'])
    assert not batch.rows and not batch.missing_codes and batch.metadata['rejected_row_count']==1
    item,_,_=client([envelope({'snapshot_list':[]})]);batch=item.snapshots(['US.DEMO'])
    assert batch.missing_codes==('US.DEMO',) and batch.metadata['rejected_row_count']==0
    monkeypatch.setattr(provider,'MAX_SNAPSHOT_REJECTION_BYTES',2)
    item,_,_=client([envelope({'snapshot_list':[snapshot(open_price=0)]})])
    with pytest.raises(RESTError,match='snapshot-rejection-budget'):item.snapshots(['US.DEMO'])


def test_full300_rows_count_rejections_once_and_accept_missing_optional_signed_values():
    rows=[snapshot(code='US.F'+str(i),open_price=0 if i%50==0 else None,pe_ratio=-3) for i in range(300)]
    item,_,_=client([envelope({'snapshot_list':rows})],max_rows=300)
    batch=item.snapshots([r['code'] for r in rows])
    assert len(batch.rows)==294 and batch.metadata['raw_rows_received']==300 and batch.metadata['rejected_row_count']==6
    assert all(r['financial_metrics']['pe_ratio']['value']==-3 for r in batch.rows)


@pytest.mark.parametrize('position',[0,1,2])
def test_snapshot_bad_row_position_does_not_change_healthy_rows(position):
    rows=[snapshot(code='US.F'+str(i)) for i in range(3)];rows[position]['high_price']=0
    item,_,_=client([envelope({'snapshot_list':rows})]);batch=item.snapshots([r['code'] for r in rows])
    assert [r['code'] for r in batch.rows]==[r['code'] for i,r in enumerate(rows) if i!=position]
    assert batch.metadata['rejected_rows'][0]['ordinal']==position


def test_snapshot_bad_numeric_does_not_hide_later_fatal_source_error():
    item,_,_=client([envelope({'snapshot_list':[snapshot(code='US.BAD',open_price=0),snapshot(code='US.LATER',update_time=NOW+1)]})])
    with pytest.raises(RESTError,match='invalid-source-time'):item.snapshots(['US.BAD','US.LATER'])


def test_complete_ohlc_raw_timezone_provenance_and_explicit_currency_calendar():
    evidence = contracts.CurrencyEvidence('US.DEMO', 'USD', 'https://example.org/fictional-currency', NOW - 1)
    item, requests, _ = client([history_page()])
    result = history(item, currency_evidence=evidence, session_closes={'2026-10-14': CLOSE_TIME})
    row = result.rows[0]
    assert row['volume'] == 123.45 and row['turnover'] == 100000
    assert row['time_zone_unit_status'] == 'documented-minutes/runtime-unverified'
    assert row['provider_finality_status'] == 'unverified'
    assert row['raw_time_zone'] == -240 and row['raw_time_key'] == BAR_TIME and row['session_date'] == '2026-10-14'
    assert row['currency'] == 'USD' and row['completed'] and row['known_at_ms'] == NOW
    assert row['adjustment'] == 'forward-excluding-dividends' and len(row['revision_vintage']) == 64
    assert parse_qs(requests[0].query)['ktype'] == ['2']
    coverage = contracts.history_coverage(result.rows, expected_sessions=['2026-10-14'], cutoff_ms=NOW, minimum=1)
    assert coverage['status'] == 'complete'
    assert contracts.history_coverage(result.rows, expected_sessions=['2026-10-14'], cutoff_ms=NOW)['status'] == 'insufficient'


def test_history_without_currency_or_calendar_never_claims_training_ready():
    item, _, _ = client([history_page()])
    rows = history(item).rows
    assert rows[0]['currency'] is None and rows[0]['completion_status'] == 'calendar-unverified'
    assert contracts.history_coverage(rows, expected_sessions=None, cutoff_ms=NOW)['status'] == 'unverified'
    assert contracts.history_coverage(rows, expected_sessions=['2026-10-14'], cutoff_ms=NOW, minimum=1)['status'] == 'insufficient'


@pytest.mark.parametrize('change', [{'open': None}, {'high': 23}, {'low': 28}, {'close': 0}, {'volume': -1},
    {'turnover': True}, {'date': 20260230}, {'time_zone': -300}, {'time_key': NOW + 1}, {'time_key': True}])
def test_invalid_or_inconsistent_ohlc_dates_units_and_future_times_rejected(change):
    item, _, _ = client([history_page([bar(**change)])])
    with pytest.raises(RESTError):
        history(item)


def test_history_duplicate_dates_missing_precision_and_unknown_next_time():
    item, _, _ = client([history_page([bar(), bar()])])
    with pytest.raises(RESTError, match='duplicate-history-date'):
        history(item)
    item, _, _ = client([history_page(volume_precision=None)])
    with pytest.raises(RESTError, match='volume-unit-unverified'):
        history(item)
    item, requests, _ = client([history_page(next_time=BAR_TIME)])
    result = history(item)
    assert result.status == 'success'
    assert result.metadata['next_time_status'] == 'unverified-not-used'
    assert result.metadata['windows'][0]['next_time_raw'] == BAR_TIME and len(requests) == 1


def test_bounded_date_backfill_never_reinterprets_millisecond_cursor_as_date():
    item, requests, _ = client([history_page([]), history_page([])], history_window_days=1, max_pages=2)
    result = item.history('US.DEMO', start='2026-10-12', end='2026-10-14')
    assert result.status == 'truncated' and result.reason == 'page-budget'
    assert [parse_qs(request.query)['end'][0] for request in requests] == ['2026-10-14', '2026-10-13']
    assert [parse_qs(request.query)['start'][0] for request in requests] == ['2026-10-14', '2026-10-13']


def test_global_request_row_and_concurrent_caps():
    item, requests, _ = client([screen_page()], max_requests=1)
    screen(item)
    with pytest.raises(RESTError, match='request-budget'):
        screen(item)
    assert len(requests) == 1
    item, _, _ = client([screen_page([screen_row('US.A'), screen_row('US.B')])], max_rows=1)
    with pytest.raises(RESTError, match='row-budget'):
        screen(item)
    item, requests, _ = client()
    item._lock.acquire()
    try:
        with pytest.raises(RESTError, match='concurrent-request-forbidden'):
            screen(item)
    finally:
        item._lock.release()
    assert not requests


@pytest.mark.parametrize('response,kind', [
    (ReadResponse(429, b'fictional-private-provider-text', {'Retry-After': '7'}), 'rate-limited'),
    (ReadResponse(503, b'fictional-private-provider-text'), 'upstream-failed'),
    (ReadResponse(302, b'fictional-private-provider-text'), 'http-failed'),
    (ReadResponse(200, b'{"data":0,"data":1}'), 'malformed-response'),
    (envelope({}, ret_code=5), 'provider-failed')])
def test_errors_sanitized_without_automatic_retry(response, kind):
    item, requests, _ = client([response])
    with pytest.raises(RESTError) as caught:
        screen(item)
    assert caught.value.kind == kind and len(requests) == 1
    assert_private(caught.value)
    if kind == 'rate-limited':
        assert caught.value.retry_after == 7
        with pytest.raises(RESTError, match='provider-stopped'):
            screen(item)
        assert len(requests) == 1


def test_dependency_exception_and_credentials_do_not_escape_context():
    item, requests, _ = client()
    def fail(_):
        raise RuntimeError('fictional-api-key fictional-private-provider-text')
    item._transport = fail
    with pytest.raises(RESTError) as caught:
        screen(item)
    assert_private(caught.value)
    with pytest.raises(RESTError, match='live-not-authorized'):
        provider.build_live_provider({}, clock_ms=lambda: NOW, nonce_factory=lambda: 'fixture', credential_loader=fail)


def test_explicit_live_factory_reuses_injected_credentials_without_actual_access():
    calls = []
    def load(locator):
        calls.append(locator)
        return 'fictional-api-key', lambda _: b'fictional-signature'
    item = provider.build_live_provider({'fictional': True}, clock_ms=lambda: NOW, nonce_factory=lambda: 'fixture',
        allow_live=True, credential_loader=load, transport=lambda _: screen_page())
    assert calls == [{'fictional': True}] and screen(item).status == 'success'


HEADERS = {'X-Api-Key': 'fictional-api-key', 'Authorization': 'fictional-signature',
           'X-Timestamp': str(NOW), 'X-Nonce': 'fixture', 'Content-Type': 'application/json'}


@pytest.mark.parametrize('path,method', [('/api/v1.0/accounts/1/funds', 'GET'),
    ('https://example.org/api/v1.0/quote/stock-screen', 'POST'), ('/api/v1.0/trade/orders', 'POST'),
    ('/api/v1.0/quote/find-news', 'GET'), ('/api/v1.0/quote/HK.TEST/history-kline', 'GET')])
def test_standalone_allowlist_rejects_accounts_orders_arbitrary_host_and_other_routes(path, method):
    item, requests, signed = client()
    with pytest.raises(RESTError, match='endpoint-forbidden'):
        item._read(method, path)
    assert not requests and not signed
    with pytest.raises(LiveReadError):
        provider.ResearchReadTransport._validate(ReadRequest(method, path, '', b'{}', HEADERS, 5))


def test_old_allowlist_unchanged_and_new_transport_reuses_tls_no_redirect_guards():
    request = ReadRequest('POST', provider.SCREEN, '', b'{}', HEADERS, 5)
    with pytest.raises(LiveReadError):
        SecureReadTransport._validate(request)
    assert provider.ResearchReadTransport._validate(request) == HEADERS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    transport = provider.ResearchReadTransport(context_factory=lambda: context)
    with pytest.raises(LiveReadError, match='tls-required'):
        transport(request)


def test_issuer_registry_classifies_only_discovered_names_and_never_claims_listing():
    result = provider.classify_discovered_etfs(['US.SOXL', 'US.IBB', 'US.UNLISTED'])
    assert set(result) == {'US.SOXL', 'US.IBB', 'US.UNLISTED'}
    assert result['US.SOXL']['signed_leverage'] == '3' and result['US.SOXL']['reset'] == 'daily'
    assert result['US.SOXL']['listing_verified'] is False and not result['US.SOXL']['selection_eligible']
    assert result['US.IBB']['benchmark_name'] == 'NYSE Biotechnology Index'
    assert result['US.UNLISTED']['signed_leverage'] is None
    assert provider.classify_discovered_etfs([]) == {}


def test_config_example_and_capability_unknowns():
    loaded = config.load_config(ROOT / 'scripts/stock-research/config.example.toml')
    assert loaded == config.ProviderConfig()
    with pytest.raises(ValueError):
        config.ProviderConfig(max_requests=True)
    with pytest.raises(ValueError):
        config.ProviderConfig(timeout_seconds=float('inf'))
    capabilities = provider.ResearchProvider.capabilities()
    assert capabilities['rest_numeric_quota'] is None and capabilities['native_bullish_count'] is None
    assert capabilities['entitlements'] == 'unverified'


@pytest.mark.parametrize('stock_id', [True, '', 'issuer-123', -1, 1.5, '0', str(2**63)])
def test_malformed_internal_security_id_rejected(stock_id):
    row = {'code': 'US.DEMO', 'name': 'Fictional', 'stock_id': stock_id}
    item, _, _ = client([envelope({'basic_list': [row]})])
    with pytest.raises(RESTError, match='invalid-security-id'):
        item.basicinfo(['US.DEMO'])


def test_safe_history_backfill_uses_actual_oldest_date_and_detects_calendar_holes():
    prior = bar(date=20261013, time_key=BAR_TIME - 86400000)
    item, requests, _ = client([history_page(next_time=123), history_page([prior], next_time=999), history_page([])])
    evidence = contracts.CurrencyEvidence('US.DEMO', 'USD', 'https://example.org/fictional-currency', NOW - 1)
    result = item.history('US.DEMO', start='2026-10-12', end='2026-10-14', currency_evidence=evidence,
        session_closes={'2026-10-14': CLOSE_TIME, '2026-10-13': CLOSE_TIME - 86400000})
    assert [parse_qs(request.query)['end'][0] for request in requests] == ['2026-10-14', '2026-10-13', '2026-10-12']
    assert [row['session_date'] for row in result.rows] == ['2026-10-13', '2026-10-14']
    assert [window['next_time_raw'] for window in result.metadata['windows']][:2] == [123, 999]
    coverage = contracts.history_coverage(result.rows, expected_sessions=['2026-10-12', '2026-10-13', '2026-10-14'],
                                          cutoff_ms=NOW, minimum=1)
    assert coverage['status'] == 'insufficient' and coverage['missing_sessions'] == ['2026-10-12']


def test_bounded_three_year_date_bootstrap_progresses_with_nonterminal_next_time():
    item, requests, _ = client([history_page([], next_time=123)] * 7, max_pages=7)
    result = item.history('US.DEMO', start='2023-10-15', end='2026-10-14')
    assert result.status == 'empty' and len(requests) == 7
    ranges = [parse_qs(request.query) for request in requests]
    for first, second in zip(ranges, ranges[1:]):
        assert second['end'][0] < first['start'][0]
    assert all(window['next_time_raw'] == 123 for window in result.metadata['windows'])
    assert result.metadata['coverage'] == 'requires-actual-calendar-evidence'


def test_global_history_timestamp_duplicates_rejected_across_backfill_pages():
    stamp = BAR_TIME + 19 * 3600000
    first = bar(date=20261015, time_key=stamp, time_zone=120)
    second = bar(date=20261014, time_key=stamp, time_zone=-240)
    item, _, _ = client([history_page([first]), history_page([second])])
    with pytest.raises(RESTError, match='duplicate-history-date'):
        item.history('US.DEMO', start='2026-10-14', end='2026-10-15')


def test_raw_timezone_minus_four_is_never_silently_multiplied_by_sixty():
    item, _, _ = client([history_page([bar(time_zone=-4)])])
    result = history(item).rows[0]
    assert result['raw_time_zone'] == -4
    assert result['time_zone_unit_status'] == 'documented-minutes/runtime-unverified'
    assert result['provider_finality_status'] == 'unverified'


def test_default_is_small_bounded_and_explicit_large_override_validates():
    assert config.ProviderConfig().max_requests == 128
    assert config.ProviderConfig(max_requests=2048).max_requests == 2048
    with pytest.raises(ValueError):
        config.ProviderConfig(max_requests=2049)


def test_daily_change_rate_discovery_request_sort_keeps_numeric_rate_unavailable():
    query = {'cumulative_property': {'name': 3102, 'days': 1, 'period_average': False}}
    row = screen_row();row['results'] = [{'unknown_rate_wrapper': {'ival': '5000'}}]
    item, requests, _ = client([screen_page([row])])
    batch = item.screen(retrieve_queries=[query], sort={'direction': 2, **query})
    sent = json.loads(requests[0].body)
    assert sent['retrieve_queries'] == [query] and sent['sort'] == {'direction': 2, **query}
    result = batch.rows[0]['fields'][0]
    assert result.value is None and result.raw_value is None and result.unit is None
    assert result.reason == 'cumulative-response-shape-unverified'
    for properties in [{'name': 3102, 'days': 20, 'period_average': False},
                       {'name': 3102, 'days': 1, 'period_average': True}]:
        with pytest.raises(RESTError, match='unsupported-change-rate-window'):
            contracts.descriptor({'cumulative_property': properties})
    with pytest.raises(RESTError, match='factor-family-mismatch'):
        contracts.descriptor({'simple_property': {'name': 3102}})


def cumulative_row(factor=3105, *, days=1, flag=0, value='25000'):
    return {'code':'US.DEMO','name':'Fictional','results':[{'cumulative_property_result':{
        'property':{'name':factor,'days':days,'period_average':flag},'res':{'result_type':2,'ival':value}}}]}


def test_live_reviewed_cumulative_wrapper_exact_integer_echo_and_units():
    for factor,expected,unit in [(3104,25000,'volume'),(3105,25,'turnover'),(3102,None,None)]:
        query={'cumulative_property':{'name':factor,'days':1,'period_average':False}}
        item,_,_=client([screen_page([cumulative_row(factor,value='-3159' if factor==3102 else '25000')])])
        field=item.screen(retrieve_queries=[query],sort={'direction':2,**query}).rows[0]['fields'][0]
        assert field.value==expected and field.unit==unit
        if factor==3102:assert field.reason=='change-rate-base-unit-unverified'


@pytest.mark.parametrize('flag,days,factor',[(True,1,3105),(2,1,3105),(1,1,3105),(0,2,3105),(0,1,3104)])
def test_cumulative_echo_rejects_bool_alternative_integer_wrong_window_or_factor(flag,days,factor):
    query={'cumulative_property':{'name':3105,'days':1,'period_average':False}}
    item,_,_=client([screen_page([cumulative_row(factor,days=days,flag=flag)])])
    with pytest.raises(RESTError,match='descriptor-mismatch'):
        item.screen(retrieve_queries=[query],sort={'direction':2,**query})


def test_signed_fundamentals_have_equity_guard_and_explicit_period_currency():
    row=snapshot(earning_per_share=-2.5,net_profit=-1000,pe_ratio=-4,dividend_ratio_ttm=3.0)
    item,_,_=client([envelope({'snapshot_list':[row]})])
    metrics=item.snapshots(['US.DEMO']).rows[0]['financial_metrics']
    assert metrics['earning_per_share']['value']==-2.5 and metrics['net_profit']['value']==-1000
    assert metrics['earning_per_share']['period']=='previous-fiscal-year/end-unknown'
    assert metrics['earning_per_share']['currency'] is None and metrics['pe_ratio']['unit']=='ratio'
    assert metrics['dividend_ratio_ttm']['unit']=='percentage-points'
    row['equity_valid']=False
    item,_,_=client([envelope({'snapshot_list':[row]})])
    assert item.snapshots(['US.DEMO']).rows[0]['financial_metrics']['net_profit']['value'] is None


def test_closed_metadata_routes_and_raw_taxonomy_no_sector_inference():
    owner={'plate_code':'US.INDUSTRY1','plate_name':'Fictional industry','plate_type':'INDUSTRY','name':'Company name differs'}
    profile={'name':'Industry label','value':'Fictional industry','field_type':0,'attribute_type':50}
    plate={'code':'US.INDUSTRY1','plate_id':'INDUSTRY1','plate_name':'Fictional industry'}
    item,requests,_=client([envelope({'sectors':[owner]}),envelope({'items':[profile]}),envelope({'plate_list':[plate]})])
    assert item.source_metadata('US.DEMO','owner-plate').rows[0]['plate_name']=='Fictional industry'
    assert item.source_metadata('US.DEMO','company/profile').rows[0]['attribute_type']==50
    catalog=item.industry_catalog()
    assert catalog.metadata['taxonomy_id']=='moomoo-rest-US-INDUSTRY' and 'sector_id' not in catalog.rows[0]
    assert requests[-1].query=='market=US&plate_class=INDUSTRY'
    assert all(request.method=='GET' and not request.body for request in requests)
    for request in requests:
        with pytest.raises(LiveReadError):SecureReadTransport._validate(request)
        with pytest.raises(LiveReadError):provider.ResearchReadTransport._validate(replace(request,query='market=HK&plate_class=INDUSTRY'))


def test_raw_mode_is_explicit_not_split_continuous_and_empty_metadata_valid():
    item,_,_=client([history_page(),envelope({'sectors':[]})],autype=0)
    assert history(item).rows[0]['adjustment']=='unadjusted'
    assert item.source_metadata('US.DEMO','owner-plate').status=='empty'


def owner_plate(plate_type='INDUSTRY', **changes):
    return {'plate_code':'US.FICTIONAL','plate_name':'Fictional industry',
            'plate_type':plate_type,'name':'Fictional queried company',**changes}


def test_owner_plate_mixed_types_preserve_rows_and_current_source_provenance():
    # Authored public-shape regression, not copied provider rows: 38 supported + 2 SPECIAL.
    rows=[owner_plate(('INDUSTRY','CONCEPT','OTHER')[i % 3],plate_code=f'US.FICTION{i}') for i in range(38)]
    rows.extend([owner_plate('SPECIAL',plate_code='US.EXTRA1'),owner_plate('SPECIAL',plate_code='US.EXTRA2')])
    response=envelope({'sectors':rows})
    item,requests,_=client([response],max_requests=1)
    batch=item.source_metadata('US.DEMO','owner-plate')
    assert batch.status=='partial' and batch.reason=='unsupported-plate-types' and batch.pages==1
    assert len(batch.rows)==40 and len(requests)==1 and item.budgets['rows_used']==40
    assert [row['plate_type'] for row in batch.rows]==[row['plate_type'] for row in rows]
    assert [row['plate_code'] for row in batch.rows]==[row['plate_code'] for row in rows]
    assert [row['plate_type_status'] for row in batch.rows]==['supported']*38+['unsupported']*2
    assert all(row['plate_name']=='Fictional industry' and row['name']=='Fictional queried company' for row in batch.rows)
    assert batch.requested_at_ms==batch.retrieved_at_ms==NOW
    assert batch.metadata=={'code':'US.DEMO','raw_payload_hash':hashlib.sha256(response.body).hexdigest(),
        'known_at_ms':NOW,'effective_from':None,'effective_to':None,'classification':'raw-current-only',
        'unsupported_type_counts':{'SPECIAL':2},'unsupported_type_rows':2}
    assert all('sector_id' not in row and 'issuer_group_id' not in row for row in batch.rows)
    assert requests[0].method=='GET' and requests[0].path=='/api/v1.0/quote/US.DEMO/owner-plate'
    assert requests[0].query=='' and requests[0].body==b''


@pytest.mark.parametrize('types,status,counts',[
    (['INDUSTRY','CONCEPT','OTHER'],'success',{}),
    (['FutureType','SPECIAL','FutureType','REGION'],'partial',{'FutureType':2,'REGION':1,'SPECIAL':1}),
    ([], 'empty',{}),
])
def test_owner_plate_supported_unknown_only_and_empty_statuses(types,status,counts):
    item,requests,_=client([envelope({'sectors':[owner_plate(value) for value in types]})])
    batch=item.source_metadata('US.DEMO','owner-plate')
    assert batch.status==status and batch.reason==('unsupported-plate-types' if counts else None)
    assert batch.metadata['unsupported_type_counts']==counts
    assert list(batch.metadata['unsupported_type_counts'])==sorted(counts)
    assert batch.metadata['unsupported_type_rows']==sum(counts.values())
    assert [row['plate_type'] for row in batch.rows]==types and len(requests)==1


def test_owner_plate_unknown_diagnostics_are_bounded_by_row_and_type_limits():
    types=[f'{i:03}'+('X'*125) for i in range(400)]
    rows=[owner_plate(value,plate_code='C'*512,plate_name='N'*512) for value in types]
    item,_,_=client([envelope({'sectors':rows})])
    batch=item.source_metadata('US.DEMO','owner-plate')
    assert batch.status=='partial' and len(batch.rows)==400
    assert all(len(row['plate_type'])==128 and row['plate_type_status']=='unsupported' for row in batch.rows)
    assert batch.metadata['unsupported_type_rows']==400
    assert batch.metadata['unsupported_type_counts']=={value:1 for value in types}
    assert len(json.dumps(batch.metadata).encode())<65536


@pytest.mark.parametrize('bad',[0,1.5,True,False,None,'','\n','TYPE\x7f','TYPE\ud800','X'*129,{},[],'missing'])
def test_owner_plate_malformed_type_is_not_coerced_or_retained(bad):
    row=owner_plate(bad)
    if bad=='missing':row.pop('plate_type')
    item,requests,_=client([envelope({'sectors':[owner_plate(),row]})])
    with pytest.raises(RESTError,match='invalid-industry-record') as error:
        item.source_metadata('US.DEMO','owner-plate')
    assert_private(error.value)
    assert len(requests)==1


@pytest.mark.parametrize('field',['plate_code','plate_name'])
@pytest.mark.parametrize('bad',[None,False,'','\n','X'*513,'missing'])
def test_owner_plate_structural_code_and_label_remain_strict(field,bad):
    row=owner_plate('SPECIAL',**{field:bad})
    if bad=='missing':row.pop(field)
    # The queried-company name is deliberately present; it is never a plate-name fallback.
    item,_,_=client([envelope({'sectors':[row]})])
    with pytest.raises(RESTError,match='invalid-industry-record'):
        item.source_metadata('US.DEMO','owner-plate')


@pytest.mark.parametrize('data,expected',[
    ({'sectors':[owner_plate()]*401},'invalid-page'),
    ({'sectors':['not-a-record']},'invalid-page'),
    ({'sectors':{}},'invalid-page'),
    ({},'invalid-page'),
    ([], 'malformed-response'),
])
def test_owner_plate_bad_list_shape_and_row_budget_remain_rejected(data,expected):
    item,requests,_=client([envelope(data)])
    with pytest.raises(RESTError,match=expected):item.source_metadata('US.DEMO','owner-plate')
    assert len(requests)==1


@pytest.mark.parametrize('plate_type',['SPECIAL','FutureType','REGION','CONCEPT','OTHER'])
def test_owner_plate_non_industry_cannot_enter_reviewed_sector_resolution(plate_type):
    universe=importlib.import_module('universe')
    item,_,_=client([envelope({'sectors':[owner_plate(plate_type),owner_plate('INDUSTRY')]})])
    batch=item.source_metadata('US.DEMO','owner-plate')
    reviewed={'status':'verified','known_at_ms':NOW,'source_url':'https://example.test/fictional',
              'source_hash':batch.metadata['raw_payload_hash'],'reviewer':'fictional-reviewer'}
    evidence=reviewed|{'market':'US','taxonomy_id':'fictional-taxonomy','taxonomy_snapshot_hash':'a'*64,
                       'industry_records':list(batch.rows[:1])}
    mapping=reviewed|{'market':'US','vendor_taxonomy_id':'fictional-taxonomy',
        'vendor_taxonomy_snapshot_hash':'a'*64,'industry_code':'US.FICTIONAL','sector_id':'fictional-sector',
        'target_sector_taxonomy_id':'fictional-target','target_taxonomy_version':'v1','mapping_version':'v1'}
    result=universe.resolve_sector(evidence,[mapping],NOW)
    assert result=={'sector_id':None,'sector_mapping_status':'unmapped','reason':'no-industry-membership'}
    # Exact INDUSTRY still resolves with reviewed evidence, even beside unsupported rows.
    result=universe.resolve_sector(evidence|{'industry_records':list(batch.rows)},[mapping],NOW)
    assert result['sector_id']=='fictional-sector' and result['sector_mapping_status']=='verified'


def test_history_keeps_prior_pages_when_global_request_budget_stops_backfill():
    item,requests,_=client([history_page()],max_requests=1,history_window_days=1)
    result=item.history('US.DEMO',start='2026-10-13',end='2026-10-14')
    assert result.status=='partial' and result.reason=='request-budget' and len(result.rows)==1
    assert result.metadata['stopped_on_failure'] is True and len(requests)==1


@pytest.mark.parametrize('value,tag', [('0',2),('-1',2),(0.0,1),(-1.0,1)])
def test_nonpositive_price_stays_strict_but_only_its_instrument_is_excluded(value,tag):
    bad=screen_row('US.ZERO',value,tag=tag)
    with pytest.raises(contracts.NonpositiveScreenPrice) as caught:
        contracts.screen_field(bad['results'][0],PRICE)
    assert caught.value.kind=='nonpositive-screen-price'
    item,requests,_=client([screen_page([bad,screen_row()])])
    result=screen(item)
    assert [r['code'] for r in result.rows]==['US.DEMO']
    assert result.rows[0]['screen_rank']==2
    assert result.status=='success' and result.reason=='screen-rows-excluded'
    assert result.metadata['raw_rows_received']==2 and result.metadata['accepted_rows']==1
    assert result.metadata['rejected_row_count']==1 and result.metadata['pagination_complete'] is True
    rejected=result.metadata['rejected_rows'][0]
    assert rejected['code']=='US.ZERO' and rejected['screen_rank']==1 and rejected['page']==1
    assert rejected['reason']=='nonpositive-screen-price' and rejected['typed_value']==value
    assert rejected['source_payload_hash']==result.rows[0]['revision_vintage']
    assert rejected['known_at_ms']==rejected['retrieved_at_ms']==NOW
    assert len(rejected['typed_value_sha256'])==64 and len(requests)==1


def test_all_excluded_page_can_refill_within_existing_page_budget():
    first=screen_page([screen_row('US.ZERO','0')],more=True,cursor='next',total=2)
    second=screen_page([screen_row()],total=2)
    item,requests,_=client([first,second])
    result=screen(item)
    assert result.status=='success' and result.pages==2 and len(requests)==2
    assert result.metadata['raw_rows_received']==2 and result.metadata['accepted_rows']==1
    assert result.rows[0]['screen_rank']==2 and result.metadata['pagination_complete']
    item,requests,_=client([first],max_pages=1)
    limited=screen(item)
    assert limited.status=='truncated' and limited.reason=='page-budget' and not limited.rows
    assert limited.metadata['raw_rows_received']==1 and not limited.metadata['pagination_complete']
    assert len(requests)==1


def test_complete_all_excluded_source_is_not_empty_source_or_missing_provider_rows():
    item,_,_=client([screen_page([screen_row('US.ZERO','0')])])
    result=screen(item)
    assert result.status=='success' and not result.rows
    assert result.reason=='screen-rows-excluded' and result.metadata['pagination_complete']
    assert result.metadata['total_reported']==result.metadata['raw_rows_received']==1
    assert result.metadata['accepted_rows']==0 and result.metadata['rejected_row_count']==1
    item,_,_=client([screen_page([])])
    empty=screen(item)
    assert empty.status=='empty' and empty.metadata['raw_rows_received']==0
    assert empty.metadata['rejected_row_count']==0


@pytest.mark.parametrize('mutation', ['wrong-price-tag','bad-integer','bool-price','nonfinite-price',
    'negative-volume','negative-turnover','wrong-later-descriptor','wrong-later-tag'])
def test_nonpositive_row_never_hides_a_malformed_wire_field(mutation):
    row=screen_row('US.ZERO','0')
    factor=3105 if mutation=='negative-turnover' else 3104
    query={'cumulative_property':{'name':factor,'days':1,'period_average':False}}
    later={'cumulative_property_result':{'property':{'name':factor,'days':1,'period_average':0},
        'res':{'result_type':2,'ival':'1000'}}}
    row['results'].append(later)
    price=row['results'][0]['simple_property_result']
    if mutation=='wrong-price-tag':price['res']={'result_type':3,'sval':'0'}
    elif mutation=='bad-integer':price['res']['ival']='0,000'
    elif mutation=='bool-price':price['res']['ival']=False
    elif mutation=='nonfinite-price':price['res']['ival']='9'*512
    elif mutation in ('negative-volume','negative-turnover'):later['cumulative_property_result']['res']['ival']='-1'
    elif mutation=='wrong-later-descriptor':later['cumulative_property_result']['property']['days']=2
    elif mutation=='wrong-later-tag':later['cumulative_property_result']['res']={'result_type':3,'sval':'1000'}
    item,requests,_=client([screen_page([row])])
    with pytest.raises(RESTError) as caught:
        item.screen(retrieve_queries=[PRICE,query],sort=SORT)
    assert not isinstance(caught.value,contracts.NonpositiveScreenPrice)
    assert len(requests)==1


@pytest.mark.parametrize('case',['duplicate-excluded','raw-row-budget','changed-total','upstream'])
def test_excluded_rows_preserve_duplicate_total_budget_and_first_failure_guards(case):
    first=screen_page([screen_row('US.ZERO','0')],more=True,cursor='next',total=2)
    second=screen_page([screen_row()],total=2)
    options={}
    if case=='duplicate-excluded':second=screen_page([screen_row('US.ZERO','0')],total=2)
    elif case=='raw-row-budget':options['max_rows']=1
    elif case=='changed-total':second=screen_page([screen_row()],total=3)
    else:second=ReadResponse(429,b'fictional-private-provider-message')
    item,requests,_=client([first,second],**options)
    with pytest.raises(RESTError):screen(item)
    assert len(requests)==2


def test_rejection_receipts_have_explicit_size_cap_and_omit_long_raw_literals(monkeypatch):
    item,_,_=client([screen_page([screen_row('US.ZERO','0'*512)])])
    rejected=screen(item).metadata['rejected_rows'][0]
    assert 'typed_value' not in rejected and rejected['typed_value_type']=='str'
    monkeypatch.setattr(provider,'MAX_SCREEN_REJECTION_BYTES',1)
    item,requests,_=client([screen_page([screen_row('US.ZERO','0')])])
    with pytest.raises(RESTError) as caught:screen(item)
    assert caught.value.kind=='screen-rejection-budget' and len(requests)==1


@pytest.mark.parametrize('floor,raw_floor',[(1,1000),(5,5000)])
def test_exact_optional_inclusive_price_floor_preserves_request_and_signing_bytes(floor,raw_floor):
    queries=provider.screen_queries_for_price_floor(floor)
    expected=[{'simple_field_query':{'simple_field':1,'screen_value_list':[2]}},
        {'simple_property_query':{'property':{'name':2201},'lower':{'value':raw_floor,'includes':True}}}]
    assert queries==expected
    item,requests,signed=client([screen_page(more=True,cursor='opaque',total=2),screen_page([screen_row('US.OTHER')],total=2)])
    item.screen(retrieve_queries=[PRICE],sort=SORT,screen_queries=queries)
    bodies=[json.loads(r.body) for r in requests]
    assert bodies[0]['screen_queries']==expected and bodies[1].pop('next_key')=='opaque'
    assert bodies[0]==bodies[1]
    assert signed==['\n'.join((str(NOW),'POST',provider.SCREEN,'',hashlib.sha256(r.body).hexdigest())).encode() for r in requests]
    queries[1]['simple_property_query']['lower']['value']=999
    assert provider.screen_queries_for_price_floor(floor)==expected


@pytest.mark.parametrize('change',['missing-US','duplicate','wrong-market','arbitrary-property','wrong-floor','exclusive',
    'bool-bound','float-bound','holdings','watchlist','average-turnover','extra-upper','reversed'])
def test_only_three_exact_screen_query_presets_are_supported_before_signing(change):
    queries=provider.screen_queries_for_price_floor(5)
    price=queries[1]['simple_property_query']
    if change=='missing-US':queries.pop(0)
    elif change=='duplicate':queries.append(copy.deepcopy(queries[1]))
    elif change=='wrong-market':queries[0]['simple_field_query']['screen_value_list']=[1]
    elif change=='arbitrary-property':price['property']['name']=2301
    elif change=='wrong-floor':price['lower']['value']=2000
    elif change=='exclusive':price['lower']['includes']=False
    elif change=='bool-bound':price['lower']['value']=True
    elif change=='float-bound':price['lower']['value']=5000.0
    elif change=='holdings':queries.append({'user_stock_list_mode':2})
    elif change=='watchlist':queries.append({'watchlist_stock_ids':[1]})
    elif change=='average-turnover':queries.append({'cumulative_property_query':{'property':{'name':3105,'days':20,'period_average':True},'lower':{'value':25000000000,'includes':True}}})
    elif change=='extra-upper':price['upper']={'value':100000,'includes':True}
    else:queries.reverse()
    item,requests,signed=client([])
    with pytest.raises(RESTError) as caught:item.screen(retrieve_queries=[PRICE],sort=SORT,screen_queries=queries)
    assert caught.value.kind=='unsupported-screen-filter' and not requests and not signed
