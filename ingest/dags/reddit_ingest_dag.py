"""Airflow DAG template for Reddit ingestion."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "praesagus",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="reddit_ingest",
    default_args=default_args,
    schedule_interval="@hourly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    run_connector = BashOperator(
        task_id="run_reddit_connector",
        bash_command="poetry run python -m connectors.reddit_run --subreddit python",
    )

    run_connector
