"""Webhook alerts for insider trades and news signals."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests


def send_webhook(url: str, payload: dict, timeout: float = 5.0) -> Optional[int]:
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        return resp.status_code
    except Exception:
        return None


def send_insider_alert(webhook_url: str, trade: Dict[str, Any]) -> Optional[int]:
    payload = {
        "alert_type": "insider_trade",
        "severity": "high" if trade.get("signal") in {"buy", "short"} else "medium",
        "ticker": trade.get("ticker"),
        "issuer_name": trade.get("issuer_name"),
        "insider_name": trade.get("reporting_owner_name"),
        "insider_title": trade.get("officer_title") or trade.get("reporting_owner_title"),
        "is_officer": trade.get("is_officer"),
        "is_director": trade.get("is_director"),
        "is_ten_percent_owner": trade.get("is_ten_percent_owner"),
        "transaction_date": trade.get("transaction_date"),
        "acceptance_datetime": trade.get("acceptance_datetime"),
        "transaction_code": trade.get("transaction_code"),
        "transaction_code_label": trade.get("transaction_code_label"),
        "shares": trade.get("shares"),
        "price_per_share": trade.get("price_per_share"),
        "transaction_value": trade.get("transaction_value"),
        "shares_owned_following": trade.get("shares_owned_following"),
        "acquired_disposed": trade.get("acquired_disposed"),
        "signal": trade.get("signal"),
        "signal_reason": trade.get("signal_reason"),
        "latency_seconds": trade.get("latency_seconds"),
        "form_url": trade.get("form_url"),
        "document_url": trade.get("document_url"),
        "message": (
            f"INSIDER {trade.get('signal', '').upper()}: {trade.get('reporting_owner_name')} "
            f"({trade.get('officer_title') or 'insider'}) "
            f"{trade.get('transaction_code_label')} {trade.get('shares')} shares of "
            f"{trade.get('ticker')} @ ${trade.get('price_per_share')} "
            f"filed {trade.get('acceptance_datetime')}"
        ),
    }
    return send_webhook(webhook_url, payload)


def send_news_alert(webhook_url: str, article: Dict[str, Any]) -> Optional[int]:
    payload = {
        "alert_type": "company_news",
        "severity": "high" if float(article.get("signal_strength") or 0) >= 0.5 else "medium",
        "ticker": article.get("ticker"),
        "title": article.get("title"),
        "summary": article.get("summary"),
        "link": article.get("link"),
        "source_name": article.get("source_name"),
        "published_at": article.get("published_at"),
        "first_seen_at": article.get("first_seen_at"),
        "latency_ms": article.get("latency_ms"),
        "signal": article.get("signal"),
        "signal_strength": article.get("signal_strength"),
        "signal_reason": article.get("signal_reason"),
        "keywords_matched": article.get("keywords_matched"),
        "message": (
            f"NEWS {article.get('signal', '').upper()}: [{article.get('ticker')}] "
            f"{article.get('title')} (latency {article.get('latency_ms')}ms)"
        ),
    }
    return send_webhook(webhook_url, payload)
