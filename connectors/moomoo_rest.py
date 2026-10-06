"""Injectable, memory-only Moomoo REST read protocol; no network implementation."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import date
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Mapping
from urllib.parse import urlencode

HOST = "https://webapi.moomoo.com"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class RESTError(RuntimeError):
    """Controlled errors never copy provider bodies or dependency exceptions."""
    def __init__(self, kind: str, retry_after: int | None = None):
        self.kind = kind
        self.retry_after = retry_after
        super().__init__(f"Moomoo REST {kind}")


@dataclass(frozen=True, repr=False)
class ReadRequest:
    method: str
    path: str
    query: str
    body: bytes
    headers: Mapping[str, str]
    timeout: float

    @property
    def url(self) -> str:
        return HOST + self.path + ("?" + self.query if self.query else "")

    def __repr__(self) -> str:
        return "<Moomoo ReadRequest>"


@dataclass(frozen=True, repr=False)
class ReadResponse:
    status: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)

    def __repr__(self) -> str:
        return "<Moomoo ReadResponse>"


@dataclass(frozen=True, repr=False)
class ReadResult:
    data: Any
    status: str
    requested_at_ms: int
    retrieved_at_ms: int
    endpoint: str
    private: bool
    provider_time_unit: str | None = None
    missing_codes: tuple[str, ...] = ()
    provider: str = "moomoo-rest"

    def __repr__(self) -> str:
        return "<Moomoo ReadResult>"


def _require(condition: bool, kind: str = "invalid-input") -> None:
    if not condition:
        raise RESTError(kind)


def _text(value: Any, maximum: int, *, empty: bool = False) -> bool:
    return (isinstance(value, str) and len(value) <= maximum
            and (empty or bool(value.strip()))
            and not any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF
                        for c in value))


def _date(value: Any) -> bool:
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _integer(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _invoke(fn: Callable, *args: Any, kind: str) -> Any:
    # Raise outside the except suite, so even __context__ cannot retain secrets.
    failure = None
    try:
        result = fn(*args)
    except TimeoutError:
        failure = "timeout" if kind == "transport-failed" else kind
    except Exception:
        failure = kind
    if failure is not None:
        raise RESTError(failure)
    return result


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _bad_constant(_: str) -> None:
    raise ValueError("nonfinite value")


def _decode(body: bytes) -> dict:
    failed = False
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_bad_constant)
        # Reject overflow such as 1e999 as well as literal NaN/Infinity.
        def finite(item: Any) -> bool:
            if isinstance(item, float):
                return math.isfinite(item)
            if isinstance(item, dict):
                return all(finite(v) for v in item.values())
            if isinstance(item, list):
                return all(finite(v) for v in item)
            return True
        failed = not isinstance(value, dict) or not finite(value)
    except Exception:
        failed = True
    if failed:
        raise RESTError("malformed-response")
    return value


def _decimal_string(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
        return False
    try:
        return Decimal(value).is_finite()
    except InvalidOperation:
        return False


def _retry_after(headers: Mapping[str, str], now_ms: int) -> int | None:
    # Bound all provider-controlled values; invalid hints are discarded.
    value = next((v for k, v in headers.items() if k.lower() == "retry-after"), None)
    if not isinstance(value, str) or len(value) > 128:
        return None
    seconds = None
    try:
        if re.fullmatch(r"\d{1,8}", value):
            seconds = int(value)
        else:
            date = parsedate_to_datetime(value)
            if date.tzinfo is not None:
                seconds = math.ceil(date.timestamp() - now_ms / 1000)
    except (ValueError, TypeError, OverflowError):
        pass
    return seconds if seconds is not None and 0 <= seconds <= 86400 else None


class MoomooRESTConnector:
    """Explicit semantic reads. Caller supplies every external capability.

    Transport receives ReadRequest and returns ReadResponse. It must honor the
    timeout; this synchronous core cannot interrupt an uncooperative callable.
    Signer receives canonical bytes and returns raw signature bytes.
    """
    def __init__(self, *, api_key: str, signer: Callable[[bytes], bytes],
                 transport: Callable[[ReadRequest], ReadResponse],
                 clock_ms: Callable[[], int], nonce_factory: Callable[[], str],
                 timeout: float = 10.0):
        _require(_text(api_key, 512) and api_key.isascii())
        _require(all(callable(x) for x in (signer, transport, clock_ms, nonce_factory)))
        _require(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 30)
        self._api_key, self._signer, self._transport = api_key, signer, transport
        self._clock_ms, self._nonce_factory, self._timeout = clock_ms, nonce_factory, timeout

    def __repr__(self) -> str:
        return "<MoomooRESTConnector>"

    def _clock(self) -> int:
        value = _invoke(self._clock_ms, kind="clock-failed")
        _require(_integer(value, 1, 2**63 - 1), "clock-failed")
        return value

    def _read(self, method: str, path: str, query: list, *, body: bytes = b"",
              account: bool = False) -> tuple[Any, int, int]:
        timestamp = self._clock()
        nonce = _invoke(self._nonce_factory, kind="nonce-failed")
        _require(isinstance(nonce, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", nonce) is not None,
                 "nonce-failed")
        raw_query = urlencode(query, encoding="utf-8", errors="strict")
        digest = hashlib.sha256(body).hexdigest() if body else ""
        canonical = "\n".join((str(timestamp), method, path, raw_query, digest)).encode("utf-8")
        signature = _invoke(self._signer, canonical, kind="signer-failed")
        _require(isinstance(signature, bytes) and 0 < len(signature) <= 4096, "signer-failed")
        headers = {"X-Api-Key": self._api_key,
                   "Authorization": base64.b64encode(signature).decode("ascii"),
                   "X-Timestamp": str(timestamp), "X-Nonce": nonce}
        if body:
            headers["Content-Type"] = "application/json"
        request = ReadRequest(method, path, raw_query, body, headers, self._timeout)
        response = _invoke(self._transport, request, kind="transport-failed")
        retrieved = self._clock()
        _require(retrieved >= timestamp, "clock-failed")
        _require(isinstance(response, ReadResponse) and _integer(response.status, 100, 599)
                 and isinstance(response.headers, Mapping)
                 and all(isinstance(k, str) and isinstance(v, str)
                         for k, v in response.headers.items()), "malformed-response")
        if response.status == 429:
            raise RESTError("rate-limited", _retry_after(response.headers, retrieved))
        if response.status >= 500:
            raise RESTError("upstream-failed")
        if response.status != 200:
            raise RESTError("http-failed")
        _require(isinstance(response.body, bytes) and len(response.body) <= MAX_RESPONSE_BYTES,
                 "malformed-response")
        payload = _decode(response.body)
        if account:
            _require("ret_code" not in payload and payload.get("s") in ("ok", "error"),
                     "malformed-response")
            if payload["s"] == "error":
                _require(type(payload.get("errcode")) is int, "malformed-response")
                raise RESTError("provider-failed")
            _require("d" in payload and "errcode" not in payload, "malformed-response")
            data = payload["d"]
        else:
            _require("s" not in payload and type(payload.get("ret_code")) is int
                     and isinstance(payload.get("ret_msg"), str), "malformed-response")
            if payload["ret_code"] != 0:
                raise RESTError("provider-failed")
            _require("data" in payload, "malformed-response")
            data = payload["data"]
        return data, timestamp, retrieved

    @staticmethod
    def _rows(data: Any, key: str | None = None) -> list:
        if key is not None:
            _require(isinstance(data, dict) and key in data, "malformed-response")
            data = data[key]
        _require(isinstance(data, list) and all(isinstance(row, dict) for row in data),
                 "malformed-response")
        return data

    @staticmethod
    def _identifiers(rows: list, key: str) -> None:
        seen = set()
        for row in rows:
            identifier = row.get(key)
            _require(_text(identifier, 512) and identifier not in seen, "malformed-response")
            seen.add(identifier)

    @staticmethod
    def _result(data: Any, started: int, ended: int, endpoint: str, *,
                private: bool = False, unit: str | None = None,
                missing: tuple[str, ...] = ()) -> ReadResult:
        status = "empty" if not data else ("partial" if missing else "success")
        return ReadResult(data, status, started, ended, endpoint, private, unit, missing)

    def search_news(self, keyword: str, size: int = 10, *, news_type: int | None = None,
                    sort_type: int | None = None, lang: str | None = None) -> ReadResult:
        _require(_text(keyword, 512) and _integer(size, 1, 50))
        _require(news_type is None or _integer(news_type, 1, 3))
        _require(sort_type is None or _integer(sort_type, 1, 2))
        _require(lang is None or lang in ("zh-CN", "zh-HK", "en", "ja"))
        query = [("symbol", keyword), ("size", size)]
        query += [(k, v) for k, v in (("news_type", news_type), ("sort_type", sort_type),
                                     ("lang", lang)) if v is not None]
        data, start, end = self._read("GET", "/api/v1.0/quote/find-news", query)
        rows = self._rows(data)
        _require(len(rows) <= size, "malformed-response")
        self._identifiers(rows, "news_id")
        for row in rows:
            _require(row.get("news_type") in ("POST", "NOTICE", "REPORT")
                     and isinstance(row.get("title"), str)
                     and _integer(row.get("publish_time"), 0, 2**63 - 1)
                     and _text(row.get("url"), 8192), "malformed-response")
            if "img_url" in row:
                _require(isinstance(row["img_url"], str), "malformed-response")
        # Titles remain literal strings, never interpreted as HTML.
        return self._result(rows, start, end, "find-news", unit="seconds")

    def snapshot(self, codes: list[str] | tuple[str, ...]) -> ReadResult:
        _require(isinstance(codes, (list, tuple)) and 1 <= len(codes) <= 400)
        _require(all(isinstance(c, str) and len(c) <= 64
                     and re.fullmatch(r"US\.[A-Z][A-Z0-9.-]*", c) for c in codes))
        _require(len(set(codes)) == len(codes))
        body = json.dumps({"code_list": list(codes)}, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8")
        data, start, end = self._read("POST", "/api/v1.0/quote/snapshot", [], body=body)
        rows = self._rows(data, "snapshot_list")
        self._identifiers(rows, "code")
        returned = {row["code"] for row in rows}
        _require(returned.issubset(codes), "malformed-response")
        for row in rows:
            _require(_text(row.get("name"), 512)
                     and _integer(row.get("update_time"), 0, 2**63 - 1)
                     and _date(row.get("data_date")),
                     "malformed-response")
            for key, value in row.items():
                if key.endswith("_valid"):
                    _require(type(value) is bool, "malformed-response")
            for key in ("last_price", "open_price", "high_price", "low_price",
                        "prev_close_price", "turnover", "turnover_rate"):
                if key in row:
                    _require(type(row[key]) in (int, float), "malformed-response")
            if "volume" in row:
                _require(_integer(row["volume"], 0, 2**63 - 1), "malformed-response")
        missing = tuple(code for code in codes if code not in returned)
        return self._result(rows, start, end, "snapshot", unit="milliseconds", missing=missing)

    def history_kline(self, code: str, end: str, *, start: str | None = None,
                      num: int = 100, ktype: int = 2, autype: int = 0) -> ReadResult:
        """Read bounded US daily K-lines; no account or order capability is used."""
        _require(isinstance(code, str) and re.fullmatch(r"US\.[A-Z][A-Z0-9.-]*", code) is not None)
        _require(_date(end) and (start is None or _date(start) and start <= end))
        _require(_integer(num, 1, 370) and _integer(ktype, 2, 2)
                 and _integer(autype, 0, 2))
        query = [("end", end), ("ktype", ktype), ("autype", autype), ("num", num)]
        if start is not None:
            query.insert(0, ("start", start))
        path = f"/api/v1.0/quote/{code}/history-kline"
        data, requested, retrieved = self._read("GET", path, query)
        _require(isinstance(data, dict) and "kline_list" in data
                 and set(data) <= {"kline_list", "next_time", "volume_precision"},
                 "malformed-response")
        rows = self._rows(data, "kline_list")
        _require(len(rows) <= num, "malformed-response")
        dates, times = set(), set()
        for row in rows:
            stamp, market_date, zone = row.get("time_key"), row.get("date"), row.get("time_zone")
            _require(_integer(stamp, 0, 2**63 - 1)
                     and _integer(market_date, 19000101, 21001231)
                     and type(zone) is int and -720 <= zone <= 840, "malformed-response")
            try:
                parsed = date.fromisoformat(f"{market_date // 10000:04d}-{market_date // 100 % 100:02d}-{market_date % 100:02d}")
            except ValueError:
                raise RESTError("malformed-response") from None
            _require(parsed.strftime("%Y%m%d") == f"{market_date:08d}"
                     and (start is None or parsed.isoformat() >= start),
                     "malformed-response")
            _require(parsed.isoformat() <= end and stamp not in times and parsed not in dates,
                     "malformed-response")
            dates.add(parsed);times.add(stamp)
            _require(type(row.get("close")) in (int, float)
                     and math.isfinite(row["close"]) and row["close"] > 0,
                     "malformed-response")
            for key in ("open", "high", "low", "last_close", "turnover", "turnover_rate",
                        "change_rate", "pe_ratio"):
                if key in row:
                    _require(type(row[key]) in (int, float) and math.isfinite(row[key]),
                             "malformed-response")
            if "volume" in row:
                _require(_integer(row["volume"], 0, 2**63 - 1), "malformed-response")
        for key in ("next_time",):
            if key in data:
                _require(_integer(data[key], 0, 2**63 - 1), "malformed-response")
        if "volume_precision" in data:
            _require(_integer(data["volume_precision"], 0, 18), "malformed-response")
        return self._result(rows, requested, retrieved, "history-kline", unit="milliseconds")

    @staticmethod
    def _account_id(account_id: str) -> str:
        _require(isinstance(account_id, str) and re.fullmatch(r"\d{1,64}", account_id,
                                                            flags=re.ASCII) is not None)
        return account_id

    def account_funds(self, account_id: str, currency: str) -> ReadResult:
        account_id = self._account_id(account_id)
        _require(isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency) is not None)
        data, start, end = self._read("GET", f"/api/v1.0/accounts/{account_id}/funds",
                                     [("currency", currency)], account=True)
        _require(isinstance(data, dict), "malformed-response")
        # Funds objects contain monetary decimal strings, currency and risk_status.
        for key, value in data.items():
            _require(isinstance(value, str) if key in ("currency", "risk_status")
                     else _decimal_string(value), "malformed-response")
        return self._result(data, start, end, "funds", private=True)

    def positions(self, account_id: str) -> ReadResult:
        account_id = self._account_id(account_id)
        data, start, end = self._read("GET", f"/api/v1.0/accounts/{account_id}/positions", [],
                                     account=True)
        rows = self._rows(data)
        numeric = ("qty", "can_sell_qty", "nominal_price", "cost_price", "market_val",
                   "pl_ratio", "pl_val", "today_pl_val", "today_trd_val", "today_buy_qty",
                   "today_buy_val", "today_sell_qty", "today_sell_val", "unrealized_pl", "realized_pl")
        for row in rows:
            _require(_text(row.get("code"), 512)
                     and row.get("position_side") in ("LONG", "SHORT", "NONE"), "malformed-response")
            for key in numeric:
                if key in row:
                    _require(_decimal_string(row[key]), "malformed-response")
            for key in ("cost_price_valid", "pl_ratio_valid", "pl_val_valid"):
                if key in row:
                    _require(type(row[key]) is bool, "malformed-response")
            for key in ("stock_name", "currency"):
                if key in row:
                    _require(isinstance(row[key], str), "malformed-response")
        return self._result(rows, start, end, "positions", private=True)

    def list_groups(self, group_type: str = "ALL") -> ReadResult:
        _require(group_type in ("ALL", "SYSTEM", "CUSTOM"))
        data, start, end = self._read("GET", "/api/v1.0/quote/user-security-group",
                                     [("group_type", group_type)])
        rows = self._rows(data, "group_list")
        self._identifiers(rows, "group_name")
        for row in rows:
            _require(_text(row["group_name"], 100)
                     and row.get("group_type") in ("SYSTEM", "CUSTOM")
                     and (group_type == "ALL" or row["group_type"] == group_type), "malformed-response")
        return self._result(rows, start, end, "user-security-group", private=True)

    def list_group_members(self, group_name: str) -> ReadResult:
        _require(_text(group_name, 100))
        data, start, end = self._read("GET", "/api/v1.0/quote/user-security", [("group_name", group_name)])
        rows = self._rows(data, "security_list")
        self._identifiers(rows, "code")
        for row in rows:
            _require(_text(row.get("name"), 512), "malformed-response")
            for key in ("lot_size", "stock_child_type", "stock_id"):
                if key in row:
                    _require(_integer(row[key], 0, 2**63 - 1), "malformed-response")
            if "main_contract" in row:
                _require(type(row["main_contract"]) is bool, "malformed-response")
            if "strike_price" in row:
                _require(type(row["strike_price"]) in (int, float), "malformed-response")
            for key in ("sc_name", "tc_name", "stock_type", "stock_owner", "option_type",
                        "strike_time", "listing_date", "last_trade_time"):
                if key in row:
                    _require(isinstance(row[key], str), "malformed-response")
        return self._result(rows, start, end, "user-security", private=True)
