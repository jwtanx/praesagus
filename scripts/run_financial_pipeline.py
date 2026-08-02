#!/usr/bin/env python3
"""Master pipeline: SEC filings + insider monitor + news + financial calendar."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_script(name: str, extra_args: list[str]) -> int:
    cmd = [sys.executable, str(SCRIPTS / name), *extra_args]
    print(f"\n=== Running {name} ===")
    result = subprocess.run(cmd, cwd=str(ROOT))
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full financial intelligence pipeline.")
    parser.add_argument("--watchlist", default=str(ROOT / "ingest" / "config" / "financial_watchlist.yaml"))
    parser.add_argument("--skip-filings", action="store_true")
    parser.add_argument("--skip-insider", action="store_true")
    parser.add_argument("--skip-news", action="store_true")
    parser.add_argument("--skip-calendar", action="store_true")
    parser.add_argument("--continuous", action="store_true", help="Run insider+news in loop (delegates to monitors)")
    args = parser.parse_args()

    common = ["--watchlist", args.watchlist]
    exit_code = 0

    if not args.skip_filings:
        exit_code |= run_script("run_sec_filings.py", common + ["--days", "365"])

    if not args.skip_calendar:
        exit_code |= run_script("run_financial_calendar.py", common + ["--horizon-days", "90"])

    if not args.skip_insider:
        insider_args = common + (["--once"] if not args.continuous else [])
        exit_code |= run_script("run_insider_monitor.py", insider_args)

    if not args.skip_news:
        news_args = common + (["--once"] if not args.continuous else [])
        exit_code |= run_script("run_company_news.py", news_args)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
