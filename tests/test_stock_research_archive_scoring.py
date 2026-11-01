import csv
import json
import math
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stock-research"
sys.path.insert(0, str(SCRIPT))
import score_forecast_archive as archive
from inference import converted_quantiles


def make_files(root: Path, *, future_input=False):
    root.mkdir(parents=True, exist_ok=True)
    issue = 1_800_000_000_000
    input_path = root / "input.csv"
    actual_path = root / "actual.csv"
    instrument_path = root / "instruments.json"
    prediction_path = root / "predictions.json"
    config_path = root / "config.json"
    input_fields = ["code", "session_date", "close", "currency", "adjustment", "known_at_ms"]
    actual_fields = ["code", "session_date", "open", "high", "low", "close", "currency", "adjustment", "known_at_ms", "completion_status"]
    with input_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=input_fields)
        writer.writeheader()
        writer.writerow({"code": "US.X", "session_date": "2026-10-28", "close": "100", "currency": "USD", "adjustment": "forward-excluding-dividends", "known_at_ms": issue + (1 if future_input else -10)})
    with actual_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=actual_fields)
        writer.writeheader()
        writer.writerow({"code": "US.X", "session_date": "2026-10-29", "open": "100", "high": "103", "low": "98", "close": "102", "currency": "USD", "adjustment": "forward-excluding-dividends", "known_at_ms": issue + 500, "completion_status": "completed"})
    instrument_path.write_text(json.dumps([{"code": "US.X", "stock_id": 7}]))
    relative = [[-.04, -.02, .03], [0, .02, .05], [-.03, .01, .04]]
    model = converted_quantiles(relative, 100)
    baseline = converted_quantiles(relative, 100)
    forecast = {
        "code": "US.X", "horizon": "1d", "origin": "2026-10-28", "issued_at_ms": issue,
        "status": "available", "stock_id": 7,
        "window": {"end": "2026-10-29", "sessions": ["2026-10-29"], "first_open_ms": issue + 100, "last_close_ms": issue + 1000},
        "reference": {"close": 100, "currency": "USD", "adjustment": "forward-excluding-dividends"},
        "model": model, "baseline": baseline,
    }
    prediction_path.write_text(json.dumps({"issued_at_ms": issue, "model_ref": {"model_sha256": "a" * 64}, "forecasts": [forecast]}))
    config_path.write_text(json.dumps({"schema_version": 1, "actual_history_csv": str(actual_path), "instrument_map_json": str(instrument_path), "bundles": [{"name": "sample", "predictions_json": str(prediction_path), "input_history_csv": str(input_path)}]}))
    return config_path


def test_score_archive_writes_hash_bound_report_and_keeps_generations_separate(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    config = make_files(tmp_path / "private")
    result, json_path, md_path = archive.score_archive(config, tmp_path / "private" / "out", repository_root=repo)
    assert result["eligible_forecasts"] == 1
    assert result["excluded_forecasts"] == 0
    assert result["model_generations_separate"][0]["model_sha256"] == "a" * 64
    assert json_path.is_file() and md_path.is_file()
    assert "no confidence intervals" in result["limitations"][3].lower()
    row = result["per_forecast"][0]
    assert row["model_abs_error"] == pytest.approx(abs(math.log(1.02) - 0.01))


def test_score_archive_excludes_bundle_with_future_known_inputs(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    config = make_files(tmp_path / "private", future_input=True)
    result, _, _ = archive.score_archive(config, tmp_path / "private" / "out", repository_root=repo)
    assert result["eligible_forecasts"] == 0
    assert result["excluded"][0]["reason"] == "bundle-contains-future-known-input"


def test_score_archive_refuses_output_inside_repository_and_overwrite(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    config = make_files(tmp_path / "private")
    with pytest.raises(ValueError, match="outside the Git repository"):
        archive.score_archive(config, repo / "reports", repository_root=repo)
    output = tmp_path / "private" / "out"
    output.mkdir()
    (output / "existing.json").write_text("preserve")
    with pytest.raises(ValueError, match="never overwritten"):
        archive.score_archive(config, output, repository_root=repo)
