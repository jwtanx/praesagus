"""Run multiple connectors in a single pipeline execution."""

import argparse
import importlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .utils import s3_atomic_write

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "ingest" / "config" / "platform_connectors.yaml"


def load_connector_config(config_path: Path = DEFAULT_CONFIG_PATH) -> List[Dict[str, Any]]:
    if not config_path.exists():
        raise FileNotFoundError(f"Connector config not found: {config_path}")
    with config_path.open(encoding="utf-8") as f:
        payload = yaml.safe_load(f)
    if not isinstance(payload, dict):
        return []
    return payload.get("connectors", []) or []


def parse_unknown_args(unknown_args: List[str]) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    i = 0
    while i < len(unknown_args):
        token = unknown_args[i]
        if not token.startswith("--"):
            i += 1
            continue
        if "=" in token:
            key, value = token[2:].split("=", 1)
        else:
            key = token[2:]
            if i + 1 < len(unknown_args) and not unknown_args[i + 1].startswith("--"):
                value = unknown_args[i + 1]
                i += 1
            else:
                value = "true"
        kwargs[key.replace("-", "_")] = value
        i += 1
    return kwargs


def instantiate_connector(connector_def: Dict[str, Any], extra_kwargs: Dict[str, Any] = None):
    module = importlib.import_module(connector_def["module"])
    cls = getattr(module, connector_def["class_name"])
    params = connector_def.get("kwargs") or {}
    combined = {**params, **(extra_kwargs or {})}
    return cls(**combined)


def main():
    parser = argparse.ArgumentParser(description="Run one or more connectors and optionally store normalized output to S3.")
    parser.add_argument("--connectors", nargs="+", help="Connector keys to run (reddit, twitter, hackernews)")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Connector configuration YAML path")
    parser.add_argument("--start", help="ISO8601 start time", default=None)
    parser.add_argument("--end", help="ISO8601 end time", default=None)
    parser.add_argument("--s3-bucket", help="S3 bucket for normalized output", default=None)
    parser.add_argument("--s3-prefix", help="S3 key prefix", default="praesagus")
    args, unknown_args = parser.parse_known_args()

    config_path = Path(args.config)
    connector_defs = load_connector_config(config_path)
    if args.connectors:
        requested = {name.lower() for name in args.connectors}
        connector_defs = [cfg for cfg in connector_defs if cfg.get("name", "").lower() in requested]

    if not connector_defs:
        raise RuntimeError("No connectors configured for execution")

    end = datetime.fromisoformat(args.end) if args.end else datetime.utcnow()
    start = datetime.fromisoformat(args.start) if args.start else end - timedelta(hours=1)
    extra_kwargs = parse_unknown_args(unknown_args)

    for connector_def in connector_defs:
        connector_name = connector_def.get("name", "unknown")
        connector = instantiate_connector(connector_def, extra_kwargs)
        print(f"Running connector: {connector_name}")
        for raw in connector.fetch(start, end):
            normalized = connector.normalize(raw)
            if args.s3_bucket:
                connector.store(raw, normalized, s3_bucket=args.s3_bucket, s3_writer=s3_atomic_write)
            else:
                print(normalized)


if __name__ == "__main__":
    main()
