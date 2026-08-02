"""Financial calendar connector — earnings, dividends, SEC filing deadlines, macro events."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterator, List, Optional

from connectors.base import NormalizedRecord, RawRecord
from connectors.financial.schemas import CALENDAR_FILTER_FIELDS, CalendarEvent, EventCategory
from connectors.financial.sec_client import SecEdgarClient
from connectors.financial.storage import upsert_records

# Typical SEC filing windows after fiscal quarter end (days)
FILING_WINDOWS = {
    "10-Q": {"large_accelerated": 40, "accelerated": 45, "non_accelerated": 45},
    "10-K": {"large_accelerated": 60, "accelerated": 75, "non_accelerated": 90},
}

MACRO_EVENTS = [
    {"title": "FOMC Rate Decision", "month_day": "01-29", "impact": "high"},
    {"title": "FOMC Rate Decision", "month_day": "03-19", "impact": "high"},
    {"title": "FOMC Rate Decision", "month_day": "05-07", "impact": "high"},
    {"title": "FOMC Rate Decision", "month_day": "06-18", "impact": "high"},
    {"title": "FOMC Rate Decision", "month_day": "07-30", "impact": "high"},
    {"title": "FOMC Rate Decision", "month_day": "09-17", "impact": "high"},
    {"title": "FOMC Rate Decision", "month_day": "11-05", "impact": "high"},
    {"title": "FOMC Rate Decision", "month_day": "12-17", "impact": "high"},
    {"title": "US CPI Release", "month_day": "01-15", "impact": "high"},
    {"title": "US CPI Release", "month_day": "02-12", "impact": "high"},
    {"title": "US Nonfarm Payrolls", "month_day": "01-10", "impact": "high"},
    {"title": "US Nonfarm Payrolls", "month_day": "02-07", "impact": "high"},
]


class FinancialCalendarConnector:
    """Build an investable financial calendar from SEC filings and macro schedule."""

    def __init__(
        self,
        tickers: Optional[List[str]] = None,
        include_macro: bool = True,
        horizon_days: int = 90,
        user_agent: Optional[str] = None,
    ):
        self.client = SecEdgarClient(user_agent=user_agent)
        self.tickers = [t.upper() for t in (tickers or [])]
        self.include_macro = include_macro
        self.horizon_days = horizon_days

    def authenticate(self) -> None:
        self.client.load_ticker_map()

    def discover(self) -> list[dict]:
        return [{"tickers": self.tickers, "horizon_days": self.horizon_days}]

    def _estimate_next_quarterly_filing(self, cik: str, ticker: str, company_name: str) -> Optional[dict]:
        try:
            submissions = self.client.get_submissions(cik)
        except Exception:
            return None
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        report_dates = recent.get("reportDate", [])
        filing_dates = recent.get("filingDate", [])
        for idx, form in enumerate(forms):
            if form not in {"10-Q", "10-K"}:
                continue
            report_date = report_dates[idx] if idx < len(report_dates) else None
            filing_date = filing_dates[idx] if idx < len(filing_dates) else None
            if not report_date:
                continue
            report_dt = datetime.strptime(report_date, "%Y-%m-%d")
            window = FILING_WINDOWS.get(form, {}).get("accelerated", 45)
            if filing_date:
                last_filed = datetime.strptime(filing_date, "%Y-%m-%d")
                delta = (last_filed - report_dt).days
                window = max(window, delta)
            if form == "10-Q":
                next_report = report_dt + timedelta(days=91)
            else:
                next_report = report_dt + timedelta(days=365)
            estimated_filing = next_report + timedelta(days=window)
            return {
                "ticker": ticker,
                "company_name": company_name,
                "form_type": form,
                "report_date": report_date,
                "estimated_filing_date": estimated_filing.strftime("%Y-%m-%d"),
                "title": f"{company_name} estimated {form} filing",
                "description": f"Estimated next {form} based on last report date {report_date}",
            }
        return None

    def _macro_events_for_horizon(self, start: datetime, end: datetime) -> Iterator[dict]:
        if not self.include_macro:
            return
        year = start.year
        for template in MACRO_EVENTS:
            month, day = template["month_day"].split("-")
            event_dt = datetime(year, int(month), int(day))
            if event_dt < start:
                event_dt = datetime(year + 1, int(month), int(day))
            if start <= event_dt <= end:
                yield {
                    "source_id": f"macro_{template['title'].replace(' ', '_').lower()}_{event_dt.date()}",
                    "ticker": None,
                    "company_name": None,
                    "event_type": EventCategory.MACRO.value,
                    "title": template["title"],
                    "event_date": event_dt.strftime("%Y-%m-%d"),
                    "event_time": "14:00",
                    "description": "Scheduled macro event (verify exact time on official calendar)",
                    "estimated": True,
                    "impact": template["impact"],
                }

    def fetch(
        self,
        start: datetime,
        end: datetime,
        cursor: Optional[str] = None,
    ) -> Iterator[RawRecord]:
        horizon_end = end + timedelta(days=self.horizon_days)
        for ticker in self.tickers:
            try:
                cik, resolved_ticker, company_name = self.client.resolve_company(ticker)
            except ValueError:
                continue
            estimate = self._estimate_next_quarterly_filing(cik, resolved_ticker, company_name)
            if estimate:
                est_date = datetime.strptime(estimate["estimated_filing_date"], "%Y-%m-%d")
                if start <= est_date <= horizon_end:
                    yield RawRecord(
                        payload={
                            "source_id": f"est_filing_{cik}_{estimate['form_type']}_{estimate['estimated_filing_date']}",
                            "ticker": resolved_ticker,
                            "company_name": company_name,
                            "event_type": EventCategory.EARNINGS.value,
                            "title": estimate["title"],
                            "event_date": estimate["estimated_filing_date"],
                            "event_time": "16:00",
                            "form_type": estimate["form_type"],
                            "description": estimate["description"],
                            "estimated": True,
                            "impact": "high",
                            "metadata": {"report_date": estimate["report_date"]},
                        }
                    )
            for filing in self.client.iter_filings(cik, form_types=["8-K", "10-Q", "10-K"], limit=10):
                filing_date = filing.get("filing_date", "")
                if not filing_date:
                    continue
                filed_dt = datetime.strptime(filing_date, "%Y-%m-%d")
                if filed_dt < start or filed_dt > horizon_end:
                    continue
                category = EventCategory.SEC_FILING.value
                if filing["form_type"] == "8-K":
                    category = EventCategory.OTHER.value
                yield RawRecord(
                    payload={
                        "source_id": f"filing_{cik}_{filing['accession_number']}",
                        "ticker": resolved_ticker,
                        "company_name": company_name,
                        "event_type": category,
                        "title": f"{company_name} {filing['form_type']} filed",
                        "event_date": filing_date,
                        "event_time": filing.get("acceptance_datetime", "")[11:19] or None,
                        "form_type": filing["form_type"],
                        "description": filing.get("description"),
                        "estimated": False,
                        "impact": "high" if filing["form_type"] in {"10-Q", "10-K"} else "medium",
                        "metadata": {"filing_url": filing["filing_url"]},
                    }
                )

        for macro in self._macro_events_for_horizon(start, horizon_end) or []:
            yield RawRecord(payload=macro)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        record = CalendarEvent(
            source_id=p["source_id"],
            ticker=p.get("ticker"),
            company_name=p.get("company_name"),
            event_type=EventCategory(p.get("event_type", EventCategory.OTHER.value)),
            title=p.get("title", ""),
            event_date=p.get("event_date", ""),
            event_time=p.get("event_time"),
            description=p.get("description"),
            form_type=p.get("form_type"),
            estimated=bool(p.get("estimated")),
            impact=p.get("impact", "medium"),
            metadata=p.get("metadata", {}),
        )
        metadata = record.to_dict()
        metadata["investable_fields"] = CALENDAR_FILTER_FIELDS
        return NormalizedRecord(
            source="financial_calendar",
            source_id=record.source_id,
            timestamp=datetime.utcnow(),
            text=f"{record.title} on {record.event_date}",
            entities=[{"type": "ticker", "value": record.ticker}] if record.ticker else [],
            metadata=metadata,
            provenance={"connector": "financial_calendar", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(
        self,
        raw: RawRecord,
        normalized: NormalizedRecord,
        s3_bucket: Optional[str] = None,
        s3_writer=None,
        data_dir=None,
    ) -> dict:
        record = normalized.metadata
        merged = upsert_records("calendar", [record], data_dir=data_dir)
        result = {"stored": len(merged), "source_id": record.get("source_id")}
        if s3_bucket and s3_writer:
            from connectors.financial.storage import store_to_s3

            uri = store_to_s3(s3_bucket, "calendar", merged, s3_writer=s3_writer)
            result["s3_uri"] = uri
        return result

    def monitor(self) -> dict:
        return {"status": "ok", "tickers": self.tickers, "horizon_days": self.horizon_days}
