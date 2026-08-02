#!/usr/bin/env python3
"""Real-time SEC Form 4 insider trading monitor with first-second alerts."""

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

from alerting.financial_alerts import send_insider_alert
from connectors.financial.storage import get_data_dir, load_dataset
from connectors.sec_form4_insider import SecForm4InsiderConnector
from connectors.utils import s3_atomic_write

DEFAULT_WATCHLIST = ROOT / "ingest" / "config" / "financial_watchlist.yaml"


def load_watchlist(path: Path) -> dict:
    if not path.exists():
        return {"watchlist": [], "settings": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_once(connector, start, end, s3_bucket, data_dir, alert_webhook, min_value, seen_ids):
    new_count = 0
    for raw in connector.fetch(start, end):
        normalized = connector.normalize(raw)
        source_id = normalized.source_id
        if source_id in seen_ids:
            continue
        seen_ids.add(source_id)
        connector.store(
            raw,
            normalized,
            s3_bucket=s3_bucket,
            s3_writer=s3_atomic_write if s3_bucket else None,
            data_dir=data_dir,
        )
        meta = normalized.metadata
        print(
            f"[INSIDER] {meta.get('acceptance_datetime')} {meta.get('ticker')} "
            f"{meta.get('reporting_owner_name')} {meta.get('transaction_code_label')} "
            f"{meta.get('shares')} @ ${meta.get('price_per_share')} "
            f"signal={meta.get('signal')} latency={meta.get('latency_seconds')}s"
        )
        if alert_webhook:
            send_insider_alert(alert_webhook, meta)
        new_count += 1
    return new_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor SEC Form 4 insider trades in near real-time.")
    parser.add_argument("--tickers", nargs="+", help="Limit to tickers (default: watchlist)")
    parser.add_argument("--watch-all", action="store_true", help="Monitor all Form 4 filings")
    parser.add_argument("--poll-interval", type=int, default=30, help="Poll interval seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--atom-count", type=int, default=100, help="Form 4 atom feed count")
    parser.add_argument("--min-value", type=float, default=100_000, help="Min transaction value for alerts")
    parser.add_argument("--watchlist", default=str(DEFAULT_WATCHLIST))
    parser.add_argument("--s3-bucket", default=os.getenv("PRAESAGUS_S3_BUCKET"))
    parser.add_argument("--user-agent", default=None)
    args = parser.parse_args()

    config = load_watchlist(Path(args.watchlist))
    settings = config.get("settings", {})
    tickers = args.tickers or [item["ticker"] for item in config.get("watchlist", [])]
    poll_interval = args.poll_interval or settings.get("insider_poll_interval_seconds", 30)
    min_value = args.min_value or settings.get("min_insider_transaction_value", 100_000)
    user_agent = args.user_agent or settings.get("sec_user_agent") or os.getenv("SEC_USER_AGENT")
    alert_webhook = os.getenv("PRAESAGUS_ALERT_WEBHOOK")

    connector = SecForm4InsiderConnector(
        tickers=tickers if not args.watch_all else None,
        watch_all=args.watch_all,
        atom_count=args.atom_count,
        min_transaction_value=min_value,
        user_agent=user_agent,
    )
    connector.authenticate()
    data_dir = get_data_dir()
    seen_ids = {r.get("source_id") for r in load_dataset("insider_trades", data_dir)}

    print(f"Insider monitor started. Tickers={tickers or 'ALL'} poll={poll_interval}s min_value=${min_value:,.0f}")
    while True:
        end = datetime.utcnow()
        start = end - timedelta(hours=24)
        new_count = run_once(connector, start, end, args.s3_bucket, data_dir, alert_webhook, min_value, seen_ids)
        if new_count:
            print(f"  -> {new_count} new insider trade(s)")
        if args.once:
            break
        time.sleep(poll_interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
