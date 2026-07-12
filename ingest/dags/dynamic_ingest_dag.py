"""Generates Airflow DAGs dynamically from connector configuration."""

import os
import yaml
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "platform_connectors.yaml")


def load_connectors(config_path=CONFIG_PATH):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("connectors", [])


def build_dag(connector_def: dict):
    connector_name = connector_def["name"]
    dag_id = f"ingest_{connector_name}"
    default_args = {
        "owner": "praesagus",
        "depends_on_past": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    }
    schedule = connector_def.get("schedule", "@daily")
    run_args = connector_def.get("run_args", "")
    task_id = f"run_{connector_name}_connector"
    raw_bucket = os.environ.get("RAW_DATA_BUCKET", "praesagus-raw-data-local")

    command = f"python -m connectors.multi_runner --connectors {connector_name} --s3-bucket {raw_bucket} {run_args}"

    dag = DAG(
        dag_id=dag_id,
        default_args=default_args,
        schedule_interval=schedule,
        start_date=datetime(2026, 1, 1),
        catchup=False,
    )

    BashOperator(
        task_id=task_id,
        bash_command=command,
        dag=dag,
    )

    return dag


for connector in load_connectors():
    globals()[f"dag_{connector['name']}"] = build_dag(connector)
