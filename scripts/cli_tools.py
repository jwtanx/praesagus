#!/usr/bin/env python3
"""CLI navigator for standalone Praesagus tools.

Run this script and choose the tool you want to execute.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

AVAILABLE_TOOLS = {
    "sec_qr_report": {
        "script": "sec_qr_report.py",
        "description": "Poll EDGAR filings for 10-Q/10-K/8-K and write JSON reports.",
    },
    "run_sec_filings": {
        "script": "run_sec_filings.py",
        "description": "Fetch SEC filings for watchlist companies or specified tickers.",
    },
    "run_insider_monitor": {
        "script": "run_insider_monitor.py",
        "description": "Monitor SEC Form 4 insider trades in near real-time.",
    },
    "run_company_news": {
        "script": "run_company_news.py",
        "description": "Find earliest company news and surface buy/short signals.",
    },
    "run_financial_calendar": {
        "script": "run_financial_calendar.py",
        "description": "Sync earnings, dividend, SEC filing deadlines, and macro events.",
    },
    "run_financial_pipeline": {
        "script": "run_financial_pipeline.py",
        "description": "Run the full pipeline of SEC filings, insider monitor, news, and calendar tools.",
    },
    "realtime_qr_watcher": {
        "script": "realtime_qr_watcher.py",
        "description": "Watch for the latest QR filings across SEC and print ticker/action signals.",
    },
}


def run_tool(name: str, extra_args: list[str]) -> int:
    tool = AVAILABLE_TOOLS.get(name)
    if not tool:
        print(f"Unknown tool: {name}")
        return 1
    cmd = [sys.executable, str(SCRIPTS / tool["script"]), *extra_args]
    print(f"\n>>> Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(ROOT))
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Praesagus tool launcher. Run standalone ingestion and monitoring scripts.")
    parser.add_argument("tool", nargs="?", help="Tool name to run")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the selected tool")
    args = parser.parse_args()

    if not args.tool:
        print("Available tools:")
        for name, item in AVAILABLE_TOOLS.items():
            print(f"  {name}\t- {item['description']}")
        print("\nRun a tool with: python scripts/cli_tools.py <tool> [tool args]")
        return 0

    return run_tool(args.tool, args.args)


if __name__ == "__main__":
    raise SystemExit(main())
