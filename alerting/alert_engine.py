"""Simple alert engine that loads signals and sends webhook notifications."""

import json
import requests
import os


def load_signals(path: str):
    with open(path) as f:
        return json.load(f)


def send_webhook(url: str, payload: dict):
    try:
        resp = requests.post(url, json=payload, timeout=5)
        return resp.status_code
    except Exception:
        return None


def run_alerts(signals_path: str, webhook_url: str, threshold: float = 0.8):
    data = load_signals(signals_path)
    for t in data.get("trends", []):
        if t.get("score", 0) >= threshold:
            payload = {"entity": t["entity"], "score": t["score"], "evidence": t.get("evidence", [])}
            send_webhook(webhook_url, payload)


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "..", "data", "signals.json")
    webhook = os.getenv("PRAESAGUS_ALERT_WEBHOOK")
    if not webhook:
        print("Set PRAESAGUS_ALERT_WEBHOOK to enable alert delivery")
    else:
        run_alerts(path, webhook)
