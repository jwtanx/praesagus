"""Typed, provenance-preserving wire normalization; no I/O or financial inference."""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import math
import re
from typing import Any

from connectors.moomoo_rest import RESTError


class ContractError(RESTError):
    pass


def need(condition, kind='invalid-contract'):
    if not condition:
        raise ContractError(kind)


def integer(value, low=0, high=2**63 - 1):
    return type(value) is int and low <= value <= high


def numeric(value, *, positive=False):
    need(type(value) in (int, float), 'invalid-numeric-field')
    failed = False
    try:
        number = float(value)
    except (OverflowError, ValueError):
        failed = True
    if failed:
        raise ContractError('invalid-numeric-field')
    need(math.isfinite(number) and (number > 0 if positive else number >= 0), 'invalid-numeric-field')
    return number


def signed_numeric(value):
    need(type(value) in (int, float), 'invalid-numeric-field')
    failed=False
    try:number=float(value)
    except (OverflowError, ValueError):failed=True
    if failed:raise ContractError('invalid-numeric-field')
    need(math.isfinite(number), 'invalid-numeric-field')
    return number


def code(value):
    need(isinstance(value, str) and re.fullmatch(r'US\.[A-Z][A-Z0-9.-]{0,63}', value) is not None, 'invalid-code')
    return value


def iso_date(value):
    need(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is not None, 'invalid-date')
    failed = False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        failed = True
    if failed:
        raise ContractError('invalid-date')
    return parsed


def text(value, maximum=512):
    return isinstance(value, str) and 0 < len(value) <= maximum and not any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in value)


@dataclass(frozen=True)
class FieldValue:
    value: float | str | None
    raw_value: int | float | str | None
    unit: str | None
    status: str
    reason: str | None = None


def descriptor(query):
    """Exact reviewed descriptor families; never use SDK value_type or formatted value."""
    need(isinstance(query, dict) and len(query) == 1, 'unsupported-descriptor')
    family, properties = next(iter(query.items()))
    need(family in {'simple_property', 'cumulative_property'} and isinstance(properties, dict), 'unsupported-descriptor')
    need(integer(properties.get('name'), 1, 10000), 'unsupported-descriptor')
    if family == 'simple_property':
        need(set(properties) == {'name'}, 'unsupported-descriptor')
        need(properties['name'] not in {3102, 3104, 3105}, 'factor-family-mismatch')
    else:
        need(properties['name'] in {3102, 3104, 3105}, 'unsupported-cumulative-factor')
        need(set(properties) == {'name', 'days', 'period_average'} and integer(properties['days'], 1, 252)
             and type(properties['period_average']) is bool, 'unsupported-descriptor')
        if properties['name'] == 3102:
            need(properties['days'] == 1 and properties['period_average'] is False, 'unsupported-change-rate-window')
    return family, properties


def screen_field(wrapper, query):
    family, properties = descriptor(query)
    expected_key = family + '_result'
    if family == 'cumulative_property' and isinstance(wrapper, dict) and expected_key not in wrapper:
        return FieldValue(None, None, ('average_' if properties['period_average'] else '') + {3104: 'volume', 3105: 'turnover'}.get(properties['name'], '') or None,
                          'unavailable', 'cumulative-response-shape-unverified')
    need(isinstance(wrapper, dict) and set(wrapper) == {expected_key}, 'descriptor-mismatch')
    result = wrapper[expected_key]
    need(isinstance(result, dict) and isinstance(result.get('property'), dict)
         and isinstance(result.get('res'), dict), 'descriptor-mismatch')
    echo = result['property']
    need(set(echo) == set(properties) and type(echo.get('name')) is int and echo['name'] == properties['name'], 'descriptor-mismatch')
    if family == 'cumulative_property':
        need(type(echo.get('days')) is int and echo['days'] == properties['days']
             and type(echo.get('period_average')) is int and echo['period_average'] in (0, 1)
             and echo['period_average'] == int(properties['period_average']), 'descriptor-mismatch')
    raw = result['res']
    tag = raw.get('result_type')
    need(type(tag) is int and tag in (1, 2, 3), 'invalid-result-type')
    key = {1: 'dval', 2: 'ival', 3: 'sval'}[tag]
    name = properties['name']
    units = {2201: 'price', 2301: 'market_cap', 3104: 'volume', 3105: 'turnover'}
    unit = units.get(name)
    if key not in raw:
        return FieldValue(None, None, unit, 'unavailable', 'typed-value-missing')
    value = raw[key]
    if unit is not None:
        need(tag in (1, 2), 'invalid-typed-value')
    if tag == 1:
        number = signed_numeric(value)
    elif tag == 2:
        need(type(value) is int or isinstance(value, str) and re.fullmatch(r'[+-]?\d+(?:\.\d+)?', value) is not None, 'invalid-typed-value')
        number = float(Decimal(value))
        need(math.isfinite(number), 'invalid-typed-value')
    else:
        need(text(value, 4096), 'invalid-typed-value')
        return FieldValue(None, value, None, 'unavailable', 'factor-unit-unverified')
    if name == 3102:
        return FieldValue(None, value, None, 'unavailable', 'change-rate-base-unit-unverified')
    if unit is None:
        return FieldValue(None, value, None, 'unavailable', 'factor-unit-unverified')
    scaled = number / 1000 if name in {2201, 2301, 3105} else number
    need(scaled >= 0, 'invalid-typed-value')
    if name == 2201:
        need(scaled > 0, 'invalid-typed-value')
    if family == 'cumulative_property' and properties['period_average']:
        unit = 'average_' + unit
    return FieldValue(scaled, value, unit, 'available')


@dataclass(frozen=True, repr=False)
class Batch:
    rows: tuple[Any, ...]
    endpoint: str
    status: str
    reason: str | None
    pages: int
    missing_codes: tuple[str, ...] = ()
    requested_at_ms: int | None = None
    retrieved_at_ms: int | None = None
    metadata: dict = field(default_factory=dict)

    def __repr__(self):
        return '<StockResearchBatch>'


def normalize_basic(row, retrieved_at_ms):
    code(row.get('code'))
    need(text(row.get('name')), 'invalid-identity')
    for name in ('stock_type', 'exchange', 'state'):
        need(name not in row or text(row[name]), 'invalid-identity')
    need('suspension' not in row or type(row['suspension']) is bool, 'invalid-identity')
    need('listing_date' not in row or integer(row['listing_date']) and row['listing_date'] <= retrieved_at_ms, 'invalid-listing-time')
    stock_id = row.get('stock_id')
    need(stock_id is None or integer(stock_id, 1) or isinstance(stock_id, str) and re.fullmatch(r'[0-9]{1,19}', stock_id) is not None and 0 < int(stock_id) <= 2**63 - 1, 'invalid-security-id')
    # Internal provider security ID is not an issuer or share-class grouping identifier.
    # No invented sector, issuer, leverage, fundamental period or ETF identity.
    return {key: row.get(key) for key in ('code', 'name', 'stock_id', 'stock_type', 'exchange', 'listing_date', 'suspension', 'state')} | {
        'sector': None, 'sector_status': 'unavailable', 'fundamental_period': None,
        'retrieved_at_ms': retrieved_at_ms, 'known_at_ms': retrieved_at_ms, 'source': 'moomoo-rest-basicinfo'}


def normalize_snapshot(row, retrieved_at_ms):
    code(row.get('code'))
    stamp = row.get('update_time')
    need(integer(stamp) and stamp <= retrieved_at_ms, 'invalid-source-time')
    need(iso_date(row.get('data_date')) <= datetime.fromtimestamp(retrieved_at_ms / 1000, timezone.utc).date(), 'invalid-source-date')
    output = {'code': row['code'], 'source_at_ms': stamp, 'session_date': row['data_date'],
              'retrieved_at_ms': retrieved_at_ms, 'known_at_ms': retrieved_at_ms, 'source': 'moomoo-rest-snapshot'}
    for name in ('last_price', 'prev_close_price', 'open_price', 'high_price', 'low_price'):
        output[name] = None if row.get(name) is None else numeric(row[name], positive=True)
    for name in ('volume', 'turnover'):
        output[name] = None if row.get(name) is None else numeric(row[name])
    for name in ('suspension', 'equity_valid', 'trust_valid'):
        need(name not in row or type(row[name]) is bool, 'invalid-snapshot')
        output[name] = row.get(name)
    output['sec_status'] = row.get('sec_status') if text(row.get('sec_status')) else None
    financial_periods = {'earning_per_share': 'previous-fiscal-year/end-unknown', 'net_profit': 'previous-fiscal-year/end-unknown',
        'pe_ttm_ratio': 'trailing-12-months/end-unknown', 'dividend_ttm': 'trailing-12-months/end-unknown',
        'dividend_ratio_ttm': 'trailing-12-months/end-unknown'}
    ratios = {'pe_ratio', 'pe_ttm_ratio', 'pb_ratio'}
    fields = {'total_market_val','circular_market_val','pe_ratio','pe_ttm_ratio','pb_ratio','earning_per_share',
              'net_profit','net_asset_per_share','dividend_ttm','dividend_ratio_ttm'}
    output['financial_metrics'] = {}
    for name in sorted(fields):
        value = row.get(name) if row.get('equity_valid') is True else None
        value = None if value is None else signed_numeric(value)
        output['financial_metrics'][name] = {'value': value, 'unit': 'ratio' if name in ratios else 'percentage-points' if name == 'dividend_ratio_ttm' else 'monetary/currency-unverified',
            'period': financial_periods.get(name, 'unknown'), 'currency': None,
            'status': 'available' if value is not None else 'unavailable', 'source_at_ms': stamp}
    for name in ('bid_price','ask_price','price_spread','bid_vol','ask_vol'):
        output[name] = None if row.get(name) is None else numeric(row[name])
    output.update(currency=None, native_bullish_count=None, native_bearish_count=None,
                  native_count_status='methodology-unverified', observation_kind='live-snapshot-not-completed-bar')
    return output


@dataclass(frozen=True)
class CurrencyEvidence:
    code: str
    currency: str
    source_url: str
    known_at_ms: int

    def __post_init__(self):
        code(self.code)
        need(self.currency == 'USD' and text(self.source_url, 2048) and self.source_url.startswith('https://')
             and integer(self.known_at_ms), 'invalid-currency-evidence')


def normalize_bar(row, *, security_code, start, end, retrieved_at_ms, volume_precision,
                  autype, vintage, currency_evidence=None, session_closes=None):
    code(security_code)
    need(isinstance(row, dict), 'invalid-ohlc')
    raw_date, stamp, offset = row.get('date'), row.get('time_key'), row.get('time_zone')
    need(integer(raw_date, 19000101, 21001231) and integer(stamp) and stamp <= retrieved_at_ms
         and type(offset) is int and -720 <= offset <= 840, 'invalid-history-time')
    failed = False
    try:
        day = date(raw_date // 10000, raw_date // 100 % 100, raw_date % 100)
        local_day = date(1970, 1, 1) + timedelta(days=(stamp + offset * 60000) // 86400000)
    except (ValueError, OverflowError):
        failed = True
    if failed:
        raise ContractError('invalid-history-time')
    need(day == local_day and iso_date(start) <= day <= iso_date(end), 'invalid-history-time')
    prices = {key: numeric(row.get(key), positive=True) for key in ('open', 'high', 'low', 'close')}
    need(prices['low'] <= min(prices['open'], prices['close']) <= max(prices['open'], prices['close']) <= prices['high'], 'invalid-ohlc-range')
    need(integer(volume_precision, 0, 18), 'volume-unit-unverified')
    need(integer(row.get('volume')), 'invalid-volume')
    volume = numeric(row.get('volume')) / 10**volume_precision
    turnover = numeric(row.get('turnover'))
    need(autype in (0, 1, 2) and type(autype) is int, 'adjustment-unverified')
    currency = None
    if currency_evidence is not None:
        need(isinstance(currency_evidence, CurrencyEvidence) and currency_evidence.code == security_code
             and currency_evidence.known_at_ms <= retrieved_at_ms, 'invalid-currency-evidence')
        currency = currency_evidence.currency
    close_at = (session_closes or {}).get(day.isoformat())
    need(close_at is None or integer(close_at) and stamp <= close_at, 'invalid-session-evidence')
    completed = close_at is not None and close_at <= retrieved_at_ms
    return {'code': security_code, 'session_date': day.isoformat(), **prices, 'volume': volume, 'turnover': turnover,
            'currency': currency, 'currency_source_url': currency_evidence.source_url if currency else None,
            'adjustment': {0: 'unadjusted', 1: 'forward-excluding-dividends', 2: 'back-excluding-dividends'}[autype],
            'source': 'moomoo-rest-history', 'source_at_ms': stamp, 'raw_time_key': stamp, 'raw_date': raw_date,
            'raw_time_zone': offset,
            'time_zone_unit_status': 'documented-minutes/runtime-unverified',
            'time_zone_unit_source_url': 'https://open.moomoo.com/zh-cn/api/quote/basic-data/history-kline',
            'provider_finality_status': 'unverified', 'retrieved_at_ms': retrieved_at_ms, 'known_at_ms': retrieved_at_ms,
            'revision_vintage': vintage, 'completed': completed,
            'completion_status': 'completed' if completed else 'not-completed' if close_at is not None else 'calendar-unverified',
            'volume_precision': volume_precision, 'native_bullish_count': None, 'native_bearish_count': None}


def history_coverage(rows, *, expected_sessions, cutoff_ms, minimum=252):
    """Explicit calendar membership, usable OHLC/units and actual known-time coverage."""
    need(integer(cutoff_ms) and integer(minimum, 1, 10000), 'invalid-coverage-input')
    if expected_sessions is None:
        return {'status': 'unverified', 'reason': 'calendar-coverage-unverified', 'sessions': 0}
    need(isinstance(expected_sessions, (list, tuple)) and len(set(expected_sessions)) == len(expected_sessions), 'invalid-coverage-input')
    for day in expected_sessions:
        iso_date(day)
    by_day = {row['session_date']: row for row in rows}
    need(len(by_day) == len(rows), 'duplicate-history-date')
    usable = {day for day, row in by_day.items() if row['completed'] and row['currency'] == 'USD'
              and row['known_at_ms'] <= cutoff_ms}
    missing = sorted(set(expected_sessions) - usable)
    complete = not missing and len(expected_sessions) >= minimum
    return {'status': 'complete' if complete else 'insufficient', 'reason': None if complete else 'required-session-coverage-missing',
            'sessions': len(usable & set(expected_sessions)), 'missing_sessions': missing}
