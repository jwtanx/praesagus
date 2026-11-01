#!/usr/bin/env python3
"""Generate a private, reproducible benchmark report from saved forecast bundles.

This scores one-session forecasts against later actual OHLC rows. It never fits
models, downloads market data, publishes outputs, or combines model generations.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

from evaluation import forecast_metrics
from model import pinball

SCHEMA_VERSION = 1
REQUIRED_ACTUAL_FIELDS = {"code", "session_date", "open", "high", "low", "close", "currency", "adjustment", "known_at_ms"}
REQUIRED_INPUT_FIELDS = {"code", "session_date", "close", "currency", "adjustment", "known_at_ms"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, (dict, list)):
        raise ValueError(f"expected JSON object or list: {path}")
    return value


def load_csv(path: Path, required: set[str]):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"CSV missing required columns {missing}: {path}")
        rows = list(reader)
    return rows


def typed_identity_map(value):
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict):
        rows = [dict(v, code=k) for k, v in value.items() if isinstance(v, dict)]
    else:
        raise ValueError("instrument_map_json must be a list or code-to-instrument object")
    result = {}
    for row in rows:
        code = row.get("code")
        if not isinstance(code, str) or code in result or "stock_id" not in row:
            raise ValueError("instrument map has missing/duplicate code or stock_id")
        result[code] = row["stock_id"]
    return result


def metric_summary(rows, prefix):
    if not rows:
        return {"n": 0}
    hits = sum(bool(row[f"{prefix}_direction_hit"]) for row in rows)
    qloss = {q: statistics.mean(row[f"{prefix}_pinball"][q] for row in rows) for q in ("q05", "q50", "q95")}
    covered = sum(bool(row[f"{prefix}_interval_covered"]) for row in rows)
    return {
        "n": len(rows),
        "direction_hits": hits,
        "direction_hit_rate": hits / len(rows),
        "median_absolute_log_return_error": statistics.median(row[f"{prefix}_abs_error"] for row in rows),
        "mean_pinball_loss": qloss,
        "central_90_coverage_count": covered,
        "central_90_coverage": covered / len(rows),
    }


def score_archive(config_path: Path, output_dir: Path, *, repository_root: Path):
    config_path = config_path.expanduser().resolve(strict=True)
    output_dir = output_dir.expanduser().resolve()
    repository_root = repository_root.resolve(strict=True)
    if config_path == repository_root or repository_root in config_path.parents:
        raise ValueError("benchmark config must be outside the Git repository")
    if output_dir == repository_root or repository_root in output_dir.parents:
        raise ValueError("benchmark outputs must be outside the Git repository")
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise ValueError("output directory must be new or empty; existing results are never overwritten")

    config = load_json(config_path)
    if not isinstance(config, dict) or config.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported archive config schema")
    bundles = config.get("bundles")
    if not isinstance(bundles, list) or not bundles:
        raise ValueError("archive config requires a nonempty bundles list")

    def source_path(key):
        raw = config.get(key)
        if not isinstance(raw, str) or not Path(raw).is_absolute():
            raise ValueError(f"{key} must be an absolute private path")
        path = Path(raw).expanduser().resolve(strict=True)
        if repository_root == path or repository_root in path.parents:
            raise ValueError(f"{key} must be outside the Git repository")
        return path

    actual_path = source_path("actual_history_csv")
    instrument_path = source_path("instrument_map_json")
    actual_rows = load_csv(actual_path, REQUIRED_ACTUAL_FIELDS)
    instrument_ids = typed_identity_map(load_json(instrument_path))
    actual = {}
    for row in actual_rows:
        key = (row["code"], row["session_date"])
        if key in actual:
            raise ValueError(f"duplicate actual row: {key}")
        actual[key] = row

    sources = [{"role": "actual_history", "sha256": sha256(actual_path), "rows": len(actual_rows)},
               {"role": "instrument_map", "sha256": sha256(instrument_path), "rows": len(instrument_ids)}]
    scored = []
    excluded = []
    bundle_names = set()
    for bundle in bundles:
        if not isinstance(bundle, dict) or not isinstance(bundle.get("name"), str) or not bundle["name"].strip():
            raise ValueError("each bundle requires a nonempty name")
        name = bundle["name"].strip()
        if name in bundle_names:
            raise ValueError(f"duplicate bundle name: {name}")
        bundle_names.add(name)
        def bundle_path(key):
            raw = bundle.get(key)
            if not isinstance(raw, str) or not Path(raw).is_absolute():
                raise ValueError(f"bundle {name}: {key} must be an absolute private path")
            path = Path(raw).expanduser().resolve(strict=True)
            if repository_root == path or repository_root in path.parents:
                raise ValueError(f"bundle {name}: {key} must be outside the Git repository")
            return path
        prediction_path = bundle_path("predictions_json")
        inputs_path = bundle_path("input_history_csv")
        predictions = load_json(prediction_path)
        if not isinstance(predictions, dict) or not isinstance(predictions.get("forecasts"), list):
            raise ValueError(f"bundle {name}: invalid forecast payload")
        issued = predictions.get("issued_at_ms")
        if type(issued) is not int or issued <= 0:
            raise ValueError(f"bundle {name}: invalid issued_at_ms")
        input_rows = load_csv(inputs_path, REQUIRED_INPUT_FIELDS)
        inputs = {}
        for row in input_rows:
            key = (row["code"], row["session_date"])
            if key in inputs:
                raise ValueError(f"bundle {name}: duplicate input row {key}")
            inputs[key] = row
        future_known_inputs = [row for row in input_rows if int(row["known_at_ms"]) > issued]
        model_ref = predictions.get("model_ref")
        model_sha = model_ref.get("model_sha256") if isinstance(model_ref, dict) else None
        if not isinstance(model_sha, str) or len(model_sha) != 64:
            raise ValueError(f"bundle {name}: model SHA-256 missing")
        sources.extend([
            {"role": "predictions", "bundle": name, "sha256": sha256(prediction_path), "rows": len(predictions["forecasts"])},
            {"role": "input_history", "bundle": name, "sha256": sha256(inputs_path), "rows": len(input_rows)},
        ])
        for forecast in predictions["forecasts"]:
            code = forecast.get("code") if isinstance(forecast, dict) else None
            target_session = (forecast.get("window") or {}).get("end") if isinstance(forecast, dict) else None
            reason = None
            try:
                if future_known_inputs:
                    reason = "bundle-contains-future-known-input"
                elif forecast.get("horizon") != "1d":
                    reason = "outside-one-session-scope"
                elif forecast.get("status") != "available":
                    reason = "forecast-unavailable"
                elif type(forecast.get("issued_at_ms")) is not int or forecast["issued_at_ms"] != issued:
                    reason = "forecast-issue-time-mismatch"
                elif type(forecast.get("window", {}).get("first_open_ms")) is not int or issued >= forecast["window"]["first_open_ms"]:
                    reason = "forecast-not-issued-before-target-open"
                elif forecast.get("window", {}).get("sessions") != [target_session]:
                    reason = "not-a-single-session-target"
                elif (code, forecast.get("origin")) not in inputs:
                    reason = "origin-input-missing"
                elif code not in instrument_ids or type(instrument_ids[code]) is not type(forecast.get("stock_id")) or instrument_ids[code] != forecast.get("stock_id"):
                    reason = "typed-security-id-mismatch"
                elif (code, target_session) not in actual:
                    reason = "target-actual-missing"
                else:
                    origin = inputs[(code, forecast["origin"])]
                    target = actual[(code, target_session)]
                    ref = forecast.get("reference") or {}
                    if int(origin["known_at_ms"]) > issued:
                        reason = "future-known-input"
                    elif float(origin["close"]) != float(ref.get("close", -1)):
                        reason = "origin-close-mismatch"
                    elif origin["currency"] != ref.get("currency") or origin["adjustment"] != ref.get("adjustment"):
                        reason = "origin-currency-or-basis-mismatch"
                    elif target["currency"] != ref.get("currency") or target["adjustment"] != ref.get("adjustment"):
                        reason = "target-currency-or-basis-mismatch"
                    elif int(target["known_at_ms"]) <= issued:
                        reason = "target-not-known-after-issuance"
                    elif target.get("completion_status") not in ("completed", "completed-by-XNYS-calendar"):
                        reason = "target-session-not-complete"
                    else:
                        close = float(ref["close"])
                        actual_targets = {
                            "low_return": float(target["low"]) / close - 1,
                            "high_return": float(target["high"]) / close - 1,
                            "terminal_logreturn": math.log(float(target["close"]) / close),
                        }
                        metrics = forecast_metrics(forecast, actual_targets)
                        quantiles = forecast["model"]["quantiles"]
                        # This scorer's realized target is a log return, so pair it
                        # with the model's terminal_logreturn quantiles. The separate
                        # terminal_return_quantiles field is simple return space.
                        terminal = forecast["model"]["relative_quantiles"][2]
                        baseline = forecast["baseline"]["relative_quantiles"][2]
                        qidx = {q: i for i, q in enumerate(quantiles)}
                        y = actual_targets["terminal_logreturn"]
                        row = {
                            "bundle": name, "code": code, "model_sha256": model_sha,
                            "origin_session": forecast["origin"], "target_session": target_session,
                            "actual_log_return": y, "model_metrics": metrics["model"]["terminal_logreturn"],
                            "baseline_metrics": metrics["baseline"]["terminal_logreturn"],
                            "model_abs_error": metrics["model"]["terminal_logreturn"]["absolute_error"],
                            "baseline_abs_error": metrics["baseline"]["terminal_logreturn"]["absolute_error"],
                            "model_direction_hit": (terminal[qidx[0.5]] > 0 and y > 0) or (terminal[qidx[0.5]] < 0 and y < 0) or (terminal[qidx[0.5]] == 0 and y == 0),
                            "baseline_direction_hit": (baseline[qidx[0.5]] > 0 and y > 0) or (baseline[qidx[0.5]] < 0 and y < 0) or (baseline[qidx[0.5]] == 0 and y == 0),
                            "zero_return_abs_error": abs(y), "zero_return_direction_hit": y == 0,
                        }
                        for label, values in (("model", terminal), ("baseline", baseline)):
                            row[f"{label}_pinball"] = {f"q{int(q*100):02d}": float(pinball(y, values[qidx[q]], q)) for q in (0.05, 0.5, 0.95)}
                            row[f"{label}_interval_covered"] = values[qidx[0.05]] <= y <= values[qidx[0.95]]
                        scored.append(row)
            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                reason = reason or f"invalid-row:{type(exc).__name__}"
            if reason:
                excluded.append({"bundle": name, "code": code, "target_session": target_session, "reason": reason})

    groups = {}
    for row in scored:
        groups.setdefault(row["model_sha256"], []).append(row)
    summaries = []
    for model_sha, rows in sorted(groups.items()):
        summaries.append({
            "model_sha256": model_sha,
            "bundles": sorted({r["bundle"] for r in rows}),
            "origin_dates": sorted({r["origin_session"] for r in rows}),
            "target_dates": sorted({r["target_session"] for r in rows}),
            "model": metric_summary(rows, "model"),
            "matched_baseline": metric_summary(rows, "baseline"),
            "zero_return": {
                "n": len(rows), "direction_hits": sum(r["zero_return_direction_hit"] for r in rows),
                "median_absolute_log_return_error": statistics.median(r["zero_return_abs_error"] for r in rows),
            },
        })
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "private-forecast-archive-benchmark",
        "purpose": "Descriptive one-session forecast score; not a multi-period accuracy, trading, or profitability claim.",
        "config_sha256": sha256(config_path), "sources": sources,
        "eligible_forecasts": len(scored), "excluded_forecasts": len(excluded),
        "model_generations_separate": summaries, "per_forecast": scored, "excluded": excluded,
        "limitations": [
            "Model generations are kept separate; this report does not name an overall winner.",
            "Forecasts may share target dates and are not independent observations.",
            "Provider finality, adjustment basis and universe membership are inherited from the saved evidence and must be reviewed.",
            "No confidence intervals, significance, profitability, model promotion or trading authorization is produced.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "benchmark.json"
    md_path = output_dir / "benchmark.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Private Forecast Archive Benchmark", "", report["purpose"], "",
             f"Eligible forecasts: {len(scored)} · Excluded: {len(excluded)}", "",
             "| Model SHA-256 | N | Origin dates | Target dates | Model direction | Baseline direction | Model median abs. error | Baseline median abs. error |",
             "|---|---:|---|---|---:|---:|---:|---:|"]
    for group in summaries:
        m, b = group["model"], group["matched_baseline"]
        lines.append(f"| `{group['model_sha256']}` | {m['n']} | {', '.join(group['origin_dates'])} | {', '.join(group['target_dates'])} | {m['direction_hits']}/{m['n']} | {b['direction_hits']}/{b['n']} | {m['median_absolute_log_return_error']:.6f} | {b['median_absolute_log_return_error']:.6f} |")
    lines.extend(["", "## Limitations", ""] + [f"- {item}" for item in report["limitations"]] + [""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return report, json_path, md_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Private JSON archive config with explicit input bundle paths")
    parser.add_argument("--output-dir", required=True, help="New/empty private output directory outside the repository")
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[2]
    report, json_path, md_path = score_archive(Path(args.config), Path(args.output_dir), repository_root=repo)
    print(json.dumps({"status": "scored", "eligible": report["eligible_forecasts"], "excluded": report["excluded_forecasts"], "json": str(json_path), "markdown": str(md_path)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"archive score failed: {error}")
