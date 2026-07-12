import json
import os
from unittest.mock import patch

from alerting.alert_engine import run_alerts


def test_alert_engine_sends_webhook(tmp_path, monkeypatch):
    signals = {"trends": [{"entity": "p1", "score": 0.95, "evidence": []}]}
    file = tmp_path / "signals.json"
    file.write_text(json.dumps(signals))

    called = {}

    def fake_post(url, json=None, timeout=5):
        called["url"] = url
        class R:
            status_code = 200
        return R()

    monkeypatch.setattr("requests.post", fake_post)
    run_alerts(str(file), "http://example.local/webhook", threshold=0.8)
    assert called.get("url") == "http://example.local/webhook"
