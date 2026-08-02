#!/usr/bin/env python3
"""Automate SEC quarterly/annual report (10-Q, 10-K, 8-K) ingestion from EDGAR."""

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
from connectors.sec_filings import SecFilingsConnector
from connectors.utils import s3_atomic_write

DEFAULT_WATCHLIST = ROOT / "ingest" / "config" / "financial_watchlist.yaml"


def load_watchlist(path: Path) -> dict:
    if not path.exists():
        return {"watchlist": [], "settings": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch SEC filings (10-Q quarterly reports, 10-K, 8-K) from EDGAR REST API."
    )
    parser.add_argument("--tickers", nargs="+", help="Ticker symbols (overrides watchlist)")
    parser.add_argument("--ciks", nargs="+", help="CIK numbers")
    parser.add_argument("--forms", nargs="+", default=["10-Q", "10-K", "8-K"], help="Form types")
    parser.add_argument("--limit", type=int, default=20, help="Max filings per company")
    parser.add_argument("--days", type=int, default=365, help="Lookback window in days")
    parser.add_argument("--watchlist", default=str(DEFAULT_WATCHLIST), help="Watchlist YAML path")
    parser.add_argument("--s3-bucket", default=os.getenv("PRAESAGUS_S3_BUCKET"), help="Optional S3 bucket")
    parser.add_argument("--no-metrics", action="store_true", help="Skip XBRL metrics extraction")
    parser.add_argument("--user-agent", default=None, help="SEC User-Agent (required by SEC fair access policy)")
    args = parser.parse_args()

    config = load_watchlist(Path(args.watchlist))
    settings = config.get("settings", {})
    tickers = args.tickers or [item["ticker"] for item in config.get("watchlist", [])]
    if not tickers and not args.ciks:
        print("Error: provide --tickers, --ciks, or a watchlist with tickers.", file=sys.stderr)
        return 1

    user_agent = args.user_agent or settings.get("sec_user_agent") or os.getenv("SEC_USER_AGENT")
    end = datetime.utcnow()
    start = end - timedelta(days=args.days)

    connector = SecFilingsConnector(
        tickers=tickers,
        ciks=args.ciks,
        form_types=args.forms,
        limit_per_company=args.limit,
        user_agent=user_agent,
        include_metrics=not args.no_metrics,
    )
    connector.authenticate()
    data_dir = get_data_dir()
    count = 0
    print(f"Ingesting SEC filings for {len(tickers)} tickers ({args.forms}), lookback={args.days}d")
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
            f"  [{meta.get('form_type')}] {meta.get('ticker')} {meta.get('company_name')} "
            f"filed {meta.get('filing_date')} accession={meta.get('accession_number')}"
        )
        count += 1
    print(f"Done. Stored {count} filing records to {data_dir / 'filings.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
