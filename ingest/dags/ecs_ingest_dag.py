"""Dynamically generate Airflow DAGs that launch ingestion connectors as ECS Fargate tasks."""

import os
import yaml
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from airflow import DAG
from airflow.operators.python import PythonOperator

from ingest.ecs_runner import run_fargate_task

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "platform_connectors.yaml")

DEFAULT_ARGS = {
    "owner": "praesagus",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

TASK_CLUSTER = os.environ.get("ECS_CLUSTER")
TASK_DEFINITION = os.environ.get("ECS_TASK_DEFINITION")
TASK_SUBNETS = os.environ.get("ECS_SUBNETS")
TASK_SECURITY_GROUPS = os.environ.get("ECS_SECURITY_GROUPS")
TASK_CONTAINER_NAME = os.environ.get("ECS_TASK_CONTAINER_NAME", "ingest")
RAW_DATA_BUCKET = os.environ.get("RAW_DATA_BUCKET", "praesagus-raw-data-local")


def load_connectors(config_path: str = CONFIG_PATH) -> List[Dict[str, Any]]:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    return [connector for connector in cfg.get("connectors", []) if connector.get("execution") == "ecs"]


def build_connector_command(connector_name: str, connector_args: Optional[str] = None) -> List[str]:
    command = ["python", "-m", "connectors.multi_runner", "--connectors", connector_name, "--s3-bucket", RAW_DATA_BUCKET]
    if connector_args:
        command.extend(connector_args.split())
    return command


def run_connector_task(connector_name: str, connector_args: Optional[str] = None):
    if not TASK_CLUSTER or not TASK_DEFINITION or not TASK_SUBNETS:
        raise RuntimeError("ECS_CLUSTER, ECS_TASK_DEFINITION, and ECS_SUBNETS must be configured")

    run_fargate_task(
        cluster=TASK_CLUSTER,
        task_definition=TASK_DEFINITION,
        subnets=TASK_SUBNETS.split(","),
        security_groups=TASK_SECURITY_GROUPS.split(",") if TASK_SECURITY_GROUPS else None,
        assign_public_ip=True,
        command=build_connector_command(connector_name, connector_args),
        environment={
            "CONNECTOR_NAME": connector_name,
            "ECS_TASK_CONTAINER_NAME": TASK_CONTAINER_NAME,
        },
    )


def build_dag(connector_def: Dict[str, Any]) -> DAG:
    connector_name = connector_def["name"]
    dag_id = f"ecs_ingest_{connector_name}"
    schedule = connector_def.get("schedule", "@daily")
    run_args = connector_def.get("run_args", "")

    dag = DAG(
        dag_id=dag_id,
        default_args=DEFAULT_ARGS,
        schedule_interval=schedule,
        start_date=datetime(2026, 1, 1),
        catchup=False,
    )

    PythonOperator(
        task_id=f"run_{connector_name}_connector",
        python_callable=run_connector_task,
        op_args=[connector_name, run_args],
        dag=dag,
    )

    return dag


for connector in load_connectors():
    globals()[f"dag_{connector['name']}"] = build_dag(connector)
