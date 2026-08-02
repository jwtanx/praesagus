#!/usr/bin/env python3
"""Real-time watcher for new SEC QR filings with terminal buy/short signals.

This script polls the SEC EDGAR current filings feed for 10-Q and 10-K filings,
logs new filings, and classifies each filing into a basic buy/short/watch signal
based on keywords in the filing description and form type.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import feedparser
from connectors.financial.sec_client import SecEdgarClient
from connectors.financial.signals import BULLISH_KEYWORDS, BEARISH_KEYWORDS, TradeSignal

STATE_DIR = Path(".state")
STATE_DIR.mkdir(exist_ok=True)

DEFAULT_USER_AGENT = "Praesagus FinancialBot contact@praesagus.example"
DEFAULT_FORM_TYPES = ["10-Q", "10-K"]


def load_seen_accessions() -> Dict[str, str]:
    path = STATE_DIR / "realtime_qr_seen.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_seen_accessions(data: Dict[str, str]) -> None:
    path = STATE_DIR / "realtime_qr_seen.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def classify_filing_signal(form_type: str, title: str, summary: str) -> TradeSignal:
    text = f"{form_type} {title} {summary}".lower()
    bullish = [k for k in BULLISH_KEYWORDS if k in text]
    bearish = [k for k in BEARISH_KEYWORDS if k in text]
    if bullish and not bearish:
        return TradeSignal.BUY
    if bearish and not bullish:
        return TradeSignal.SHORT
    if bullish and bearish:
        return TradeSignal.WATCH
    return TradeSignal.WATCH


def parse_atom_entries(atom_feed: Dict[str, List]) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    for entry in atom_feed.get("entries", []):
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        link = entry.get("link", "")
        accession = entry.get("accession_number") or entry.get("accession") or ""
        updated = entry.get("updated") or entry.get("published") or ""
        entries.append({"title": title, "summary": summary, "link": link, "accession": accession, "updated": updated})
    return entries


def fetch_current_filings(client: SecEdgarClient, count: int = 100) -> List[Dict[str, str]]:
    url = (
        "https://www.sec.gov/cgi-bin/browse-edgar"
        f"?action=getcurrent&type=10-Q&company=&dateb=&owner=include&count={count}&output=atom"
    )
    resp = client.session.get(url, timeout=30)
    resp.raise_for_status()
    feed = __import__("feedparser").parse(resp.text)
    return parse_atom_entries({"entries": [dict(entry) for entry in feed.entries]})


def build_filings_for_types(client: SecEdgarClient, forms: List[str], count: int) -> List[Dict[str, str]]:
    filings: List[Dict[str, str]] = []
    for form in forms:
        url = (
            "https://www.sec.gov/cgi-bin/browse-edgar"
            f"?action=getcurrent&type={form}&company=&dateb=&owner=include&count={count}&output=atom"
        )
        resp = client.session.get(url, timeout=30)
        resp.raise_for_status()
        feed = __import__("feedparser").parse(resp.text)
        filings.extend(parse_atom_entries({"entries": [dict(entry) for entry in feed.entries]}))
    return filings


def normalized_accession(entry: Dict[str, str]) -> str:
    accession = entry.get("accession", "") or entry.get("link", "")
    return accession.strip().split("/")[-2] if "/" in accession else accession


def run_watcher(forms: List[str], poll_interval: int, lookback_minutes: int, user_agent: Optional[str]) -> None:
    client = SecEdgarClient(user_agent=user_agent)
    seen = load_seen_accessions()
    print(f"Realtime QR watcher started: forms={forms} poll_interval={poll_interval}s lookback={lookback_minutes}m")
    while True:
        try:
            filings = build_filings_for_types(client, forms, count=100)
            now = datetime.utcnow()
            new_found = 0
            for entry in filings:
                accession = normalized_accession(entry)
                if not accession or accession in seen:
                    continue
                updated = entry.get("updated", "")
                updated_ts = None
                try:
                    updated_ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                except Exception:
                    updated_ts = now
                if lookback_minutes and (now - updated_ts) > timedelta(minutes=lookback_minutes):
                    continue
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                signal = classify_filing_signal(entry.get("link", ""), title, summary)
                ticker = "UNKNOWN"
                if "(" in title and ")" in title:
                    ticker = title.split("(")[-1].split(")")[0].strip()
                print(
                    f"[{datetime.utcnow().isoformat()}] {signal.value.upper()} {ticker} {entry.get('title')}"
                )
                print(f"  accession={accession} link={entry.get('link')}")
                print(f"  summary={summary[:200]}")
                seen[accession] = datetime.utcnow().isoformat()
                new_found += 1
            if new_found:
                save_seen_accessions(seen)
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("Realtime QR watcher stopped by user.")
            break
        except Exception as exc:
            print("Watcher error:", exc)
            time.sleep(poll_interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch SEC EDGAR for latest QR filings and log buy/short signals.")
    parser.add_argument("--poll-interval", type=int, default=60, help="Seconds between polls")
    parser.add_argument("--lookback-minutes", type=int, default=60, help="Ignore filings older than this many minutes")
    parser.add_argument("--forms", nargs="+", default=DEFAULT_FORM_TYPES, help="SEC forms to watch")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="SEC User-Agent header")
    args = parser.parse_args()

    run_watcher(forms=args.forms, poll_interval=args.poll_interval, lookback_minutes=args.lookback_minutes, user_agent=args.user_agent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
