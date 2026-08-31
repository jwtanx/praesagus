"""SEC EDGAR REST API client — legal, free, public data from data.sec.gov."""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urljoin

import feedparser
import requests

from connectors.financial.schemas import FinancialMetrics

# SEC fair-access policy: identify your application; max ~10 req/s.
DEFAULT_USER_AGENT = "Praesagus FinancialBot contact@praesagus.example"

FORM4_TRANSACTION_CODES = {
    "P": "Open market or private purchase",
    "S": "Open market or private sale",
    "A": "Grant, award, or other acquisition",
    "D": "Disposition to issuer",
    "F": "Payment of exercise price or tax liability",
    "G": "Gift",
    "M": "Exercise or conversion of derivative",
    "C": "Conversion of derivative",
    "X": "Exercise of in-the-money derivative",
    "J": "Other acquisition or disposition",
    "K": "Equity swap or similar instrument",
    "U": "Disposition pursuant to tender offer",
    "W": "Acquisition or disposition by will or laws of descent",
    "Z": "Deposit into or withdrawal from voting trust",
}

XBRL_METRIC_MAP = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "eps_basic": ["EarningsPerShareBasic"],
    "eps_diluted": ["EarningsPerShareDiluted"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "stockholders_equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "long_term_debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "short_term_debt": ["ShortTermBorrowings", "DebtCurrent"],
    "shares_outstanding": ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"],
    "research_and_development": ["ResearchAndDevelopmentExpense"],
    "goodwill": ["Goodwill"],
}


class SecEdgarClient:
    """Client for SEC EDGAR public APIs with rate limiting and CIK normalization."""

    def __init__(self, user_agent: Optional[str] = None, min_request_interval: float = 0.11):
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.min_request_interval = min_request_interval
        self._last_request_at = 0.0
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": "data.sec.gov",
            }
        )
        self._ticker_map: Optional[Dict[str, Dict[str, str]]] = None
        self._facts_cache: Dict[str, Dict[str, Any]] = {}

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self._last_request_at = time.monotonic()

    def _get(self, url: str, host: str = "data.sec.gov") -> requests.Response:
        self._rate_limit()
        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate", "Host": host}
        resp = self.session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp

    @staticmethod
    def normalize_cik(cik: str) -> str:
        digits = re.sub(r"\D", "", cik or "")
        return digits.zfill(10)

    def load_ticker_map(self) -> Dict[str, Dict[str, str]]:
        if self._ticker_map is not None:
            return self._ticker_map
        url = "https://www.sec.gov/files/company_tickers.json"
        self._rate_limit()
        resp = self.session.get(url, headers={"User-Agent": self.user_agent}, timeout=30)
        resp.raise_for_status()
        raw = resp.json()
        mapping: Dict[str, Dict[str, str]] = {}
        for entry in raw.values():
            ticker = str(entry.get("ticker", "")).upper()
            cik = self.normalize_cik(str(entry.get("cik_str", "")))
            mapping[ticker] = {"cik": cik, "title": entry.get("title", "")}
            mapping[cik] = {"ticker": ticker, "title": entry.get("title", "")}
        self._ticker_map = mapping
        return mapping

    def resolve_company(self, ticker_or_cik: str) -> Tuple[str, str, str]:
        """Return (cik, ticker, company_name)."""
        token = (ticker_or_cik or "").strip().upper()
        mapping = self.load_ticker_map()
        if token.isdigit():
            cik = self.normalize_cik(token)
            info = mapping.get(cik, {})
            return cik, info.get("ticker", ""), info.get("title", "")
        info = mapping.get(token, {})
        cik = info.get("cik", "")
        if not cik:
            raise ValueError(f"Unknown ticker or CIK: {ticker_or_cik}")
        return cik, token, info.get("title", "")

    def get_submissions(self, cik: str) -> Dict[str, Any]:
        cik = self.normalize_cik(cik)
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        return self._get(url).json()

    def get_company_facts(self, cik: str) -> Dict[str, Any]:
        cik = self.normalize_cik(cik)
        if cik in self._facts_cache:
            return self._facts_cache[cik]
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        facts = self._get(url).json()
        self._facts_cache[cik] = facts
        return facts

    def iter_filings(
        self,
        cik: str,
        form_types: Optional[List[str]] = None,
        limit: int = 40,
    ) -> Iterator[Dict[str, Any]]:
        submissions = self.get_submissions(cik)
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        form_types_set = {f.upper() for f in (form_types or [])}
        count = 0
        for idx, form in enumerate(forms):
            if form_types_set and form.upper() not in form_types_set:
                continue
            def row(name: str, default: Any = "") -> Any:
                values = recent.get(name, []) or []
                return values[idx] if idx < len(values) else default

            accession = row("accessionNumber")
            if not accession:
                continue
            accession_no_dashes = accession.replace("-", "")
            primary_doc = row("primaryDocument")
            if not primary_doc:
                continue
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_no_dashes}/{primary_doc}"
            )
            yield {
                "form_type": form,
                "filing_date": row("filingDate"),
                "acceptance_datetime": row("acceptanceDateTime"),
                "report_date": row("reportDate") or None,
                "accession_number": accession,
                "primary_document": primary_doc,
                "filing_url": filing_url,
                "description": row("primaryDocDescription") or None,
                "is_amendment": form.endswith("/A"),
            }
            count += 1
            if count >= limit:
                break

    def extract_metrics(self, cik: str, as_of: Optional[str] = None) -> FinancialMetrics:
        facts = self.get_company_facts(cik)
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        metrics = FinancialMetrics()
        for field_name, tags in XBRL_METRIC_MAP.items():
            for tag in tags:
                if tag not in us_gaap:
                    continue
                units = us_gaap[tag].get("units", {})
                unit_key = next(iter(units.keys()), None)
                if not unit_key:
                    continue
                entries = units[unit_key]
                if not entries:
                    continue
                eligible = [
                    entry for entry in entries
                    if not as_of or (
                        (entry.get("filed") or "") <= as_of
                        and (entry.get("end") or entry.get("instant") or "") <= as_of
                    )
                ]
                if not eligible:
                    continue
                latest = max(
                    eligible,
                    key=lambda e: (e.get("end", e.get("instant", "")), e.get("filed", "")),
                )
                value = latest.get("val")
                setattr(metrics, field_name, float(value) if value is not None else None)
                if not metrics.period_end:
                    metrics.period_end = latest.get("end") or latest.get("instant")
                    metrics.fiscal_year = str(latest.get("fy", "")) or None
                    metrics.fiscal_period = latest.get("fp")
                    metrics.unit = unit_key
                break

        if metrics.revenue is not None and metrics.revenue != 0 and metrics.gross_profit is not None:
            metrics.gross_margin = round(metrics.gross_profit / metrics.revenue, 4)
        if metrics.revenue is not None and metrics.revenue != 0 and metrics.operating_income is not None:
            metrics.operating_margin = round(metrics.operating_income / metrics.revenue, 4)
        if metrics.revenue is not None and metrics.revenue != 0 and metrics.net_income is not None:
            metrics.net_margin = round(metrics.net_income / metrics.revenue, 4)
        if metrics.stockholders_equity is not None and metrics.stockholders_equity != 0 and metrics.net_income is not None:
            metrics.roe = round(metrics.net_income / metrics.stockholders_equity, 4)
        if metrics.total_assets is not None and metrics.total_assets != 0 and metrics.net_income is not None:
            metrics.roa = round(metrics.net_income / metrics.total_assets, 4)
        if metrics.total_liabilities and metrics.stockholders_equity and metrics.stockholders_equity != 0:
            metrics.debt_to_equity = round(metrics.total_liabilities / metrics.stockholders_equity, 4)

        return metrics

    def fetch_form4_atom_feed(self, count: int = 100) -> List[Dict[str, Any]]:
        url = (
            "https://www.sec.gov/cgi-bin/browse-edgar"
            f"?action=getcurrent&type=4&company=&dateb=&owner=include&count={count}&output=atom"
        )
        self._rate_limit()
        resp = self.session.get(url, headers={"User-Agent": self.user_agent}, timeout=30)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        entries = []
        for entry in feed.entries:
            summary = getattr(entry, "summary", "") or ""
            title = getattr(entry, "title", "") or ""
            link = getattr(entry, "link", "") or ""
            updated = getattr(entry, "updated", "") or getattr(entry, "published", "")
            accession_match = re.search(r"accession-number=([\d-]+)", link) or re.search(
                r"/([\d-]{18})/", link
            )
            accession = accession_match.group(1) if accession_match else ""
            cik_match = re.search(r"CIK=(\d+)", link) or re.search(r"/data/(\d+)/", link)
            cik = self.normalize_cik(cik_match.group(1)) if cik_match else ""
            entries.append(
                {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "updated": updated,
                    "accession_number": accession,
                    "cik": cik,
                }
            )
        return entries

    def fetch_filing_index(self, cik: str, accession_number: str) -> Dict[str, Any]:
        accession_no_dashes = accession_number.replace("-", "")
        base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_no_dashes}/"
        index_url = urljoin(base, "index.json")
        self._rate_limit()
        resp = self.session.get(index_url, headers={"User-Agent": self.user_agent, "Host": "www.sec.gov"}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def find_form4_xml_url(self, cik: str, accession_number: str) -> Optional[str]:
        try:
            index = self.fetch_filing_index(cik, accession_number)
        except Exception:
            return None
        items = index.get("directory", {}).get("item", [])
        for item in items:
            name = item.get("name", "")
            if name.endswith(".xml") and "form4" in name.lower():
                accession_no_dashes = accession_number.replace("-", "")
                return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_no_dashes}/{name}"
        for item in items:
            name = item.get("name", "")
            if name.endswith(".xml"):
                accession_no_dashes = accession_number.replace("-", "")
                return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_no_dashes}/{name}"
        return None

    def parse_form4_xml(self, xml_url: str) -> List[Dict[str, Any]]:
        self._rate_limit()
        resp = self.session.get(xml_url, headers={"User-Agent": self.user_agent, "Host": "www.sec.gov"}, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        def find_text(path: str, node: ET.Element) -> Optional[str]:
            el = node.find(f"{ns}{path}")
            return el.text.strip() if el is not None and el.text else None

        issuer_name = find_text("issuer/issuerName", root) or ""
        issuer_cik = self.normalize_cik(find_text("issuer/issuerCik", root) or "")
        issuer_ticker = find_text("issuer/issuerTradingSymbol", root) or ""

        owner = root.find(f"{ns}reportingOwner")
        owner_name = ""
        owner_cik = ""
        owner_title = None
        is_director = False
        is_officer = False
        is_ten_percent = False
        is_other = False
        officer_title = None
        if owner is not None:
            owner_name = find_text("reportingOwnerId/rptOwnerName", owner) or ""
            owner_cik = find_text("reportingOwnerId/rptOwnerCik", owner) or ""
            rel = owner.find(f"{ns}reportingOwnerRelationship")
            if rel is not None:
                is_director = (find_text("isDirector", rel) or "0") == "1"
                is_officer = (find_text("isOfficer", rel) or "0") == "1"
                is_ten_percent = (find_text("isTenPercentOwner", rel) or "0") == "1"
                is_other = (find_text("isOther", rel) or "0") == "1"
                officer_title = find_text("officerTitle", rel)

        period = find_text("periodOfReport", root) or ""
        transactions: List[Dict[str, Any]] = []

        for txn in root.findall(f".//{ns}nonDerivativeTransaction"):
            code = find_text("transactionCoding/transactionCode", txn) or ""
            shares_text = find_text("transactionAmounts/transactionShares/value", txn) or "0"
            price_text = find_text("transactionAmounts/transactionPricePerShare/value", txn) or None
            acquired = find_text("transactionAmounts/transactionAcquiredDisposedCode/value", txn) or ""
            shares_owned = find_text("postTransactionAmounts/sharesOwnedFollowingTransaction/value", txn)
            ownership = find_text("ownershipNature/directOrIndirectOwnership/value", txn)
            symbol = find_text("securityTitle/value", txn)
            try:
                shares = float(shares_text)
            except ValueError:
                shares = 0.0
            price = float(price_text) if price_text else None
            value = shares * price if price is not None else None
            transactions.append(
                {
                    "issuer_name": issuer_name,
                    "issuer_cik": issuer_cik,
                    "issuer_ticker": issuer_ticker,
                    "reporting_owner_name": owner_name,
                    "reporting_owner_cik": owner_cik,
                    "reporting_owner_title": owner_title,
                    "is_director": is_director,
                    "is_officer": is_officer,
                    "is_ten_percent_owner": is_ten_percent,
                    "is_other": is_other,
                    "officer_title": officer_title,
                    "transaction_date": find_text("transactionDate/value", txn) or period,
                    "transaction_code": code,
                    "transaction_code_label": FORM4_TRANSACTION_CODES.get(code, "Unknown"),
                    "equity_symbol": symbol,
                    "shares": shares,
                    "price_per_share": price,
                    "transaction_value": value,
                    "shares_owned_following": float(shares_owned) if shares_owned else None,
                    "ownership_nature": ownership,
                    "acquired_disposed": acquired,
                }
            )
        return transactions

    @staticmethod
    def compute_latency_seconds(acceptance_datetime: str) -> Optional[float]:
        if not acceptance_datetime:
            return None
        try:
            filed_at = datetime.fromisoformat(acceptance_datetime.replace("Z", "+00:00"))
            if filed_at.tzinfo is None:
                filed_at = filed_at.replace(tzinfo=timezone.utc)
            return max(0.0, (datetime.now(timezone.utc) - filed_at).total_seconds())
        except ValueError:
            return None
