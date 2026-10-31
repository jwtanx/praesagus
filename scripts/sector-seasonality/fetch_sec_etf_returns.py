#!/usr/bin/env python3
"""Fetch SEC-filed monthly ETF total returns for the five thematic proxies."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import time
import urllib.parse
import threading
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests

SEC_SERIES = [
    ("AI", "Artificial intelligence", "AIQ", "Global X Artificial Intelligence & Technology ETF", "S000061326", "C000198548"),
    ("Robotics", "Robotics & automation", "ROBO", "ROBO Global Robotics and Automation Index ETF", "S000042659", "C000131868"),
    ("Quantum", "Quantum computing", "QTUM", "Defiance Quantum ETF", "S000062478", "C000202668"),
    ("Nuclear", "Nuclear energy", "NLR", "VanEck Uranium and Nuclear ETF", "S000018475", "C000051121"),
    ("Renewable", "Renewable energy", "ICLN", "iShares Global Clean Energy ETF", "S000022498", "C000065074"),
]
SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
ARCHIVE_ROOT = "https://www.sec.gov/Archives/edgar/data"
SEC_USER_AGENT = "Praesagus Seasonality Data Fetcher/1.0"
_request_lock = threading.Lock()
_last_request_at = 0.0


def _tag(element: ET.Element, name: str) -> ET.Element | None:
    return next((node for node in element.iter() if node.tag.split("}")[-1] == name), None)


def parse_filing(xml_bytes: bytes, expected_series: str, expected_class: str) -> dict:
    root = ET.fromstring(xml_bytes)
    series_id = _tag(root, "seriesId")
    report_date = _tag(root, "repPdDate")
    series_name = _tag(root, "seriesName")
    if series_id is None or series_id.text != expected_series:
        raise ValueError("SEC filing series identifier mismatch")
    if report_date is None or report_date.text is None or series_name is None:
        raise ValueError("SEC filing lacks series name or report date")
    reported_date = date.fromisoformat(report_date.text)
    return_record = next(
        (node for node in root.iter() if node.tag.split("}")[-1] == "monthlyTotReturn" and node.attrib.get("classId") == expected_class),
        None,
    )
    if return_record is None:
        raise ValueError(f"SEC filing lacks reported return for class {expected_class}")
    observations = []
    for slot, months_before in (("rtn1", 2), ("rtn2", 1), ("rtn3", 0)):
        raw_value = return_record.attrib.get(slot)
        if raw_value is None:
            raise ValueError(f"SEC filing lacks {slot}")
        try:
            value = Decimal(raw_value)
        except InvalidOperation as exc:
            raise ValueError(f"SEC filing has invalid {slot}: {raw_value!r}") from exc
        if not value.is_finite() or abs(value) > Decimal("1000"):
            raise ValueError(f"SEC filing has implausible {slot}: {raw_value!r}")
        year, month = reported_date.year, reported_date.month - months_before
        while month < 1:
            month += 12
            year -= 1
        observations.append({"period": year * 100 + month, "value": float(value), "reportedValue": raw_value, "slot": slot})
    return {"seriesId": expected_series, "seriesName": series_name.text, "reportDate": reported_date.isoformat(), "observations": observations}


def _get(url: str) -> bytes:
    global _last_request_at
    with _request_lock:
        delay = 0.13 - (time.monotonic() - _last_request_at)
        if delay > 0:
            time.sleep(delay)
        response = requests.get(url, headers={"User-Agent": SEC_USER_AGENT}, timeout=30)
        _last_request_at = time.monotonic()
    response.raise_for_status()
    return response.content


def _month_label(period: int) -> str:
    return f"{period // 100:04d}-{period % 100:02d}"


def fetch_series(
    code: str,
    name: str,
    ticker: str,
    fund_name: str,
    series_id: str,
    class_id: str,
    *,
    existing_accessions: set[str] | None = None,
    from_period: int | None = None,
    through_period: int | None = None,
    skip_existing: bool = True,
) -> dict:
    query = urllib.parse.urlencode({"q": series_id, "forms": "NPORT-P", "from": 0, "size": 100})
    search_url = f"{SEARCH_URL}?{query}"
    search = json.loads(_get(search_url))
    hits = search.get("hits", {})
    total = hits.get("total", {}).get("value", 0)
    documents = hits.get("hits", [])
    if total != len(documents):
        raise ValueError(f"{ticker}: SEC search returned {len(documents)} of {total} matching filings")

    filings = {}
    existing_accessions = existing_accessions or set()
    for hit in documents:
        source = hit.get("_source", {})
        form_type = source.get("file_type")
        if form_type not in ("NPORT-P", "NPORT-P/A"):
            continue
        accession = source.get("adsh", "")
        if skip_existing and accession in existing_accessions:
            continue
        filed_period = source.get("period_ending", "")
        if from_period is not None and filed_period:
            filed_period = int(filed_period[:7].replace("-", ""))
            if filed_period < from_period:
                continue
            if through_period is not None and filed_period > through_period:
                continue
        cik = (source.get("ciks") or [""])[0]
        if not accession or not cik.isdigit():
            raise ValueError(f"{ticker}: malformed SEC filing search result")
        accession_path = accession.replace("-", "")
        url = f"{ARCHIVE_ROOT}/{int(cik)}/{accession_path}/primary_doc.xml"
        xml_bytes = _get(url)
        parsed = parse_filing(xml_bytes, series_id, class_id)
        filed_on = source.get("file_date")
        if not filed_on:
            raise ValueError(f"{ticker}: SEC search result lacks filing date")
        parsed["accession"] = accession
        parsed["filedOn"] = filed_on
        parsed["filingUrl"] = url
        parsed["filingSha256"] = hashlib.sha256(xml_bytes).hexdigest()
        filings[parsed["reportDate"]] = parsed
        time.sleep(0.12)

    if not filings:
        return {
            "code": code, "name": name, "ticker": ticker, "fundName": fund_name,
            "historicalFundNames": [], "seriesId": series_id, "classId": class_id,
            "periodStart": None, "periodEnd": None,
            "source": "U.S. Securities and Exchange Commission, Form N-PORT, Item B.5",
            "sourceUrl": f"https://www.sec.gov/edgar/search/#/q={series_id}&forms=NPORT-P",
            "issuerUrl": _issuer_url(ticker),
            "method": "Fund-reported monthly total return for the share class, as filed under Form N-PORT Item B.5. Each observation links to the exact filing and records the reported value and field.",
            "filings": [], "returns": [],
        }

    selected: dict[int, dict] = {}
    for filing in sorted(filings.values(), key=lambda item: item["filedOn"]):
        for observation in filing["observations"]:
            selected[observation["period"]] = {
                **observation,
                "filingDate": filing["reportDate"],
                "filedOn": filing["filedOn"],
                "accession": filing["accession"],
                "filingUrl": filing["filingUrl"],
                "filingSha256": filing["filingSha256"],
            }
    series = [selected[period] for period in sorted(selected)]
    gaps = []
    for left, right in zip(series, series[1:]):
        year, month = divmod(left["period"], 100)
        expected_period = year * 100 + month + 1 if month < 12 else (year + 1) * 100 + 1
        if right["period"] != expected_period:
            gaps.append((left["period"], right["period"]))
    if gaps:
        raise ValueError(f"{ticker}: SEC return history contains gaps {gaps[:5]}")
    return {
        "code": code,
        "name": name,
        "ticker": ticker,
        "fundName": fund_name,
        "historicalFundNames": sorted({item["seriesName"] for item in filings.values()}),
        "seriesId": series_id,
        "classId": class_id,
        "periodStart": _month_label(series[0]["period"]),
        "periodEnd": _month_label(series[-1]["period"]),
        "source": "U.S. Securities and Exchange Commission, Form N-PORT, Item B.5",
        "sourceUrl": f"https://www.sec.gov/edgar/search/#/q={series_id}&forms=NPORT-P",
        "issuerUrl": _issuer_url(ticker),
        "method": "Fund-reported monthly total return for the share class, as filed under Form N-PORT Item B.5. Each observation links to the exact filing and records the reported value and field.",
        "filings": sorted(filings.values(), key=lambda item: item["filedOn"]),
        "returns": series,
    }


def _issuer_url(ticker: str) -> str:
    return {
        "AIQ": "https://www.globalxetfs.com/funds/AIQ/",
        "ROBO": "https://www.roboglobaletfs.com/robo/",
        "QTUM": "https://www.defianceetfs.com/qtum/",
        "NLR": "https://www.vaneck.com/us/en/investments/uranium-nuclear-energy-etf-nlr/",
        "ICLN": "https://www.ishares.com/us/products/239738/ishares-global-clean-energy-etf/",
    }[ticker]


def fetch_all(existing_data: dict | None = None, *, from_period: int | None = None, through_period: int | None = None, skip_existing: bool = True) -> dict:
    existing_by_code = {item["code"]: item for item in (existing_data or {}).get("series", [])}
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for entry in SEC_SERIES:
            previous = existing_by_code.get(entry[0], {})
            known = {filing["accession"] for filing in previous.get("filings", []) if filing.get("accession")}
            futures.append(executor.submit(
                fetch_series, *entry, existing_accessions=known,
                from_period=from_period, through_period=through_period,
                skip_existing=skip_existing,
            ))
        for future in futures:
            results.append(future.result())
    return {"schemaVersion": 1, "provider": "SEC EDGAR public filings", "retrievedOn": date.today().isoformat(), "series": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_json", type=Path, help="Path for extracted, source-linked SEC return observations")
    args = parser.parse_args()
    data = fetch_all()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    print("Fetched " + ", ".join(f"{item['ticker']} {item['periodStart']}–{item['periodEnd']} ({len(item['returns'])} months)" for item in data["series"]))


if __name__ == "__main__":
    main()
