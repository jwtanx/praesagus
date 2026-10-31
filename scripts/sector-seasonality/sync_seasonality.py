#!/usr/bin/env python3
"""Incrementally sync official industry/market and SEC-filed ETF return data."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[2]
INDUSTRY_JSON = ROOT / "frontend/src/data/industry-seasonality.json"
ETF_JSON = ROOT / "frontend/src/data/etf-nport-returns.json"
BUILD_SCRIPT = Path(__file__).with_name("build_dataset.py")
SEC_SCRIPT = Path(__file__).with_name("fetch_sec_etf_returns.py")
TODAY = datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).date()
CURRENT_PERIOD = TODAY.year * 100 + TODAY.month
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dataset_builder = _load_module("seasonality_dataset_builder", BUILD_SCRIPT)
sec_fetcher = _load_module("seasonality_sec_fetcher", SEC_SCRIPT)


def parse_month(value: str) -> int:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise argparse.ArgumentTypeError("month must use YYYY-MM")
    year, month = map(int, value.split("-"))
    return year * 100 + month


def add_months(period: int, count: int) -> int:
    year, month = divmod(period, 100)
    ordinal = year * 12 + month - 1 + count
    return ordinal // 12 * 100 + ordinal % 12 + 1


def conditional_download(url: str, etag: str | None, modified: str | None) -> tuple[bytes | None, dict]:
    headers = {"User-Agent": "Praesagus Seasonality Sync/1.0"}
    if etag:
        headers["If-None-Match"] = etag
    if modified:
        headers["If-Modified-Since"] = modified
    response = requests.get(url, headers=headers, timeout=45, stream=True)
    if response.status_code == 304:
        response.close()
        return None, {}
    response.raise_for_status()
    length = int(response.headers.get("Content-Length", "0") or 0)
    if length > MAX_ARCHIVE_BYTES:
        raise ValueError(f"Source archive exceeds {MAX_ARCHIVE_BYTES} bytes: {url}")
    chunks = []
    total = 0
    for chunk in response.iter_content(65536):
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_ARCHIVE_BYTES:
            raise ValueError(f"Source archive exceeds {MAX_ARCHIVE_BYTES} bytes: {url}")
        chunks.append(chunk)
    return b"".join(chunks), {
        "etag": response.headers.get("ETag"),
        "lastModified": response.headers.get("Last-Modified"),
    }


def _period_label(period: int) -> str:
    return f"{period // 100:04d}-{period % 100:02d}"


def _source_industries(previous: dict, archive: bytes | None, end_period: int | None) -> tuple[list[str], dict[int, list[float]]]:
    if archive is None:
        codes = previous["industryCodes"]
        return codes, {int(row[0]): row[1:50] for row in previous["rows"]}
    codes, rows = dataset_builder.read_monthly_value_weighted(archive, end_period)
    return codes, {int(row[0]): row[1:] for row in rows}


def _source_market(previous: dict, archive: bytes | None, end_period: int | None) -> dict[int, float]:
    if archive is None:
        return {int(row[0]): row[50] for row in previous["rows"]}
    return dataset_builder.read_monthly_market_returns(archive, end_period)


def merge_industry_dataset(previous: dict, industries: dict[int, list[float]], market: dict[int, float], *, from_period: int | None, month: int | None, missing_only: bool, industry_archive: bytes | None, market_archive: bytes | None, industry_validators: dict, market_validators: dict) -> tuple[dict, int]:
    if previous.get("industryCodes") and previous["industryCodes"] != dataset_builder.EXPECTED_INDUSTRIES:
        raise ValueError("Stored industry schema does not match the pinned 49-industry source")
    old_rows = {int(row[0]): row for row in previous.get("rows", [])}
    source_periods = sorted(set(industries) & set(market))
    selected_periods = [period for period in source_periods if period <= CURRENT_PERIOD]
    if month is not None:
        selected_periods = [period for period in selected_periods if period == month]
    elif from_period is not None:
        selected_periods = [period for period in selected_periods if period >= from_period]

    result = dict(previous)
    changed = 0
    merged = dict(old_rows)
    for period in selected_periods:
        if missing_only and period in merged:
            continue
        merged[period] = [period, *industries[period], market[period]]
        changed += 1
    if not merged:
        raise ValueError("No existing or newly available industry/market observations")
    periods = sorted(merged)
    expected = []
    year, month_number = divmod(periods[0], 100)
    while year * 100 + month_number <= periods[-1]:
        expected.append(year * 100 + month_number)
        month_number += 1
        if month_number == 13:
            year, month_number = year + 1, 1
    if periods != expected:
        raise ValueError("Merged industry/market history is not contiguous; use --start-year or --back-years to fill the gap")
    result["rows"] = [merged[period] for period in periods]
    result["periodStart"] = _period_label(periods[0])
    result["periodEnd"] = _period_label(periods[-1])
    end_year, end_month = divmod(periods[-1], 100)
    result["completeCalendarYearsThrough"] = end_year if end_month == 12 else end_year - 1
    result["latestPartialCalendarYear"] = end_year if end_month != 12 else None
    result["latestAvailableMonth"] = end_month
    result["industryCodes"] = dataset_builder.EXPECTED_INDUSTRIES
    if industry_archive is not None:
        result["sourceArchiveSha256"] = hashlib.sha256(industry_archive).hexdigest()
        result["sourceRetrievedOn"] = TODAY.isoformat()
        result["sourceDatabaseAsOf"] = f"{_period_label(max(industries))} CRSP database"
    if market_archive is not None:
        result["marketSourceArchiveSha256"] = hashlib.sha256(market_archive).hexdigest()
        result["marketSourceRetrievedOn"] = TODAY.isoformat()
    result["sourceValidator"] = industry_validators
    result["marketSourceValidator"] = market_validators
    return result, changed


def merge_etf_data(previous: dict, fetched: dict, *, from_period: int | None, month: int | None, missing_only: bool) -> tuple[dict, int]:
    old_by_code = {item["code"]: item for item in previous.get("series", [])}
    new_by_code = {item["code"]: item for item in fetched.get("series", [])}
    merged_series = []
    total_added = 0
    for code, *_ in sec_fetcher.SEC_SERIES:
        old = old_by_code.get(code)
        new = new_by_code[code]
        if old is None:
            combined = new
        else:
            filings = {item["accession"]: item for item in old.get("filings", []) if item.get("accession")}
            filings.update({item["accession"]: item for item in new.get("filings", []) if item.get("accession")})
            values = {int(item["period"]): item for item in old.get("returns", [])}
            for item in new.get("returns", []):
                period = int(item["period"])
                if month is not None and period != month:
                    continue
                if from_period is not None and period < from_period:
                    continue
                if missing_only and period in values:
                    continue
                if period > CURRENT_PERIOD:
                    continue
                prior = values.get(period)
                if prior is None or item.get("filedOn", "") >= prior.get("filedOn", ""):
                    values[period] = item
                    if prior is None or item != prior:
                        total_added += 1
            values_list = [values[period] for period in sorted(values)]
            combined = dict(old)
            combined["filings"] = sorted(filings.values(), key=lambda filing: (filing.get("filedOn", ""), filing.get("accession", "")))
            combined["returns"] = values_list
            combined["historicalFundNames"] = sorted(set(old.get("historicalFundNames", [])) | set(new.get("historicalFundNames", [])))
            if values_list:
                combined["periodStart"] = _period_label(values_list[0]["period"])
                combined["periodEnd"] = _period_label(values_list[-1]["period"])
        if old is None:
            total_added += len(combined.get("returns", []))
        merged_series.append(combined)
    result = {"schemaVersion": 1, "provider": "SEC EDGAR public filings", "retrievedOn": previous.get("retrievedOn", TODAY.isoformat()), "series": merged_series}
    if merged_series != previous.get("series", []):
        result["retrievedOn"] = TODAY.isoformat()
    return result, total_added


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as destination:
            json.dump(data, destination, separators=(",", ":"))
            destination.write("\n")
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sync(args: argparse.Namespace) -> tuple[int, int, list[str]]:
    industry_path, etf_path = args.industry_json, args.etf_json
    previous_industry = _load_json(industry_path)
    previous_etf = _load_json(etf_path)
    if args.start_year and args.back_years:
        raise ValueError("Use only one of --start-year or --back-years")
    if args.back_years is not None and args.back_years < 1:
        raise ValueError("--back-years must be at least 1")
    if args.missing_only and args.start_year is None and args.back_years is None:
        raise ValueError("--missing-only is meaningful only with --start-year or --back-years")
    if args.month and (args.start_year or args.back_years):
        raise ValueError("--month cannot be combined with --start-year or --back-years")
    start_year = args.start_year
    if args.back_years:
        start_year = TODAY.year - args.back_years + 1
    from_period = start_year * 100 + 1 if start_year else None
    missing_only = args.missing_only or start_year is None
    requested_month = parse_month(args.month) if args.month else None
    if requested_month is not None and requested_month > CURRENT_PERIOD:
        raise ValueError("--month cannot be in the future")
    target = requested_month if requested_month is not None else CURRENT_PERIOD

    industry_bytes, industry_validator = conditional_download(
        dataset_builder.SOURCE_URL,
        previous_industry.get("sourceValidator", {}).get("etag"),
        previous_industry.get("sourceValidator", {}).get("lastModified"),
    )
    market_bytes, market_validator = conditional_download(
        dataset_builder.MARKET_SOURCE_URL,
        previous_industry.get("marketSourceValidator", {}).get("etag"),
        previous_industry.get("marketSourceValidator", {}).get("lastModified"),
    )
    end_period = None
    industries, industry_map = _source_industries(previous_industry, industry_bytes, end_period)
    market_map = _source_market(previous_industry, market_bytes, end_period)
    if industries != dataset_builder.EXPECTED_INDUSTRIES:
        raise ValueError("Official source industry columns differ from the pinned 49-industry schema")
    updated_industry, industry_changed = merge_industry_dataset(
        previous_industry, industry_map, market_map,
        from_period=from_period, month=requested_month, missing_only=missing_only,
        industry_archive=industry_bytes, market_archive=market_bytes,
        industry_validators=industry_validator or previous_industry.get("sourceValidator", {}),
        market_validators=market_validator or previous_industry.get("marketSourceValidator", {}),
    )

    fetched_etf = sec_fetcher.fetch_all(
        previous_etf,
        from_period=(requested_month if requested_month is not None else from_period),
        through_period=add_months(requested_month, 2) if requested_month is not None else None,
        skip_existing=requested_month is None and start_year is None,
    )
    updated_etf, etf_changed = merge_etf_data(
        previous_etf, fetched_etf, from_period=from_period,
        month=requested_month, missing_only=missing_only,
    )
    messages = [f"Target month: {_period_label(target)} (current calendar month is the default)."]
    messages.append(f"Industry/market observations {'added or refreshed' if not missing_only else 'filled'}: {industry_changed}.")
    messages.append(f"SEC proxy monthly observations added or refreshed: {etf_changed}.")
    messages.append(f"Official industry and market data now covers {updated_industry['periodStart']}–{updated_industry['periodEnd']}.")
    messages.append("SEC proxy latest months: " + ", ".join(f"{item['ticker']} {item['periodEnd'] or 'no filed return'}" for item in updated_etf["series"]) + ".")
    if industry_bytes is None and market_bytes is None:
        messages.append("Both French source archives returned HTTP 304 Not Modified; no archive payload was downloaded.")
    elif industry_bytes is None or market_bytes is None:
        messages.append("At least one French archive was unchanged (HTTP 304); only changed source archives were downloaded.")
    if requested_month is not None and industry_changed == 0 and etf_changed == 0:
        messages.append("No new missing observation was found for that month; it may already be stored or not yet published by a source.")
    if updated_industry != previous_industry:
        atomic_write(industry_path, updated_industry)
    if updated_etf != previous_etf:
        atomic_write(etf_path, updated_etf)
    return industry_changed, etf_changed, messages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--industry-json", type=Path, default=INDUSTRY_JSON, help="Industry/market data JSON (default: frontend/src/data/industry-seasonality.json)")
    parser.add_argument("--etf-json", type=Path, default=ETF_JSON, help="SEC proxy data JSON (default: frontend/src/data/etf-nport-returns.json)")
    parser.add_argument("--month", help="Only fill missing observations for one YYYY-MM month; defaults to newly published missing observations up to the current month")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--start-year", type=int, help="Re-sync data from January of this year through the latest source-available month")
    group.add_argument("--back-years", type=int, help="Re-sync a rolling window including this year (e.g. 5 means current year plus the four prior years)")
    parser.add_argument("--missing-only", action="store_true", help="With --start-year/--back-years, fill blank periods without replacing values already present")
    args = parser.parse_args()
    if args.start_year is not None and not 1900 <= args.start_year <= TODAY.year:
        parser.error(f"--start-year must be between 1900 and {TODAY.year}")
    try:
        industry_count, etf_count, messages = sync(args)
    except (OSError, ValueError, requests.RequestException, json.JSONDecodeError) as exc:
        parser.exit(2, f"Seasonality sync failed: {exc}\n")
    for message in messages:
        print(message)
    print(f"Updated JSON: {args.industry_json} ({industry_count} industry/market months), {args.etf_json} ({etf_count} proxy observations).")


if __name__ == "__main__":
    main()
