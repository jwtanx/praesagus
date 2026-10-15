"""Standalone bounded REST research reads. All external capabilities are injected."""
from dataclasses import replace
from datetime import timedelta
import base64
import csv
import hashlib
import json
from pathlib import Path
import re
import threading
from typing import Mapping
from urllib.parse import urlencode

from connectors.moomoo_rest import (MAX_RESPONSE_BYTES, ReadRequest, ReadResponse, RESTError,
    _decode, _invoke, _retry_after, _text)
from connectors.moomoo_rest_live import SecureReadTransport, LiveReadError
from contracts import (Batch, ContractError, code, descriptor, history_coverage, integer, iso_date,
                       need, normalize_bar, normalize_basic, normalize_snapshot, screen_field, text)
from config import ProviderConfig

SCREEN = '/api/v1.0/quote/stock-screen'
BASIC = '/api/v1.0/quote/stock-basicinfo'
SNAPSHOT = '/api/v1.0/quote/snapshot'
INDUSTRY = '/api/v1.0/quote/plate-list'
META_RE = r'/api/v1\.0/quote/US\.[A-Z][A-Z0-9.-]{0,63}/(?:owner-plate|company/profile)'
POST_PATHS = frozenset({SCREEN, BASIC, SNAPSHOT})


def allowed_request(method, path):
    return (method == 'POST' and path in POST_PATHS or method == 'GET' and isinstance(path, str)
            and (re.fullmatch(r'/api/v1\.0/quote/US\.[A-Z][A-Z0-9.-]{0,63}/history-kline', path) is not None or re.fullmatch(META_RE, path) is not None or path == INDUSTRY))


class ResearchReadTransport(SecureReadTransport):
    """Inherit verified TLS/size/redirect/deadline behavior; separate quote-only allowlist."""
    @staticmethod
    def _validate(request):
        if not isinstance(request, ReadRequest) or not allowed_request(request.method, request.path):
            raise LiveReadError('invalid-request')
        # Shared shape/header validation, without changing bytes actually sent/signed.
        metadata = request.method == 'GET' and (request.path == INDUSTRY or re.fullmatch(META_RE, request.path))
        if metadata and (request.body or request.query != ('market=US&plate_class=INDUSTRY' if request.path == INDUSTRY else '')):
            raise LiveReadError('invalid-request')
        shared = (replace(request, path='/api/v1.0/quote/find-news') if metadata else
                  replace(request, path=SNAPSHOT) if request.method == 'POST' else request)
        return SecureReadTransport._validate(shared)

    def __repr__(self):
        return '<StockResearchReadTransport>'


class ResearchProvider:
    def __init__(self, *, api_key, signer, transport, clock_ms, nonce_factory, config=None):
        need(_text(api_key, 512) and api_key.isascii(), 'invalid-credential-input')
        need(all(callable(value) for value in (signer, transport, clock_ms, nonce_factory)), 'invalid-capability')
        self.config = config or ProviderConfig()
        need(isinstance(self.config, ProviderConfig), 'invalid-config')
        self._api_key, self._signer, self._transport = api_key, signer, transport
        self._clock_ms, self._nonce_factory = clock_ms, nonce_factory
        self._requests_used = self._rows_used = 0
        self._stopped = False
        self._lock = threading.Lock()

    def __repr__(self):
        return '<StockResearchProvider>'

    @property
    def budgets(self):
        return {'requests_used': self._requests_used, 'rows_used': self._rows_used,
                'max_requests': self.config.max_requests, 'max_rows': self.config.max_rows}

    @staticmethod
    def capabilities():
        return {'native_bullish_count': None, 'native_bearish_count': None,
                'native_count_status': 'methodology-unverified', 'rest_numeric_quota': None,
                'entitlements': 'unverified', 'live_coverage': 'unverified',
                'cumulative_response_shape': 'reviewed-daily-wrapper/int-flag-echo', 'metadata_endpoints': 'documented/mocked-only', 'history_next_time_paging': 'unverified-not-used', 'provider_bar_finality': 'unverified'}

    def _clock(self):
        value = _invoke(self._clock_ms, kind='clock-failed')
        need(integer(value, 1), 'clock-failed')
        return value

    def _read(self, method, path, query=(), *, body=b''):
        need(allowed_request(method, path), 'endpoint-forbidden')
        need(not self._stopped, 'provider-stopped')
        need(self._lock.acquire(blocking=False), 'concurrent-request-forbidden')
        try:
            need(self._requests_used < self.config.max_requests, 'request-budget')
            need(isinstance(body, bytes) and len(body) <= 32768, 'invalid-request')
            started = self._clock()
            nonce = _invoke(self._nonce_factory, kind='nonce-failed')
            need(isinstance(nonce, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', nonce) is not None, 'nonce-failed')
            raw_query = urlencode(query)
            digest = hashlib.sha256(body).hexdigest() if body else ''
            canonical = '\n'.join((str(started), method, path, raw_query, digest)).encode()
            signature = _invoke(self._signer, canonical, kind='signer-failed')
            need(isinstance(signature, bytes) and 0 < len(signature) <= 4096, 'signer-failed')
            headers = {'X-Api-Key': self._api_key, 'Authorization': base64.b64encode(signature).decode('ascii'),
                       'X-Timestamp': str(started), 'X-Nonce': nonce}
            if body:
                headers['Content-Type'] = 'application/json'
            request = ReadRequest(method, path, raw_query, body, headers, self.config.timeout_seconds)
            # Validate even injected transports; no accounts, arbitrary URLs or malformed wire.
            ResearchReadTransport._validate(request)
            self._requests_used += 1
            response = _invoke(self._transport, request, kind='transport-failed')
            retrieved = self._clock()
            need(retrieved >= started, 'clock-failed')
            need(isinstance(response, ReadResponse) and integer(response.status, 100, 599)
                 and isinstance(response.headers, Mapping)
                 and all(isinstance(k, str) and isinstance(v, str) for k, v in response.headers.items()), 'malformed-response')
            if response.status == 429:
                self._stopped = True
                raise RESTError('rate-limited', _retry_after(response.headers, retrieved))
            if response.status >= 500:
                raise RESTError('upstream-failed')
            if response.status != 200:
                raise RESTError('http-failed')
            need(isinstance(response.body, bytes) and len(response.body) <= MAX_RESPONSE_BYTES, 'malformed-response')
            payload = _decode(response.body)
            need(type(payload.get('ret_code')) is int and isinstance(payload.get('ret_msg'), str)
                 and 's' not in payload and 'data' in payload, 'malformed-response')
            if payload['ret_code'] != 0:
                raise RESTError('provider-failed')
            need(isinstance(payload['data'], dict), 'malformed-response')
            return payload, started, retrieved, hashlib.sha256(response.body).hexdigest()
        finally:
            self._lock.release()

    def _count_rows(self, count):
        need(self._rows_used + count <= self.config.max_rows, 'row-budget')
        self._rows_used += count

    @staticmethod
    def _body(value):
        failed = False
        try:
            body = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        except (TypeError, ValueError):
            failed = True
        if failed:
            raise ContractError('invalid-request')
        need(len(body) <= 32768, 'invalid-request')
        return body

    @staticmethod
    def _rows(data, key, limit):
        rows = data.get(key)
        need(isinstance(rows, list) and len(rows) <= limit and all(isinstance(row, dict) for row in rows), 'invalid-page')
        return rows

    def screen(self, *, retrieve_queries, sort, screen_queries=None, page_limit=None):
        need(isinstance(retrieve_queries, list) and 1 <= len(retrieve_queries) <= 16, 'invalid-screen-query')
        for query in retrieve_queries:
            descriptor(query)
        need(isinstance(sort, dict) and type(sort.get('direction')) is int and sort['direction'] in (1, 2)
             and len(sort) == 2, 'invalid-screen-query')
        descriptor({key: value for key, value in sort.items() if key != 'direction'})
        us_filter = {'simple_field_query': {'simple_field': 1, 'screen_value_list': [2]}}
        queries = [us_filter] if screen_queries is None else screen_queries
        # Initial reviewed contract supports US market identity only; eligibility uses actual history later.
        need(self._body(queries) == self._body([us_filter]), 'unsupported-screen-filter')
        pages_allowed = self.config.max_pages if page_limit is None else page_limit
        need(integer(pages_allowed, 1, self.config.max_pages), 'invalid-page-budget')
        frozen = {'limit': self.config.screen_limit, 'retrieve_queries': retrieve_queries,
                  'screen_queries': queries, 'sort': sort}
        base = json.loads(self._body(frozen))
        seen, cursors, output = set(), set(), []
        cursor = None
        started = ended = None
        reported_total = None
        for page in range(1, pages_allowed + 1):
            request = dict(base)
            if cursor is not None:
                request['next_key'] = cursor
            payload, stamp, ended, vintage = self._read('POST', SCREEN, body=self._body(request))
            started = started or stamp
            rows = self._rows(payload['data'], 'items', self.config.screen_limit)
            pagination = payload.get('pagination')
            need(isinstance(pagination, dict) and type(pagination.get('has_more')) is bool
                 and integer(pagination.get('total')) and text(pagination.get('next_key'), 4096), 'invalid-pagination')
            more, next_key = pagination['has_more'], pagination['next_key']
            if reported_total is None:
                reported_total = pagination['total']
            need(pagination['total'] == reported_total, 'pagination-total-changed')
            need(more or next_key == '-1', 'invalid-pagination')
            need(not more or bool(rows) and next_key != '-1' and next_key not in cursors, 'pagination-no-progress')
            self._count_rows(len(rows))
            for row in rows:
                identity = code(row.get('code'))
                need(identity not in seen and text(row.get('name')), 'duplicate-or-invalid-screen-code')
                seen.add(identity)
                results = row.get('results')
                need(isinstance(results, list) and len(results) == len(retrieve_queries), 'descriptor-mismatch')
                values = tuple(screen_field(wrapper, query) for wrapper, query in zip(results, retrieve_queries))
                output.append({'code': identity, 'name': row['name'], 'fields': values,
                               'retrieved_at_ms': ended, 'known_at_ms': ended, 'source': 'moomoo-rest-screen',
                               'revision_vintage': vintage})
            need(len(output) <= reported_total, 'invalid-pagination')
            if not more:
                missing = len(output) != reported_total
                return Batch(tuple(output), 'screen', 'partial' if missing else 'success' if output else 'empty',
                             'reported-total-incomplete' if missing else None, page,
                             requested_at_ms=started, retrieved_at_ms=ended,
                             metadata={'total_reported': pagination['total'], 'budgets': self.budgets})
            cursors.add(next_key)
            cursor = next_key
        return Batch(tuple(output), 'screen', 'truncated', 'page-budget', pages_allowed,
                     requested_at_ms=started, retrieved_at_ms=ended, metadata={'budgets': self.budgets})

    def _codes(self, codes, path, row_key, normalizer):
        need(isinstance(codes, (list, tuple)) and 1 <= len(codes) <= 400, 'invalid-code-list')
        wanted = tuple(code(value) for value in codes)
        need(len(set(wanted)) == len(wanted), 'duplicate-code-request')
        payload, started, ended, vintage = self._read('POST', path, body=self._body({'code_list': list(wanted)}))
        rows = self._rows(payload['data'], row_key, len(wanted))
        returned = set()
        output = []
        self._count_rows(len(rows))
        for row in rows:
            identity = code(row.get('code'))
            need(identity in wanted and identity not in returned, 'unrequested-or-duplicate-code')
            returned.add(identity)
            output.append(normalizer(row, ended) | {'revision_vintage': vintage})
        missing = tuple(value for value in wanted if value not in returned)
        return Batch(tuple(output), path.rsplit('/', 1)[-1], 'partial' if missing else 'success',
                     'requested-codes-missing' if missing else None, 1, missing, started, ended)

    def basicinfo(self, codes):
        return self._codes(codes, BASIC, 'basic_list', normalize_basic)

    def snapshots(self, codes):
        return self._codes(codes, SNAPSHOT, 'snapshot_list', normalize_snapshot)

    def source_metadata(self, security_code, kind):
        code(security_code)
        need(kind in {'owner-plate', 'company/profile'}, 'unsupported-metadata')
        path = f'/api/v1.0/quote/{security_code}/{kind}'
        payload, started, ended, vintage = self._read('GET', path)
        key = 'sectors' if kind == 'owner-plate' else 'items'
        rows = self._rows(payload['data'], key, 400)
        self._count_rows(len(rows))
        normalized = []
        unsupported_types = {}
        for row in rows:
            if kind == 'owner-plate':
                need(text(row.get('plate_code')) and text(row.get('plate_name'))
                     and text(row.get('plate_type'), 128), 'invalid-industry-record')
                value = {name: row.get(name) for name in ('plate_code', 'plate_name', 'plate_type', 'name')}
                supported = row['plate_type'] in {'INDUSTRY', 'CONCEPT', 'OTHER'}
                value['plate_type_status'] = 'supported' if supported else 'unsupported'
                if not supported:
                    unsupported_types[row['plate_type']] = unsupported_types.get(row['plate_type'], 0) + 1
            else:
                need(text(row.get('name')) and isinstance(row.get('value'), str) and len(row['value']) <= 16384
                     and type(row.get('field_type')) is int and row['field_type'] in (0, 1, 2)
                     and ('attribute_type' not in row or integer(row['attribute_type'], 0, 10000)), 'invalid-profile-record')
                value = {name: row.get(name) for name in ('name', 'value', 'field_type', 'attribute_type')}
            normalized.append(value)
        metadata = {'code': security_code, 'raw_payload_hash': vintage, 'known_at_ms': ended,
                    'effective_from': None, 'effective_to': None, 'classification': 'raw-current-only'}
        if kind == 'owner-plate':
            metadata.update(unsupported_type_counts=dict(sorted(unsupported_types.items())),
                            unsupported_type_rows=sum(unsupported_types.values()))
        return Batch(tuple(normalized), kind, 'partial' if unsupported_types else 'success' if rows else 'empty',
                     'unsupported-plate-types' if unsupported_types else None, 1,
                     requested_at_ms=started, retrieved_at_ms=ended,
                     metadata=metadata)

    def industry_catalog(self):
        payload, started, ended, vintage = self._read('GET', INDUSTRY, [('market', 'US'), ('plate_class', 'INDUSTRY')])
        rows = self._rows(payload['data'], 'plate_list', 2000)
        self._count_rows(len(rows))
        seen = set()
        output = []
        for row in rows:
            need(text(row.get('code')) and row['code'].startswith('US.') and text(row.get('plate_id'))
                 and text(row.get('plate_name')) and row['code'] not in seen, 'invalid-taxonomy')
            seen.add(row['code'])
            output.append({key: row.get(key) for key in ('code', 'plate_id', 'plate_name', 'sc_name', 'tc_name')})
        return Batch(tuple(output), 'industry-catalog', 'success' if rows else 'empty', None, 1,
                     requested_at_ms=started, retrieved_at_ms=ended,
                     metadata={'taxonomy_id': 'moomoo-rest-US-INDUSTRY', 'taxonomy_snapshot_hash': vintage,
                               'known_at_ms': ended, 'effective_from': None, 'effective_to': None})

    def history(self, security_code, *, start, end, currency_evidence=None, session_closes=None):
        code(security_code)
        first, last = iso_date(start), iso_date(end)
        need(first <= last, 'invalid-history-range')
        output, seen, seen_times, sources = [], set(), set(), []
        pages = 0
        requested = retrieved = None
        right = last
        while right >= first and pages < self.config.max_pages:
            left = max(first, right - timedelta(days=self.config.history_window_days - 1))
            query = [('start', left.isoformat()), ('end', right.isoformat()), ('ktype', 2),
                     ('autype', self.config.autype), ('num', self.config.history_num)]
            failure=None
            try:payload, stamp, retrieved, vintage = self._read('GET', f'/api/v1.0/quote/{security_code}/history-kline', query)
            except RESTError as error:failure=error
            if failure is not None:
                if output:
                    return Batch(tuple(sorted(output,key=lambda row:row['session_date'])),'history','partial',failure.kind,pages,
                        requested_at_ms=requested,retrieved_at_ms=retrieved,
                        metadata={'windows':sources,'coverage':'incomplete','stopped_on_failure':True,'budgets':self.budgets})
                raise RESTError(failure.kind,failure.retry_after)

            requested = requested or stamp
            pages += 1
            data = payload['data']
            rows = self._rows(data, 'kline_list', self.config.history_num)
            self._count_rows(len(rows))
            dates, times = set(), set()
            for row in rows:
                normalized = normalize_bar(row, security_code=security_code, start=left.isoformat(), end=right.isoformat(),
                    retrieved_at_ms=retrieved, volume_precision=data.get('volume_precision'), autype=self.config.autype,
                    vintage=vintage, currency_evidence=currency_evidence, session_closes=session_closes)
                day, time = normalized['session_date'], normalized['source_at_ms']
                need(day not in seen and day not in dates and time not in times and time not in seen_times, 'duplicate-history-date')
                dates.add(day);times.add(time)
                output.append(normalized)
            seen.update(dates)
            seen_times.update(times)
            next_time = data.get('next_time')
            need(next_time is None or integer(next_time), 'invalid-next-time')
            sources.append({'start': left.isoformat(), 'end': right.isoformat(), 'next_time_raw': next_time,
                            'revision_vintage': vintage, 'retrieved_at_ms': retrieved})
            # Use only actual returned session dates for backward progress. Never translate
            # undocumented millisecond next_time into the ISO end request parameter.
            next_end = iso_date(min(dates)) - timedelta(days=1) if dates else left - timedelta(days=1)
            need(next_end < right, 'history-no-progress')
            right = next_end
        truncated = right >= first
        return Batch(tuple(sorted(output, key=lambda row: row['session_date'])), 'history',
                     'truncated' if truncated else 'success' if output else 'empty', 'page-budget' if truncated else None,
                     pages, requested_at_ms=requested, retrieved_at_ms=retrieved,
                     metadata={'windows': sources, 'coverage': 'requires-actual-calendar-evidence', 'next_time_status': 'unverified-not-used', 'budgets': self.budgets})


def build_live_provider(locator, *, clock_ms, nonce_factory, config=None, allow_live=False,
                        credential_loader=None, transport=None):
    """Explicit capability construction only; caller must authorize the live pilot first."""
    need(allow_live is True, 'live-not-authorized')
    if credential_loader is None:
        from ingest.market_collector import load_credentials
        credential_loader = load_credentials
    credentials = _invoke(credential_loader, locator, kind='credential-unavailable')
    need(isinstance(credentials, tuple) and len(credentials) == 2, 'credential-unavailable')
    api_key, signer = credentials
    return ResearchProvider(api_key=api_key, signer=signer,
        transport=transport if transport is not None else ResearchReadTransport(),
        clock_ms=clock_ms, nonce_factory=nonce_factory, config=config)


def classify_discovered_etfs(discovered_codes, registry_path=None):
    """Lookup only: registry never emits candidates that were not independently discovered."""
    wanted = tuple(code(value) for value in discovered_codes)
    need(len(set(wanted)) == len(wanted), 'duplicate-code-request')
    path = Path(registry_path) if registry_path is not None else Path(__file__).with_name('etf_metadata.csv')
    with path.open(newline='') as stream:
        registry = list(csv.DictReader(stream))
    by_code = {}
    for row in registry:
        identity = code('US.' + row.get('symbol', ''))
        need(identity not in by_code and row.get('registry_purpose') == 'classification_only', 'invalid-etf-registry')
        need(row.get('signed_leverage') in {'-3', '-2', '-1', '1', '2', '3'}
             and row.get('reset') in {'daily', 'not_applicable'} and text(row.get('issuer'))
             and text(row.get('benchmark_name')) and text(row.get('exposure_family'))
             and row.get('etf_verification_url', '').startswith('https://'), 'invalid-etf-registry')
        iso_date(row.get('source_asof'))
        by_code[identity] = row
    return {identity: (dict(by_code[identity]) | {'listing_verified': False, 'selection_eligible': False,
        'classification_status': 'issuer-identity-only'}) if identity in by_code else
        {'classification_status': 'unavailable', 'signed_leverage': None, 'selection_eligible': False}
        for identity in wanted}
