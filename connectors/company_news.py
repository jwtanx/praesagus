"""Earliest company news connector for buy/short signal generation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterator, List, Optional
from urllib.parse import quote_plus

import feedparser

from connectors.base import NormalizedRecord, RawRecord
from connectors.financial.schemas import NEWS_FILTER_FIELDS, NewsRecord, TradeSignal
from connectors.financial.signals import classify_news_signal, extract_tickers
from connectors.financial.storage import upsert_records


class CompanyNewsConnector:
    """Fetch earliest company news from Google News RSS and SEC 8-K atom feeds."""

    def __init__(
        self,
        tickers: Optional[List[str]] = None,
        company_names: Optional[List[str]] = None,
        include_sec_8k: bool = True,
        max_items_per_source: int = 25,
        locale: str = "en-US",
    ):
        self.tickers = [t.upper() for t in (tickers or [])]
        self.company_names = company_names or []
        self.include_sec_8k = include_sec_8k
        self.max_items_per_source = max_items_per_source
        self.locale = locale

    def authenticate(self) -> None:
        return None

    def discover(self) -> list[dict]:
        return [{"tickers": self.tickers, "company_names": self.company_names}]

    def _google_news_url(self, query: str) -> str:
        encoded = quote_plus(query)
        return (
            f"https://news.google.com/rss/search?q={encoded}"
            f"&hl={self.locale}&gl=US&ceid=US:en"
        )

    def _parse_feed_entries(self, feed_url: str, source_name: str, default_ticker: str = "") -> Iterator[dict]:
        feed = feedparser.parse(feed_url)
        now = datetime.utcnow()
        for entry in feed.entries[: self.max_items_per_source]:
            title = getattr(entry, "title", "") or ""
            summary = getattr(entry, "summary", "") or ""
            link = getattr(entry, "link", "") or ""
            published = getattr(entry, "published", "") or getattr(entry, "updated", "")
            published_dt = now
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_dt = datetime(*entry.published_parsed[:6])
            source_id = hashlib.sha256(f"{source_name}:{link}:{title}".encode()).hexdigest()[:24]
            latency_ms = max(0.0, (now - published_dt).total_seconds() * 1000)
            tickers = extract_tickers(f"{title} {summary}", self.tickers) or ([default_ticker] if default_ticker else [])
            yield {
                "source_id": source_id,
                "ticker": tickers[0] if tickers else default_ticker,
                "related_tickers": tickers,
                "title": title,
                "summary": summary,
                "link": link,
                "source_name": source_name,
                "published_at": published_dt.isoformat() + "Z",
                "first_seen_at": now.isoformat() + "Z",
                "latency_ms": latency_ms,
            }

    def fetch(
        self,
        start: datetime,
        end: datetime,
        cursor: Optional[str] = None,
    ) -> Iterator[RawRecord]:
        seen_links = set()

        def in_window(item: dict) -> bool:
            try:
                published = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            except (KeyError, TypeError, ValueError):
                return False
            return start <= published <= end

        for ticker in self.tickers:
            queries = [f"{ticker} stock", f"{ticker} earnings", f"{ticker} SEC"]
            for query in queries:
                url = self._google_news_url(query)
                for item in self._parse_feed_entries(url, "google_news", default_ticker=ticker):
                    if item["link"] in seen_links:
                        continue
                    seen_links.add(item["link"])
                    if not in_window(item):
                        continue
                    yield RawRecord(payload=item)

        for idx, name in enumerate(self.company_names):
            ticker = self.tickers[idx] if idx < len(self.tickers) else ""
            url = self._google_news_url(f'"{name}" stock')
            for item in self._parse_feed_entries(url, "google_news", default_ticker=ticker):
                if item["link"] in seen_links:
                    continue
                seen_links.add(item["link"])
                if in_window(item):
                    yield RawRecord(payload=item)

        if self.include_sec_8k:
            sec_url = (
                "https://www.sec.gov/cgi-bin/browse-edgar"
                "?action=getcurrent&type=8-K&company=&dateb=&owner=include&count=100&output=atom"
            )
            for item in self._parse_feed_entries(sec_url, "sec_8k"):
                if item["link"] in seen_links:
                    continue
                seen_links.add(item["link"])
                if in_window(item):
                    yield RawRecord(payload=item)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        signal, strength, keywords, reason = classify_news_signal(p.get("title", ""), p.get("summary", ""))
        record = NewsRecord(
            source_id=p["source_id"],
            ticker=p.get("ticker", ""),
            company_name=p.get("company_name", ""),
            title=p.get("title", ""),
            summary=p.get("summary", ""),
            link=p.get("link", ""),
            source_name=p.get("source_name", ""),
            published_at=p.get("published_at", ""),
            first_seen_at=p.get("first_seen_at", datetime.utcnow().isoformat() + "Z"),
            latency_ms=float(p.get("latency_ms") or 0),
            keywords_matched=keywords,
            signal=signal,
            signal_strength=strength,
            signal_reason=reason,
            categories=["material_event"] if p.get("source_name") == "sec_8k" else ["news"],
            related_tickers=p.get("related_tickers", []),
        )
        metadata = record.to_dict()
        metadata["investable_fields"] = NEWS_FILTER_FIELDS
        return NormalizedRecord(
            source="company_news",
            source_id=record.source_id,
            timestamp=datetime.utcnow(),
            text=f"{record.title} [{record.signal.value}]",
            entities=[{"type": "ticker", "value": t} for t in record.related_tickers or ([record.ticker] if record.ticker else [])],
            metadata=metadata,
            provenance={"connector": "company_news", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(
        self,
        raw: RawRecord,
        normalized: NormalizedRecord,
        s3_bucket: Optional[str] = None,
        s3_writer=None,
        data_dir=None,
    ) -> dict:
        record = normalized.metadata
        merged = upsert_records("news", [record], data_dir=data_dir)
        result = {"stored": len(merged), "source_id": record.get("source_id"), "signal": record.get("signal")}
        if s3_bucket and s3_writer:
            from connectors.financial.storage import store_to_s3

            uri = store_to_s3(s3_bucket, "news", merged, s3_writer=s3_writer)
            result["s3_uri"] = uri
        return result

    def monitor(self) -> dict:
        return {"status": "ok", "tickers": self.tickers}
