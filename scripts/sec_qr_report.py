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

Requirements: requests, feedparser, beautifulsoup4
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

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
    if link:
        # link example: https://www.sec.gov/Archives/edgar/data/320193/000032019323000010/0000320193-23-000010-index.htm
        accession = link.rstrip("/").split("/")[-2] if "/Archives/edgar/data/" in link else link
    return {"title": title, "published": published, "link": link, "accession": accession}


def download_primary_document(filing_page_url: str) -> Dict[str, Optional[str]]:
    # Fetch filing page and parse document links. Prefer primary document (htm/html/xbrl)
    headers = {"User-Agent": USER_AGENT}
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
            doc_url = f"https://www.sec.gov{doc_href}" if doc_href.startswith("/") else doc_href
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
