#!/usr/bin/env python3
"""Sync financial calendar (earnings, SEC filings, macro events) for dashboard."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from connectors.financial.storage import get_data_dir
from connectors.financial_calendar import FinancialCalendarConnector
from connectors.utils import s3_atomic_write

DEFAULT_WATCHLIST = ROOT / "ingest" / "config" / "financial_watchlist.yaml"


def load_watchlist(path: Path) -> dict:
    if not path.exists():
        return {"watchlist": [], "settings": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build financial calendar from SEC filings and macro schedule.")
    parser.add_argument("--tickers", nargs="+", help="Ticker symbols")
    parser.add_argument("--horizon-days", type=int, default=90, help="Forward calendar horizon")
    parser.add_argument("--days-back", type=int, default=30, help="Include past events window")
    parser.add_argument("--no-macro", action="store_true", help="Exclude macro events (FOMC, CPI)")
    parser.add_argument("--watchlist", default=str(DEFAULT_WATCHLIST))
    parser.add_argument("--s3-bucket", default=os.getenv("PRAESAGUS_S3_BUCKET"))
    parser.add_argument("--user-agent", default=None)
    args = parser.parse_args()

    config = load_watchlist(Path(args.watchlist))
    settings = config.get("settings", {})
    tickers = args.tickers or [item["ticker"] for item in config.get("watchlist", [])]
    user_agent = args.user_agent or settings.get("sec_user_agent") or os.getenv("SEC_USER_AGENT")

    end = datetime.utcnow() + timedelta(days=args.horizon_days)
    start = datetime.utcnow() - timedelta(days=args.days_back)

    connector = FinancialCalendarConnector(
        tickers=tickers,
        include_macro=not args.no_macro,
        horizon_days=args.horizon_days,
        user_agent=user_agent,
    )
    connector.authenticate()
    data_dir = get_data_dir()
    count = 0
    print(f"Building calendar for {tickers}, {args.days_back}d back / {args.horizon_days}d forward")
    for raw in connector.fetch(start, end):
        normalized = connector.normalize(raw)
        connector.store(
            raw,
            normalized,
            s3_bucket=args.s3_bucket,
            s3_writer=s3_atomic_write if args.s3_bucket else None,
            data_dir=data_dir,
        )
        meta = normalized.metadata
        print(
            f"  [{meta.get('event_type')}] {meta.get('event_date')} "
            f"{meta.get('ticker') or 'MACRO'} — {meta.get('title')}"
        )
        count += 1
    print(f"Done. Stored {count} calendar events to {data_dir / 'calendar.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
