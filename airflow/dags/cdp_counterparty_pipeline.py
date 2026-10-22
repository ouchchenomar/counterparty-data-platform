"""Orchestration quotidienne du référentiel contrepartie.

Airflow ne fait qu'orchestrer : chaque tâche lance `python -m cdp.pipeline --step <étape>`
dans le venv du projet (CDP_PYTHON), isolé des dépendances d'Airflow.
"""

import os
import subprocess
from datetime import datetime, timedelta

try:  # Airflow 3
    from airflow.sdk import dag, task
except ImportError:  # Airflow 2
    from airflow.decorators import dag, task

PROJECT_DIR = os.environ.get("CDP_PROJECT_DIR", "/opt/airflow/project")
CDP_PYTHON = os.environ.get("CDP_PYTHON", "python")


def run_step(step: str) -> None:
    env = {**os.environ, "PYTHONPATH": f"{PROJECT_DIR}/src"}
    command = [CDP_PYTHON, "-m", "cdp.pipeline", "--step", step]
    subprocess.run(command, cwd=PROJECT_DIR, env=env, check=True)


@dag(
    dag_id="cdp_counterparty_pipeline",
    schedule="@daily",
    start_date=datetime(2026, 10, 1),
    catchup=False,
    max_active_runs=1,  # DuckDB n'accepte qu'un seul écrivain à la fois
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["gleif", "dbt", "data-quality"],
)
def cdp_counterparty_pipeline():
    @task
    def ingest_gleif():
        run_step("ingest")

    @task
    def ensure_internal_extract():
        run_step("synthetic")

    @task
    def load_raw():
        run_step("load")

    @task
    def dbt_build():
        run_step("dbt")

    ingest_gleif() >> ensure_internal_extract() >> load_raw() >> dbt_build()


cdp_counterparty_pipeline()
