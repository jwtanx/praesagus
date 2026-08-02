#!/usr/bin/env python3
"""Fetch earliest company news for buy/short signal generation."""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alerting.financial_alerts import send_news_alert
from connectors.company_news import CompanyNewsConnector
from connectors.financial.storage import get_data_dir, load_dataset
from connectors.utils import s3_atomic_write

DEFAULT_WATCHLIST = ROOT / "ingest" / "config" / "financial_watchlist.yaml"


def load_watchlist(path: Path) -> dict:
    if not path.exists():
        return {"watchlist": [], "settings": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_fetch(connector, start, end, s3_bucket, data_dir, alert_webhook, seen_ids):
    new_count = 0
    for raw in connector.fetch(start, end):
        normalized = connector.normalize(raw)
        if normalized.source_id in seen_ids:
            continue
        seen_ids.add(normalized.source_id)
        connector.store(
            raw,
            normalized,
            s3_bucket=s3_bucket,
            s3_writer=s3_atomic_write if s3_bucket else None,
            data_dir=data_dir,
        )
        meta = normalized.metadata
        print(
            f"[NEWS] {meta.get('published_at')} {meta.get('ticker')} "
            f"signal={meta.get('signal')} strength={meta.get('signal_strength')} "
            f"latency={meta.get('latency_ms')}ms | {meta.get('title')[:80]}"
        )
        if alert_webhook and meta.get("signal") in {"buy", "short"}:
            send_news_alert(alert_webhook, meta)
        new_count += 1
    return new_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest earliest company news for trading signals.")
    parser.add_argument("--tickers", nargs="+", help="Ticker symbols")
    parser.add_argument("--hours", type=int, default=24, help="Lookback hours")
    parser.add_argument("--poll-interval", type=int, default=60, help="Poll interval (continuous mode)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--no-sec-8k", action="store_true", help="Skip SEC 8-K atom feed")
    parser.add_argument("--watchlist", default=str(DEFAULT_WATCHLIST))
    parser.add_argument("--s3-bucket", default=os.getenv("PRAESAGUS_S3_BUCKET"))
    args = parser.parse_args()

    config = load_watchlist(Path(args.watchlist))
    watchlist = config.get("watchlist", [])
    settings = config.get("settings", {})
    tickers = args.tickers or [item["ticker"] for item in watchlist]
    company_names = [item.get("company_name", "") for item in watchlist if item.get("company_name")]
    if not tickers:
        print("Error: provide --tickers or configure watchlist.", file=sys.stderr)
        return 1

    poll_interval = args.poll_interval or settings.get("news_poll_interval_seconds", 60)
    connector = CompanyNewsConnector(
        tickers=tickers,
        company_names=company_names[: len(tickers)],
        include_sec_8k=not args.no_sec_8k,
    )
    data_dir = get_data_dir()
    seen_ids = {r.get("source_id") for r in load_dataset("news", data_dir)}
    alert_webhook = os.getenv("PRAESAGUS_ALERT_WEBHOOK")

    print(f"News monitor started for {tickers}")
    while True:
        end = datetime.utcnow()
        start = end - timedelta(hours=args.hours)
        new_count = run_fetch(connector, start, end, args.s3_bucket, data_dir, alert_webhook, seen_ids)
        if new_count:
            print(f"  -> {new_count} new article(s)")
        if args.once:
            break
        time.sleep(poll_interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
