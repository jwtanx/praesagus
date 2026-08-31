"""
SEC QR (Quarterly) report poller and downloader.
- Polls SEC EDGAR company feeds (Atom) for filings (10-Q, 10-K, 8-K, etc.)
- Downloads filing documents and produces a small JSON report suitable
  for dashboard ingestion (title, accession, filing_date, primary_doc_url,
  snippet of textual content, and list of document links).
- Persists last-seen accession per company to avoid duplicates.
- Supports polling frequency and optional SMTP email notification.

Usage examples:
  python scripts/sec_qr_report.py --companies AAPL:0000320193 MSFT:0000789019 --forms 10-Q 8-K --out /tmp/reports --interval 300 --email
  make sec-qr-report

Requirements: requests, feedparser, beautifulsoup4
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

# Optional local summarization/RAG imports
try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lex_rank import LexRankSummarizer
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    _HAS_RAG = True
except Exception:
    _HAS_RAG = False

import feedparser
import requests
from bs4 import BeautifulSoup
from connectors.financial.sec_client import SecEdgarClient

STATE_DIR = Path(".state")
STATE_DIR.mkdir(exist_ok=True)

USER_AGENT = os.getenv("SEC_USER_AGENT", "PraesagusBot/1.0 (contact: dev@praesagus.example)")


def sec_company_feed(cik: str) -> str:
    # SEC company filings atom feed
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&owner=include&count=40&output=atom"


def load_state(name: str) -> Dict[str, str]:
    path = STATE_DIR / f"{name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(name: str, data: Dict[str, str]):
    path = STATE_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def serpapi_fetch_overview(url_or_query: str):
    """Fetch Google AI Overview via SerpApi. Returns overview text or None."""
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise ValueError("SERPAPI_KEY not set")
    base = "https://serpapi.com/search.json"
    params = {"engine": "google", "q": url_or_query, "api_key": api_key}
    resp = requests.get(base, params=params, timeout=15)
    resp.raise_for_status()
    j = resp.json()
    if j.get("page_token"):
        follow = {"engine": "google_ai_overview", "page_token": j.get("page_token"), "api_key": api_key}
        r2 = requests.get(base, params=follow, timeout=15)
        r2.raise_for_status()
        return r2.json().get("overview_text") or r2.json()
    return j.get("ai_overview") or j


def chunk_text(text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
    if not text:
        return []
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunks.append(text[start:end])
        start = max(end - overlap, end)
    return chunks


def local_summarize_and_rag(text: str, top_k: int = 3) -> str:
    """Perform chunking, build embeddings, retrieve top-k, and summarize with LexRank."""
    chunks = chunk_text(text, chunk_size=3000, overlap=200)
    if not chunks:
        return ""
    # summarize each chunk with lexrank
    summaries = []
    try:
        summarizer = LexRankSummarizer()
        for c in chunks:
            parser = PlaintextParser.from_string(c, Tokenizer("english"))
            sents = summarizer(parser.document, sentences_count=2)
            summaries.append(" ".join(str(s) for s in sents))
    except Exception:
        summaries = [c[:400] for c in chunks]

    # embeddings + retrieval to pick top-k summaries
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        emb_chunks = model.encode(summaries, convert_to_numpy=True)
        query_emb = model.encode(["summarize performance"], convert_to_numpy=True)[0]
        sims = cosine_similarity([query_emb], emb_chunks)[0]
        idx = np.argsort(sims)[-top_k:][::-1]
        selected = "\n\n".join(summaries[i] for i in idx)
        # final summarization pass
        final_parser = PlaintextParser.from_string(selected, Tokenizer("english"))
        final_sents = LexRankSummarizer()(final_parser.document, sentences_count=3)
        return " ".join(str(s) for s in final_sents)
    except Exception:
        return " ".join(summaries)


def fetch_feed_entries(cik: str) -> List[Dict]:
    url = sec_company_feed(cik)
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    feed = feedparser.parse(resp.text)
    entries = []
    for e in feed.entries:
        # feed entries contain title that often includes form type
        entries.append(e)
    return entries


def extract_filing_info(entry) -> Dict:
    # Common fields: title contains form, link href is filing page
    title = entry.get("title", "")
    published = entry.get("published", None)
    link = entry.get("link", None)
    # attempt to derive accession from link
    accession = None
    if link and is_sec_url(link):
        accession = link.rstrip("/").split("/")[-2] if "/Archives/edgar/data/" in link else link
    return {"title": title, "published": published, "link": link, "accession": accession}


def is_sec_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"https"} and parsed.hostname is not None and parsed.hostname.endswith("sec.gov")


def download_primary_document(filing_page_url: str) -> Dict[str, Optional[str]]:
    # Fetch filing page and parse document links. Prefer primary document (htm/html/xbrl)
    headers = {"User-Agent": USER_AGENT}
    if not is_sec_url(filing_page_url):
        raise ValueError(f"Refusing to fetch non-SEC URL: {filing_page_url}")
    resp = requests.get(filing_page_url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # Look for table of documents in EDGAR filing index
    doc_table = soup.find("table", class_="tableFile")
    docs = []
    if doc_table:
        for row in doc_table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            doc_type = cols[3].get_text(strip=True) if len(cols) > 3 else cols[-1].get_text(strip=True)
            doc_name_tag = cols[2].find("a")
            if not doc_name_tag:
                continue
            doc_href = doc_name_tag.get("href")
            doc_url = urljoin("https://www.sec.gov", doc_href)
            if not is_sec_url(doc_url):
                continue
            docs.append({"name": cols[2].get_text(strip=True), "type": doc_type, "url": doc_url})
    # try to get main document text for snippet: pick first html/htm doc
    snippet = None
    primary_url = None
    for d in docs:
        if d["name"].lower().endswith((".htm", ".html")) or d["type"].lower().startswith("10-q") or d["type"].lower().startswith("10-k"):
            primary_url = d["url"]
            break
    if primary_url:
        try:
            if not is_sec_url(primary_url):
                raise ValueError(f"Refusing to fetch non-SEC URL: {primary_url}")
            r2 = requests.get(primary_url, headers=headers, timeout=30)
            r2.raise_for_status()
            text = BeautifulSoup(r2.text, "html.parser").get_text(" ", strip=True)
            snippet = text[:2000]
        except Exception:
            snippet = None
    return {"docs": docs, "primary_url": primary_url, "snippet": snippet}


def build_report_for_company(cik: str, ticker: str, forms: List[str], out_dir: Path) -> List[Dict]:
    state = load_state(f"edgar_{ticker or cik}")
    entries = fetch_feed_entries(cik)
    new_reports = []
    for e in entries:
        info = extract_filing_info(e)
        form_ok = any(f.lower() in info["title"].lower() for f in forms) if forms else True
        accession = info.get("accession")
        if not form_ok or not accession:
            continue
        last_seen = state.get("last_accession")
        if last_seen and accession == last_seen:
            # feed is reverse chronological; stop once we hit last seen
            break
        # get filing page and download primary doc list/snippet
        try:
            details = download_primary_document(info["link"]) if info.get("link") else {}
        except Exception as ex:
            details = {"error": str(ex)}
        client = SecEdgarClient(user_agent=USER_AGENT)
        # attempt to extract authoritative XBRL metrics and compute simple performance deltas
        metrics_summary = {}
        try:
            facts = client.get_company_facts(cik)
            us_gaap = facts.get("facts", {}).get("us-gaap", {})

            def latest_and_prev_for_tags(tags: List[str]):
                for tag in tags:
                    if tag not in us_gaap:
                        continue
                    units = us_gaap[tag].get("units", {})
                    unit_key = next(iter(units.keys()), None)
                    if not unit_key:
                        continue
                    entries_list = units[unit_key]
                    if not entries_list:
                        continue
                    # sort by end/instant, pick latest and previous
                    sorted_entries = sorted(entries_list, key=lambda e: e.get("end") or e.get("instant"))
                    latest = sorted_entries[-1].get("val") if len(sorted_entries) >= 1 else None
                    prev = sorted_entries[-2].get("val") if len(sorted_entries) >= 2 else None
                    return (float(latest) if latest is not None else None, float(prev) if prev is not None else None)
                return (None, None)

            revenue_tags = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"]
            net_income_tags = ["NetIncomeLoss", "ProfitLoss"]
            eps_tags = ["EarningsPerShareBasic", "EarningsPerShareDiluted"]

            rev_latest, rev_prev = latest_and_prev_for_tags(revenue_tags)
            ni_latest, ni_prev = latest_and_prev_for_tags(net_income_tags)
            eps_latest, eps_prev = latest_and_prev_for_tags(eps_tags)

            def pct_change(latest, prev):
                if latest is None or prev is None or prev == 0:
                    return None
                return (latest - prev) / abs(prev) * 100.0

            metrics_summary = {
                "revenue_latest": rev_latest,
                "revenue_prev": rev_prev,
                "revenue_pct_change": pct_change(rev_latest, rev_prev),
                "net_income_latest": ni_latest,
                "net_income_prev": ni_prev,
                "net_income_pct_change": pct_change(ni_latest, ni_prev),
                "eps_latest": eps_latest,
                "eps_prev": eps_prev,
                "eps_pct_change": pct_change(eps_latest, eps_prev),
            }
            changes = [
                value for value in (
                    metrics_summary["revenue_pct_change"],
                    metrics_summary["net_income_pct_change"],
                    metrics_summary["eps_pct_change"],
                ) if value is not None
            ]
            if not changes:
                metrics_summary["performance_label"] = "inline"
            elif sum(value > 0 for value in changes) > sum(value < 0 for value in changes):
                metrics_summary["performance_label"] = "overperformance"
            elif sum(value < 0 for value in changes) > sum(value > 0 for value in changes):
                metrics_summary["performance_label"] = "underperformance"
            else:
                metrics_summary["performance_label"] = "inline"
        except Exception:
            metrics_summary = {}
        report = {
            "ticker": ticker,
            "cik": cik,
            "title": info.get("title"),
            "accession": accession,
            "published": info.get("published"),
            "filing_page": info.get("link"),
            "primary_url": details.get("primary_url"),
            "snippet": details.get("snippet"),
            "docs": details.get("docs"),
            "metrics_summary": metrics_summary,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        new_reports.append(report)
    # persist most recent accession
    if entries:
        first = extract_filing_info(entries[0]).get("accession")
        if first:
            state["last_accession"] = first
            save_state(f"edgar_{ticker or cik}", state)
    # write reports out
    if new_reports:
        out_dir.mkdir(parents=True, exist_ok=True)
        for r in new_reports:
            fname = out_dir / f"{r['ticker']}_{r['accession']}.json"
            fname.write_text(json.dumps(r, indent=2), encoding="utf-8")
    return new_reports


def send_email(smtp_host: str, smtp_port: int, user: str, password: str, to: str, subject: str, body: str):
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--companies", nargs="+", required=True, help="List of TICKER:CIK pairs, e.g. AAPL:0000320193")
    parser.add_argument("--forms", nargs="*", default=["10-Q", "10-K", "8-K"], help="Forms to watch")
    parser.add_argument("--out", default="/tmp/sec_reports", help="Output directory for JSON reports")
    parser.add_argument("--interval", type=int, default=0, help="Polling interval in seconds (0 = run once)")
    parser.add_argument("--email", action="store_true", help="Send email for new reports using SMTP env vars")
    parser.add_argument("--summarize", action="store_true", help="Run local extractive summarization and RAG on filing text")
    parser.add_argument("--use-serpapi", action="store_true", help="Optional: fetch Google AI Overview via SerpApi as fallback (requires SERPAPI_KEY)")
    parser.add_argument("--serpapi-call-limit", type=int, default=5, help="Max SerpApi calls per run when enabled")
    args = parser.parse_args()

    companies = []
    for c in args.companies:
        if ":" in c:
            t, cik = c.split(":", 1)
            companies.append((t.upper(), cik))
        else:
            companies.append((c.upper(), c))

    out_dir = Path(args.out)

    while True:
        aggregated = []
        for ticker, cik in companies:
            try:
                new = build_report_for_company(cik, ticker, args.forms, out_dir)
                # optional summarization and RAG
                if args.summarize:
                    for r in new:
                        text = r.get("snippet") or ""
                        # if snippet is short, attempt to fetch primary_url and include
                        if r.get("primary_url") and len(text) < 1000:
                            try:
                                if is_sec_url(r.get("primary_url")):
                                    resp = requests.get(r.get("primary_url"), headers={"User-Agent": USER_AGENT}, timeout=30)
                                    resp.raise_for_status()
                                    text = BeautifulSoup(resp.text, "html.parser").get_text(" ", strip=True)
                            except Exception:
                                pass
                        summary = None
                        overview = None
                        if _HAS_RAG and text:
                            summary = local_summarize_and_rag(text)
                        else:
                            # fallback simple truncation
                            summary = (text[:1000] + "...") if text else None
                        r["summary"] = summary
                        # optionally use SerpApi as a final fallback
                        if args.use_serpapi and os.getenv("SERPAPI_KEY"):
                            serpapi_cache = load_state("serpapi_cache")
                            key = r.get("accession") or r.get("primary_url") or r.get("filing_page")
                            if key and not serpapi_cache.get(key) and args.serpapi_call_limit > 0:
                                try:
                                    overview = serpapi_fetch_overview(r.get("primary_url") or r.get("filing_page"))
                                    serpapi_cache[key] = overview
                                    save_state("serpapi_cache", serpapi_cache)
                                except Exception:
                                    overview = None
                            else:
                                overview = serpapi_cache.get(key)
                        r["ai_overview"] = overview
                aggregated.extend(new)
            except Exception as ex:
                print("Error for", ticker, ex)
        if aggregated and args.email:
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_pass = os.getenv("SMTP_PASS")
            to = os.getenv("ALERT_EMAIL")
            if smtp_host and smtp_user and smtp_pass and to:
                subj = f"SEC filings: {len(aggregated)} new filings"
                body = json.dumps(aggregated, indent=2)
                try:
                    send_email(smtp_host, smtp_port, smtp_user, smtp_pass, to, subj, body)
                except Exception as ex:
                    print("Email send failed", ex)
        if args.interval <= 0:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
