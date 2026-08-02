"""Signal classification for news and insider trades."""

from __future__ import annotations

import re
from typing import List, Tuple

from connectors.financial.schemas import TradeSignal

BULLISH_KEYWORDS = [
    "beat",
    "beats",
    "exceed",
    "upgrade",
    "upgraded",
    "acquisition",
    "acquire",
    "merger",
    "partnership",
    "approval",
    "approved",
    "record revenue",
    "record profit",
    "surge",
    "soar",
    "jump",
    "rally",
    "breakout",
    "buyback",
    "dividend increase",
    "raised guidance",
    "raises guidance",
    "outperform",
    "strong demand",
    "fda approval",
    "contract win",
    "bullish",
]

BEARISH_KEYWORDS = [
    "miss",
    "misses",
    "missed",
    "downgrade",
    "downgraded",
    "lawsuit",
    "investigation",
    "probe",
    "recall",
    "bankruptcy",
    "fraud",
    "decline",
    "plunge",
    "drop",
    "cut guidance",
    "lowered guidance",
    "layoff",
    "layoffs",
    "warning",
    "profit warning",
    "sec charges",
    "subpoena",
    "short seller",
    "bearish",
    "delisting",
    "default",
]

INSIDER_BUY_CODES = {"P", "A", "M", "C", "X"}
INSIDER_SELL_CODES = {"S", "D", "F", "G", "U"}


def classify_news_signal(title: str, summary: str = "") -> Tuple[TradeSignal, float, List[str], str]:
    text = f"{title} {summary}".lower()
    bullish = [kw for kw in BULLISH_KEYWORDS if kw in text]
    bearish = [kw for kw in BEARISH_KEYWORDS if kw in text]
    if bullish and not bearish:
        strength = min(1.0, 0.35 + 0.1 * len(bullish))
        return TradeSignal.BUY, strength, bullish, f"Bullish keywords: {', '.join(bullish)}"
    if bearish and not bullish:
        strength = min(1.0, 0.35 + 0.1 * len(bearish))
        return TradeSignal.SHORT, strength, bearish, f"Bearish keywords: {', '.join(bearish)}"
    if bullish and bearish:
        return TradeSignal.WATCH, 0.25, bullish + bearish, "Mixed bullish/bearish signals"
    return TradeSignal.HOLD, 0.0, [], "No actionable keywords detected"


def classify_insider_signal(
    transaction_code: str,
    acquired_disposed: str,
    transaction_value: float | None,
    is_officer: bool,
    is_director: bool,
    min_value: float = 100_000,
) -> Tuple[TradeSignal, str]:
    code = (transaction_code or "").upper()
    ad = (acquired_disposed or "").upper()
    value = transaction_value or 0.0
    senior = is_officer or is_director

    if code in INSIDER_BUY_CODES or ad == "A":
        if value >= min_value or (senior and value >= min_value / 5):
            return TradeSignal.BUY, f"Insider purchase ({code}) value=${value:,.0f}"
        return TradeSignal.WATCH, f"Small insider purchase ({code})"
    if code in INSIDER_SELL_CODES or ad == "D":
        if value >= min_value or (senior and value >= min_value / 5):
            return TradeSignal.SHORT, f"Insider sale ({code}) value=${value:,.0f}"
        return TradeSignal.WATCH, f"Small insider sale ({code})"
    return TradeSignal.WATCH, "Non-standard insider transaction"


def extract_tickers(text: str, known_tickers: List[str] | None = None) -> List[str]:
    found = set(re.findall(r"\b[A-Z]{1,5}\b", text or ""))
    if known_tickers:
        allowed = {t.upper() for t in known_tickers}
        found = {t for t in found if t in allowed}
    return sorted(found)
