"""SEC quarterly and annual report connector (10-Q, 10-K, 8-K) via EDGAR REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Iterator, List, Optional

from connectors.base import NormalizedRecord, RawRecord
from connectors.financial.schemas import FILING_FILTER_FIELDS, FilingRecord, FinancialMetrics
from connectors.financial.sec_client import SecEdgarClient
from connectors.financial.storage import upsert_records


class SecFilingsConnector:
    """Fetch SEC filings and XBRL financial metrics for investment analysis."""

    DEFAULT_FORMS = ["10-Q", "10-K", "8-K"]

    def __init__(
        self,
        tickers: Optional[List[str]] = None,
        ciks: Optional[List[str]] = None,
        form_types: Optional[List[str]] = None,
        limit_per_company: int = 20,
        user_agent: Optional[str] = None,
        include_metrics: bool = True,
    ):
        self.client = SecEdgarClient(user_agent=user_agent)
        self.tickers = [t.upper() for t in (tickers or [])]
        self.ciks = ciks or []
        self.form_types = form_types or self.DEFAULT_FORMS
        self.limit_per_company = limit_per_company
        self.include_metrics = include_metrics
        self._company_cache: dict[str, tuple[str, str, str]] = {}

    def authenticate(self) -> None:
        self.client.load_ticker_map()

    def discover(self) -> list[dict]:
        companies = []
        for ticker in self.tickers:
            cik, resolved_ticker, name = self.client.resolve_company(ticker)
            companies.append({"ticker": resolved_ticker, "cik": cik, "company_name": name})
        for cik in self.ciks:
            normalized, ticker, name = self.client.resolve_company(cik)
            companies.append({"ticker": ticker, "cik": normalized, "company_name": name})
        return companies

    def _resolve_companies(self) -> List[tuple[str, str, str]]:
        companies: List[tuple[str, str, str]] = []
        seen = set()
        for ticker in self.tickers:
            cik, resolved_ticker, name = self.client.resolve_company(ticker)
            key = cik
            if key not in seen:
                companies.append((cik, resolved_ticker, name))
                seen.add(key)
        for cik in self.ciks:
            normalized, ticker, name = self.client.resolve_company(cik)
            if normalized not in seen:
                companies.append((normalized, ticker, name))
                seen.add(normalized)
        return companies

    def fetch(
        self,
        start: datetime,
        end: datetime,
        cursor: Optional[str] = None,
    ) -> Iterator[RawRecord]:
        for cik, ticker, company_name in self._resolve_companies():
            metrics: Optional[FinancialMetrics] = None
            if self.include_metrics:
                try:
                    metrics = self.client.extract_metrics(cik)
                except Exception:
                    metrics = None
            for filing in self.client.iter_filings(cik, form_types=self.form_types, limit=self.limit_per_company):
                filing_date = filing.get("filing_date", "")
                if filing_date:
                    filed_dt = datetime.strptime(filing_date, "%Y-%m-%d")
                    if filed_dt < start or filed_dt > end:
                        continue
                payload = {
                    "cik": cik,
                    "ticker": ticker,
                    "company_name": company_name,
                    "metrics": metrics.to_dict() if metrics else None,
                    **filing,
                }
                yield RawRecord(payload=payload)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        metrics_data = p.get("metrics")
        metrics = FinancialMetrics(**metrics_data) if metrics_data else None
        source_id = f"{p['cik']}_{p['accession_number']}"
        record = FilingRecord(
            source_id=source_id,
            cik=p["cik"],
            ticker=p.get("ticker", ""),
            company_name=p.get("company_name", ""),
            form_type=p["form_type"],
            filing_date=p["filing_date"],
            acceptance_datetime=p.get("acceptance_datetime", ""),
            report_date=p.get("report_date"),
            accession_number=p["accession_number"],
            primary_document=p["primary_document"],
            filing_url=p["filing_url"],
            document_url=p["filing_url"],
            description=p.get("description"),
            is_amendment=bool(p.get("is_amendment")),
            metrics=metrics,
            investable_fields=FILING_FILTER_FIELDS,
        )
        text = (
            f"{record.company_name} ({record.ticker}) filed {record.form_type} "
            f"on {record.filing_date}. Report date: {record.report_date}."
        )
        return NormalizedRecord(
            source="sec_filings",
            source_id=source_id,
            timestamp=datetime.utcnow(),
            text=text,
            entities=[{"type": "ticker", "value": record.ticker}, {"type": "cik", "value": record.cik}],
            metadata=record.to_dict(),
            provenance={"connector": "sec_filings", "ingest_ts": datetime.utcnow().isoformat()},
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
        merged = upsert_records("filings", [record], data_dir=data_dir)
        result = {"stored": len(merged), "source_id": record.get("source_id")}
        if s3_bucket and s3_writer:
            from connectors.financial.storage import store_to_s3

            uri = store_to_s3(s3_bucket, "filings", merged, s3_writer=s3_writer)
            result["s3_uri"] = uri
        return result

    def monitor(self) -> dict:
        return {"status": "ok", "forms": self.form_types, "companies": len(self._resolve_companies())}
