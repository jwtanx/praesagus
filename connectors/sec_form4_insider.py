"""SEC Form 4 insider trading connector with first-second filing detection."""

from __future__ import annotations

from datetime import datetime
from typing import Iterator, List, Optional

from connectors.base import NormalizedRecord, RawRecord
from connectors.financial.schemas import INSIDER_FILTER_FIELDS, InsiderTradeRecord, TradeSignal
from connectors.financial.sec_client import SecEdgarClient
from connectors.financial.signals import classify_insider_signal
from connectors.financial.storage import upsert_records


class SecForm4InsiderConnector:
    """Monitor SEC Form 4 filings for insider buy/sell signals."""

    def __init__(
        self,
        tickers: Optional[List[str]] = None,
        watch_all: bool = False,
        atom_count: int = 100,
        min_transaction_value: float = 100_000,
        user_agent: Optional[str] = None,
    ):
        self.client = SecEdgarClient(user_agent=user_agent)
        self.tickers = {t.upper() for t in (tickers or [])}
        self.watch_all = watch_all
        self.atom_count = atom_count
        self.min_transaction_value = min_transaction_value

    def authenticate(self) -> None:
        self.client.load_ticker_map()

    def discover(self) -> list[dict]:
        return [{"tickers": sorted(self.tickers), "watch_all": self.watch_all}]

    def fetch(
        self,
        start: datetime,
        end: datetime,
        cursor: Optional[str] = None,
    ) -> Iterator[RawRecord]:
        entries = self.client.fetch_form4_atom_feed(count=self.atom_count)
        for entry in entries:
            cik = entry.get("cik", "")
            if not cik:
                continue
            try:
                _, ticker, company_name = self.client.resolve_company(cik)
            except ValueError:
                ticker, company_name = "", ""
            if self.tickers and ticker and ticker not in self.tickers and not self.watch_all:
                continue
            accession = entry.get("accession_number", "")
            if not accession:
                continue
            xml_url = self.client.find_form4_xml_url(cik, accession)
            if not xml_url:
                continue
            try:
                transactions = self.client.parse_form4_xml(xml_url)
            except Exception:
                continue
            acceptance = entry.get("updated", "")
            for idx, txn in enumerate(transactions):
                payload = {
                    "cik": cik,
                    "ticker": ticker or txn.get("issuer_ticker", ""),
                    "company_name": company_name or txn.get("issuer_name", ""),
                    "accession_number": accession,
                    "acceptance_datetime": acceptance,
                    "filing_date": acceptance[:10] if acceptance else "",
                    "form_url": entry.get("link", ""),
                    "document_url": xml_url,
                    "transaction_index": idx,
                    **txn,
                }
                yield RawRecord(payload=payload)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        signal, reason = classify_insider_signal(
            transaction_code=p.get("transaction_code", ""),
            acquired_disposed=p.get("acquired_disposed", ""),
            transaction_value=p.get("transaction_value"),
            is_officer=bool(p.get("is_officer")),
            is_director=bool(p.get("is_director")),
            min_value=self.min_transaction_value,
        )
        source_id = f"{p['accession_number']}_{p.get('transaction_index', 0)}_{p.get('reporting_owner_cik', '')}"
        latency = self.client.compute_latency_seconds(p.get("acceptance_datetime", ""))
        record = InsiderTradeRecord(
            source_id=source_id,
            cik=p["cik"],
            ticker=p.get("ticker") or p.get("issuer_ticker", ""),
            issuer_name=p.get("issuer_name") or p.get("company_name", ""),
            accession_number=p["accession_number"],
            filing_date=p.get("filing_date", ""),
            acceptance_datetime=p.get("acceptance_datetime", ""),
            reporting_owner_cik=p.get("reporting_owner_cik", ""),
            reporting_owner_name=p.get("reporting_owner_name", ""),
            reporting_owner_title=p.get("reporting_owner_title"),
            is_director=bool(p.get("is_director")),
            is_officer=bool(p.get("is_officer")),
            is_ten_percent_owner=bool(p.get("is_ten_percent_owner")),
            is_other=bool(p.get("is_other")),
            officer_title=p.get("officer_title"),
            transaction_date=p.get("transaction_date", ""),
            transaction_code=p.get("transaction_code", ""),
            transaction_code_label=p.get("transaction_code_label", ""),
            equity_symbol=p.get("equity_symbol"),
            shares=float(p.get("shares") or 0),
            price_per_share=p.get("price_per_share"),
            transaction_value=p.get("transaction_value"),
            shares_owned_following=p.get("shares_owned_following"),
            ownership_nature=p.get("ownership_nature"),
            acquired_disposed=p.get("acquired_disposed", ""),
            form_url=p.get("form_url", ""),
            document_url=p.get("document_url", ""),
            signal=signal,
            signal_reason=reason,
            latency_seconds=latency,
        )
        metadata = record.to_dict()
        metadata["investable_fields"] = INSIDER_FILTER_FIELDS
        text = (
            f"{record.reporting_owner_name} ({record.officer_title or 'insider'}) "
            f"{record.transaction_code_label} {record.shares} shares of {record.ticker} "
            f"on {record.transaction_date}. Signal: {record.signal.value}."
        )
        return NormalizedRecord(
            source="sec_form4_insider",
            source_id=source_id,
            timestamp=datetime.utcnow(),
            text=text,
            entities=[
                {"type": "ticker", "value": record.ticker},
                {"type": "insider", "value": record.reporting_owner_name},
            ],
            metadata=metadata,
            provenance={"connector": "sec_form4_insider", "ingest_ts": datetime.utcnow().isoformat()},
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
        merged = upsert_records("insider_trades", [record], data_dir=data_dir)
        result = {"stored": len(merged), "source_id": record.get("source_id"), "signal": record.get("signal")}
        if s3_bucket and s3_writer:
            from connectors.financial.storage import store_to_s3

            uri = store_to_s3(s3_bucket, "insider_trades", merged, s3_writer=s3_writer)
            result["s3_uri"] = uri
        return result

    def monitor(self) -> dict:
        return {"status": "ok", "watch_all": self.watch_all, "tickers": sorted(self.tickers)}
