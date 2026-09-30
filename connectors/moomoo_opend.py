"""Read-only adapter for Moomoo OpenD quote and news APIs.

OpenD must be running and logged in separately. News search is request/response;
market quotes require a subscription before they can be read.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional


class OpenDUnavailableError(RuntimeError):
    """Raised when the optional Moomoo SDK or OpenD connection is unavailable."""


class OpenDAPIError(RuntimeError):
    """Raised when an OpenD API call returns a failure status."""


def _json_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # pandas/numpy scalar values expose item(); avoid importing pandas here.
    if hasattr(value, "item"):
        try:
            return _json_value(value.item())
        except (TypeError, ValueError):
            pass
    return str(value)


def _rows(data: Any) -> list[dict[str, Any]]:
    if hasattr(data, "to_dict"):
        try:
            data = data.to_dict(orient="records")
        except TypeError:
            data = data.to_dict()
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, (list, tuple)):
        raise OpenDAPIError("OpenD returned an unsupported response shape")
    return [_json_value(row) for row in data if isinstance(row, dict)]


class MoomooOpenDConnector:
    """Small, injectable, read-only client for OpenD market data."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        context_factory: Optional[Callable[..., Any]] = None,
        ret_ok: Optional[int] = None,
        quote_subtype: Any = None,
    ) -> None:
        self.host = host or os.getenv("MOOMOO_OPEND_HOST", "127.0.0.1")
        self.port = int(port or os.getenv("MOOMOO_OPEND_PORT", "11111"))
        self._context_factory = context_factory
        self._ret_ok = ret_ok
        self._quote_subtype = quote_subtype

    def _sdk(self) -> tuple[Callable[..., Any], int, Any]:
        if self._context_factory is not None:
            return (
                self._context_factory,
                self._ret_ok if self._ret_ok is not None else 0,
                self._quote_subtype or "QUOTE",
            )
        try:
            from moomoo import OpenQuoteContext, RET_OK, SubType
        except ImportError as exc:
            raise OpenDUnavailableError(
                "Moomoo SDK is missing; install moomoo-api and start OpenD"
            ) from exc
        return OpenQuoteContext, RET_OK, SubType.QUOTE

    @contextmanager
    def _connection(self) -> Iterator[tuple[Any, int, Any]]:
        factory, ret_ok, quote_subtype = self._sdk()
        context = None
        try:
            try:
                context = factory(host=self.host, port=self.port)
            except Exception as exc:
                raise OpenDUnavailableError(
                    f"Could not connect to Moomoo OpenD at {self.host}:{self.port}"
                ) from exc
            yield context, ret_ok, quote_subtype
        finally:
            if context is not None:
                context.close()

    @staticmethod
    def _check(result: Any, ret_ok: int, operation: str) -> Any:
        if not isinstance(result, tuple) or len(result) < 2:
            raise OpenDAPIError(f"OpenD returned an invalid {operation} response")
        status, data = result[0], result[1]
        if status != ret_ok:
            raise OpenDAPIError(f"OpenD {operation} failed: {data}")
        return data

    def search_news(self, keyword: str, max_count: int = 10) -> list[dict[str, Any]]:
        """Search Moomoo news/notices/ratings (request/response, not a push feed)."""
        with self._connection() as (context, ret_ok, _):
            data = self._check(
                context.get_search_news(keyword, max_count=max_count), ret_ok, "news search"
            )
            return _rows(data)

    def get_quotes(self, codes: list[str]) -> list[dict[str, Any]]:
        """Subscribe to quote data, fetch latest quote rows, then close the session."""
        with self._connection() as (context, ret_ok, quote_subtype):
            self._check(
                context.subscribe(
                    codes,
                    [quote_subtype],
                    is_first_push=False,
                    subscribe_push=False,
                ),
                ret_ok,
                "quote subscription",
            )
            data = self._check(context.get_stock_quote(codes), ret_ok, "quote lookup")
            return _rows(data)


def configured_connector() -> MoomooOpenDConnector:
    """Create one request-scoped client using the configured OpenD address."""
    return MoomooOpenDConnector()
