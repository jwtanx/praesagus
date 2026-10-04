import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.catalyst_services import _normalize, get_catalysts, safe_url
from backend.main import app

NOW = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)


def write(tmp_path, dataset, rows):
    (tmp_path / f'{dataset}.json').write_text(json.dumps(rows), encoding='utf-8')


def news(source_id='n1', **overrides):
    record = {'source_id': source_id, 'ticker': ' aapl ', 'title': 'Company announcement',
              'link': 'https://example.org/news', 'source_name': 'Fixture provider',
              'published_at': '2026-10-01T09:00:00+02:00', 'first_seen_at': '2026-10-01T07:05:00Z',
              'ingest_ts': '2026-10-01T07:06:00Z', 'signal': 'watch', 'transaction_value': 1}
    record.update(overrides)
    return record


def test_four_raw_datasets_and_provenance(tmp_path):
    write(tmp_path, 'news', [news()])
    write(tmp_path, 'filings', [{'source_id': 'n1', 'ticker': 'AAPL', 'company_name': 'Apple', 'form_type': '8-K',
          'acceptance_datetime': '2026-10-01T06:00:00-04:00', 'filing_date': '2026-10-01',
          'document_url': 'https://sec.gov/document', 'filing_url': 'https://sec.gov/filing'}])
    write(tmp_path, 'insider_trades', [{'source_id': 'n1', 'ticker': 'AAPL', 'transaction_date': '2026-09-29',
          'acceptance_datetime': '2026-10-01T11:00:00Z', 'reporting_owner_name': 'Owner', 'transaction_code_label': 'Sale',
          'transaction_code': 'S', 'document_url': 'https://sec.gov/trade', 'transaction_value': 1, 'signal': 'watch'}])
    write(tmp_path, 'calendar', [{'source_id': 'c1', 'ticker': None, 'event_type': 'macro', 'event_date': '2026-10-02',
          'event_time': '09:30:00', 'timezone': 'America/New_York', 'estimated': True,
          'metadata': {'source_url': 'https://example.org/calendar'}}])
    result = get_catalysts(now=NOW, data_dir=tmp_path)
    assert result['total'] == 4
    assert len({r['id'] for r in result['records']}) == 4
    scheduled, filing, article, trade = result['records']
    assert scheduled['scheduled'] and scheduled['event_at'] == '2026-10-02T13:30:00+00:00'
    assert scheduled['estimated'] is True and scheduled['ticker'] is None
    assert filing['source'] == 'SEC' and filing['source_url'] == 'https://sec.gov/document'
    assert article['event_at'] == '2026-10-01T07:00:00+00:00'
    assert article['published_at'] == '2026-10-01T09:00:00+02:00'
    assert article['available_at'] == '2026-10-01T07:05:00Z'
    assert article['ingested_at'] == '2026-10-01T07:06:00Z'
    assert trade['event_at'] == '2026-09-29' and trade['time_precision'] == 'date'
    assert trade['available_at'] == '2026-10-01T11:00:00Z'
    assert trade['subtype'] == 'S' and 'informed' not in trade['title']
    assert result['retrieved_at'] == NOW.isoformat()


def test_file_status_empty_corrupt_shapes_and_bad_rows(tmp_path):
    write(tmp_path, 'news', [])
    (tmp_path / 'filings.json').write_text('{broken')
    write(tmp_path, 'calendar', {'records': [None, [], {}, {'title': {'bad': 'type'}}, {'source_id': 'ok', 'event_date': '2026-10-03'}]})
    result = get_catalysts(now=NOW, data_dir=tmp_path)
    statuses = result['dataset_status']
    assert statuses['news']['status'] == 'loaded' and statuses['news']['records_loaded'] == 0
    assert statuses['filings']['status'] == 'unreadable'
    assert statuses['insider_trades']['status'] == 'absent'
    assert statuses['calendar']['rows_skipped'] == 4 and result['count'] == 1
    for invalid in [{'records': {}}, 1, {'nothing': []}]:
        write(tmp_path, 'news', invalid)
        assert get_catalysts(now=NOW, data_dir=tmp_path)['dataset_status']['news']['status'] == 'unreadable'
    (tmp_path / 'news.json').write_text('[{"title": NaN}]')
    assert get_catalysts(now=NOW, data_dir=tmp_path)['dataset_status']['news']['status'] == 'unreadable'


def test_dedup_representative_and_fallback_are_input_order_independent(tmp_path):
    older = news(ingest_ts='2026-09-30T00:00:00Z', title='Older')
    newer = news(title='Latest')
    future = news(ingest_ts='2099-01-01T00:00:00Z', title='Future ingestion')
    missing_id = news(source_id=None, title='No provider identity')
    rows = [older, newer, future, missing_id, missing_id]
    write(tmp_path, 'news', rows)
    first = get_catalysts(now=NOW, data_dir=tmp_path)
    write(tmp_path, 'news', list(reversed(rows)))
    second = get_catalysts(now=NOW, data_dir=tmp_path)
    assert first == second
    assert first['total'] == 2
    assert first['dataset_status']['news']['duplicates_removed'] == 3
    assert any(r['title'] == 'Latest' for r in first['records'])
    hashed = next(r for r in first['records'] if r['source_id'] is None)
    assert hashed['id'].startswith('news:sha256:') and 'exact-record hash' in hashed['data_gaps'][0]
    write(tmp_path, 'news', [news(title='A'), news(title='Z')])
    one = get_catalysts(now=NOW, data_dir=tmp_path)
    write(tmp_path, 'news', [news(title='Z'), news(title='A')])
    assert get_catalysts(now=NOW, data_dir=tmp_path) == one


def test_timestamps_future_observed_and_date_precision(tmp_path):
    write(tmp_path, 'news', [news('naive', published_at='2026-10-01T09:00:00'), news('bad', published_at='not-a-date'),
          news('future', published_at='2026-10-03T00:00:00Z'), news('good')])
    write(tmp_path, 'filings', [{'source_id': 'date', 'filing_date': '2026-09-30'},
          {'source_id': 'ambiguous', 'acceptance_datetime': '2026-10-01T08:00:00', 'filing_date': '2026-10-01'}])
    write(tmp_path, 'calendar', [{'source_id': 'future', 'event_date': '2026-10-04'},
          {'source_id': 'past', 'event_date': '2026-09-28'},
          {'source_id': 'dst', 'event_date': '2026-11-01', 'event_time': '01:30:00', 'timezone': 'America/New_York'},
          {'source_id': 'tzbad', 'event_date': '2026-10-02', 'event_time': '09:30:00', 'timezone': 'Invalid/Zone'}])
    result = get_catalysts(now=NOW, data_dir=tmp_path)
    by_id = {r['source_id']: r for r in result['records'] if r['event_type'] != 'calendar'}
    assert result['records'][0]['scheduled'] and result['records'][0]['event_at'] == '2026-10-04'
    assert result['records'][0]['time_precision'] == 'date'
    assert by_id['future']['event_at'] is None and 'future' in ' '.join(by_id['future']['data_gaps'])
    assert by_id['naive']['event_at'] is None and by_id['naive']['published_at'] == '2026-10-01T09:00:00'
    assert by_id['ambiguous']['event_at'] is None
    assert by_id['date']['event_at'] == '2026-09-30' and by_id['date']['timezone'] is None
    assert all(r['event_at'] is None for r in result['records'][-5:])
    assert all(r['event_at'] is None for r in result['records'] if r['source_id'] in ('dst', 'tzbad'))


def test_filtering_before_paging_and_stable_ties(tmp_path):
    write(tmp_path, 'news', [news(str(i), ticker='MSFT' if i == 0 else 'AAPL') for i in range(6)])
    write(tmp_path, 'calendar', [{'source_id': 'global', 'event_date': '2026-10-02'}])
    result = get_catalysts(ticker=' aapl ', event_type='news', limit=2, offset=2, now=NOW, data_dir=tmp_path)
    assert result['total'] == 5 and result['count'] == 2 and result['offset'] == 2
    assert [r['source_id'] for r in result['records']] == ['3', '4']
    assert get_catalysts(ticker='NONE', now=NOW, data_dir=tmp_path)['total'] == 0
    assert get_catalysts(offset=100, now=NOW, data_dir=tmp_path)['count'] == 0
    assert get_catalysts(ticker='AAPL', now=NOW, data_dir=tmp_path)['total'] == 5


@pytest.mark.parametrize('link', ['javascript:alert(1)', 'data:text/html,test', 'https://user:password@example.org/', '//example.org/', 'https://example.org/\nattack', 'https://example.org\\evil', 'not-url'])
def test_unsafe_links_are_never_exposed(tmp_path, link):
    write(tmp_path, 'news', [news(link=link)])
    row = get_catalysts(now=NOW, data_dir=tmp_path)['records'][0]
    assert row['source_url'] is None and 'unsafe' in ' '.join(row['data_gaps'])


def test_api_auth_bounds_env_and_no_providers(tmp_path, monkeypatch):
    write(tmp_path, 'news', [news()])
    monkeypatch.setenv('PRAESAGUS_FINANCIAL_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('PRAESAGUS_API_KEY', 'fixture-key')
    client = TestClient(app)
    assert client.get('/api/v1/financial/catalysts').status_code == 401
    with patch('requests.sessions.Session.request', side_effect=AssertionError('provider call')), patch('connectors.financial.filters.apply_filters', side_effect=AssertionError('dashboard filters applied')):
        response = client.get('/api/v1/financial/catalysts', params={'ticker': ' aapl ', 'event_type': 'news'}, headers={'X-API-Key': 'fixture-key'})
    assert response.status_code == 200 and response.json()['count'] == 1
    for params in [{'limit': 0}, {'limit': 201}, {'offset': -1}, {'offset': 10001}, {'event_type': 'buy'}, {'ticker': '   '}, {'ticker': 'x' * 33}]:
        assert client.get('/api/v1/financial/catalysts', params=params, headers={'X-API-Key': 'fixture-key'}).status_code == 422
    assert client.get('/api/v1/financial/catalysts', headers={'Authorization': 'Bearer fixture-key'}).status_code == 200


def test_future_source_times_discrepancies_and_read_only(tmp_path):
    write(tmp_path, 'news', [news(first_seen_at='2026-10-01T06:00:00Z', ingest_ts='2026-10-02T00:00:00Z')])
    before = (tmp_path / 'news.json').read_bytes()
    row = get_catalysts(now=NOW, data_dir=tmp_path)['records'][0]
    assert row['ingested_at'] == '2026-10-02T00:00:00Z'
    assert 'future' in ' '.join(row['data_gaps'])
    assert 'precedes' in ' '.join(row['data_gaps'])
    assert (tmp_path / 'news.json').read_bytes() == before


def test_unreadable_file_and_future_observed_date(tmp_path, monkeypatch):
    write(tmp_path, 'insider_trades', [{'source_id': 'future', 'transaction_date': '2026-10-03'}])
    row = get_catalysts(now=NOW, data_dir=tmp_path)['records'][0]
    assert row['event_at'] is None and row['scheduled'] is False
    original = type(tmp_path).read_text
    def denied(path, *args, **kwargs):
        if path.name == 'news.json':
            raise PermissionError('synthetic fixture permission denial')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(type(tmp_path), 'read_text', denied)
    assert get_catalysts(now=NOW, data_dir=tmp_path)['dataset_status']['news']['status'] == 'unreadable'


def test_date_only_calendar_uses_supplied_zone_without_midnight(tmp_path):
    write(tmp_path, 'calendar', [{'source_id': 'local', 'event_date': '2026-10-02', 'timezone': 'Pacific/Auckland'}])
    row = get_catalysts(now=NOW, data_dir=tmp_path)['records'][0]
    assert row['event_at'] == '2026-10-02' and row['time_precision'] == 'date'
    assert row['timezone'] == 'Pacific/Auckland' and row['scheduled'] is False


@pytest.mark.parametrize('url', ['https://example.org:bad/source', 'https://example.org:65536/source', 'https://example.org:-1/source'])
def test_invalid_ports_are_null_without_losing_evidence(tmp_path, url):
    assert safe_url(url) is None
    raw = news(link=url)
    direct, _ = _normalize(raw, 'news', NOW)
    assert direct['source_url'] is None
    assert direct['published_at'] == raw['published_at']
    write(tmp_path, 'news', [raw])
    before = (tmp_path / 'news.json').read_bytes()
    result = get_catalysts(now=NOW, data_dir=tmp_path)
    assert result['count'] == 1 and result['dataset_status']['news']['rows_skipped'] == 0
    assert result['records'][0] == direct
    assert 'source_url unavailable or unsafe' in direct['data_gaps']
    assert direct['source_id'] == raw['source_id'] and direct['source'] == raw['source_name']
    assert direct['available_at'] == raw['first_seen_at'] and direct['ingested_at'] == raw['ingest_ts']
    assert (tmp_path / 'news.json').read_bytes() == before


@pytest.mark.parametrize('url', ['https://example.org/source', 'http://example.org:80/source', 'https://example.org:443/source', 'https://example.org:8443/source'])
def test_valid_ports_preserve_original_url(url):
    assert safe_url(url) == url
    row, _ = _normalize(news(link=url), 'news', NOW)
    assert row['source_url'] == url


@pytest.mark.parametrize('metadata', [[], False, 0, '', ['bad'], 'bad'])
def test_nonobject_metadata_rejected_and_counted(tmp_path, metadata):
    invalid = news('invalid', metadata=metadata)
    with pytest.raises(ValueError, match='metadata must be an object'):
        _normalize(invalid, 'news', NOW)
    valid = news('valid', metadata={'source_url': 'https://example.org/provenance'})
    write(tmp_path, 'news', [invalid, valid])
    before = (tmp_path / 'news.json').read_bytes()
    result = get_catalysts(now=NOW, data_dir=tmp_path)
    state = result['dataset_status']['news']
    assert state['status'] == 'loaded' and state['rows_read'] == 2
    assert state['rows_skipped'] == 1 and state['records_loaded'] == 1
    assert result['count'] == 1 and result['records'][0]['source_id'] == 'valid'
    assert result['records'][0]['published_at'] == valid['published_at']
    assert (tmp_path / 'news.json').read_bytes() == before


def test_absent_null_and_object_calendar_metadata_preserve_provenance(tmp_path):
    common = {'event_date': '2026-10-02', 'published_at': '2026-10-01T10:00:00Z',
              'first_seen_at': '2026-10-01T10:05:00Z', 'ingest_ts': '2026-10-01T10:06:00Z'}
    rows = [{**common, 'source_id': 'absent'}, {**common, 'source_id': 'null', 'metadata': None},
            {**common, 'source_id': 'empty', 'metadata': {}},
            {**common, 'source_id': 'object', 'metadata': {'source_url': 'https://example.org:443/calendar'}}]
    write(tmp_path, 'calendar', rows)
    result = get_catalysts(now=NOW, data_dir=tmp_path)
    assert result['count'] == 4 and result['dataset_status']['calendar']['rows_skipped'] == 0
    for row in result['records']:
        assert row['published_at'] == common['published_at']
        assert row['available_at'] == common['first_seen_at'] and row['ingested_at'] == common['ingest_ts']
        assert row['event_at'] == common['event_date'] and row['time_precision'] == 'date'
    assert next(row for row in result['records'] if row['source_id'] == 'object')['source_url'] == 'https://example.org:443/calendar'
