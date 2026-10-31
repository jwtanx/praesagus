#!/usr/bin/env python3
"""Extract a checked monthly industry panel and U.S. market benchmark."""

from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import io
import json
import zipfile
from pathlib import Path

START = 199601
END = 202609
SOURCE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_CSV.zip"
MARKET_SOURCE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/Ken.French/ftp/F-F_Research_Data_Factors_CSV.zip"
EXPECTED_INDUSTRIES = "Agric Food Soda Beer Smoke Toys Fun Books Hshld Clths Hlth MedEq Drugs Chems Rubbr Txtls BldMt Cnstr Steel FabPr Mach ElcEq Autos Aero Ships Guns Gold Mines Coal Oil Util Telcm PerSv BusSv Hardw Softw Chips LabEq Paper Boxes Trans Whlsl Rtail Meals Banks Insur RlEst Fin Other".split()


def read_monthly_value_weighted(zip_bytes: bytes, end: int | None = END) -> tuple[list[str], list[list[float | int]]]:
    """Read only the first (value-weighted) monthly table and validate its panel."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected one CSV in source ZIP, found {len(csv_names)}")
        text = archive.read(csv_names[0]).decode("utf-8-sig")

    lines = text.splitlines()
    try:
        heading = lines.index("  Average Value Weighted Returns -- Monthly")
    except ValueError as exc:
        raise ValueError("Source lacks the monthly value-weighted section") from exc

    header_index = next((i for i in range(heading + 1, min(heading + 8, len(lines))) if [value.strip() for value in next(csv.reader([lines[i]]))[1:]] == EXPECTED_INDUSTRIES), None)
    if header_index is None:
        raise ValueError("Could not find the 49-industry header")
    headers = [value.strip() for value in next(csv.reader([lines[header_index]]))[1:]]
    if headers != EXPECTED_INDUSTRIES:
        raise ValueError(f"Unexpected industry columns: {headers!r}")

    rows: list[list[float | int]] = []
    for line in lines[header_index + 1:]:
        parts = next(csv.reader([line]))
        if not parts or not parts[0].strip().isdigit():
            if rows:
                break
            continue
        period = int(parts[0].strip())
        if period < START or end is not None and period > end:
            continue
        if len(parts) != len(headers) + 1:
            raise ValueError(f"Unexpected column count for {period}: {len(parts) - 1}")
        values = [float(value.strip()) for value in parts[1:]]
        if any(value in (-99.99, -999.0) for value in values):
            raise ValueError(f"Missing-value marker in requested period {period}")
        rows.append([period, *values])

    actual_periods = [int(row[0]) for row in rows]
    expected_periods = []
    year, month = 1996, 1
    expected_end = end if end is not None else (actual_periods[-1] if actual_periods else START - 1)
    while (year * 100 + month) <= expected_end:
        expected_periods.append(year * 100 + month)
        month += 1
        if month == 13:
            year += 1
            month = 1
    if actual_periods != expected_periods:
        raise ValueError(f"Expected contiguous monthly industry data through {expected_periods[-1] if expected_periods else 'no period'}; found {len(rows)} ({actual_periods[:1]}..{actual_periods[-1:]})")
    return headers, rows


def read_monthly_market_returns(zip_bytes: bytes, end: int | None = END) -> dict[int, float]:
    """Read French's broad U.S. market total returns (Mkt-RF + RF), in percent."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected one CSV in market-factor ZIP, found {len(csv_names)}")
        text = archive.read(csv_names[0]).decode("utf-8-sig")

    lines = text.splitlines()
    header_index = next(
        (i for i, line in enumerate(lines) if next(csv.reader([line])) == ["", "Mkt-RF", "SMB", "HML", "RF"]),
        None,
    )
    if header_index is None:
        raise ValueError("Market-factor file has unexpected columns")

    returns: dict[int, float] = {}
    for line in lines[header_index + 1:]:
        parts = next(csv.reader([line]))
        if not parts or not parts[0].strip().isdigit():
            continue
        period = int(parts[0].strip())
        if period < START or end is not None and period > end:
            continue
        if len(parts) != 5:
            raise ValueError(f"Unexpected factor column count for {period}: {len(parts) - 1}")
        market_excess, risk_free = float(parts[1]), float(parts[4])
        if market_excess in (-99.99, -999.0) or risk_free in (-99.99, -999.0):
            raise ValueError(f"Missing market-factor marker for {period}")
        returns[period] = round(market_excess + risk_free, 2)

    expected_end = end if end is not None else (max(returns) if returns else START - 1)
    expected_periods = [int(row[0]) for row in _expected_period_rows(expected_end)]
    if sorted(returns) != expected_periods:
        raise ValueError(f"Expected contiguous market months through {expected_periods[-1] if expected_periods else 'no period'}; found {len(returns)}")
    return returns


def _expected_period_rows(end: int = END):
    year, month = 1996, 1
    while year * 100 + month <= end:
        yield [year * 100 + month]
        month += 1
        if month == 13:
            year += 1
            month = 1


def make_dataset(zip_bytes: bytes, market_zip_bytes: bytes, *, end_period: int | None = END) -> dict:
    industries, rows = read_monthly_value_weighted(zip_bytes, end_period)
    market_returns = read_monthly_market_returns(market_zip_bytes, end_period)
    for row in rows:
        row.append(market_returns[int(row[0])])
    period_start = f"{rows[0][0] // 100:04d}-{rows[0][0] % 100:02d}"
    period_end = f"{rows[-1][0] // 100:04d}-{rows[-1][0] % 100:02d}"
    end_year, end_month = divmod(int(rows[-1][0]), 100)
    complete_year = end_year if end_month == 12 else end_year - 1
    return {
        "schemaVersion": 3,
        "source": "Kenneth R. French Data Library, 49 Industry Portfolios",
        "sourceUrl": SOURCE_URL,
        "sourceFile": "49_Industry_Portfolios.csv",
        "sourceDatabaseAsOf": f"{period_end} CRSP database",
        "sourceRetrievedOn": date.today().isoformat(),
        "sourceArchiveSha256": hashlib.sha256(zip_bytes).hexdigest(),
        "marketSource": "Kenneth R. French Data Library, Fama/French 3 Factors",
        "marketSourceUrl": MARKET_SOURCE_URL,
        "marketSourceFile": "F-F_Research_Data_Factors.csv",
        "marketSourceRetrievedOn": date.today().isoformat(),
        "marketSourceArchiveSha256": hashlib.sha256(market_zip_bytes).hexdigest(),
        "marketReturnDefinition": "Mkt-RF plus RF, in percent; value-weighted return of eligible U.S.-incorporated NYSE, AMEX, and NASDAQ stocks.",
        "marketReturnColumn": 50,
        "copyright": "Copyright Eugene F. Fama and Kenneth R. French",
        "geography": "United States",
        "method": "Monthly value-weighted returns for 49 SIC-classified industry portfolios, percent. Overall U.S. market total return is Mkt-RF plus RF from the Fama/French factors; dividends are included by source methodology.",
        "periodStart": period_start,
        "periodEnd": period_end,
        "completeCalendarYearsThrough": complete_year,
        "latestPartialCalendarYear": end_year if end_month != 12 else None,
        "latestAvailableMonth": end_month,
        "industryCodes": industries,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__ + " The pinned build defaults through 2026-09; the sync command detects the current archive end.")
    parser.add_argument("source_zip", type=Path, help="Downloaded official 49_Industry_Portfolios_CSV.zip")
    parser.add_argument("market_source_zip", type=Path, help="Downloaded official F-F_Research_Data_Factors_CSV.zip")
    parser.add_argument("output_json", type=Path, help="Generated frontend dataset path")
    args = parser.parse_args()
    data = make_dataset(args.source_zip.read_bytes(), args.market_source_zip.read_bytes())
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {len(data['rows'])} months x {len(data['industryCodes'])} industries to {args.output_json}")
    print(f"Source archive SHA-256: {data['sourceArchiveSha256']}")


if __name__ == "__main__":
    main()
