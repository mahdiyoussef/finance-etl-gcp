"""Airflow orchestration for the local Finance ETL batch pipeline.

This DAG is intentionally provider-neutral: the same tasks can run on a local
Airflow installation or be moved to Cloud Composer later.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import os
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from pipeline.extract.external_dataset_loader import load_external_dataset
from pipeline.load.batch_warehouse_loader import BatchLoader
from scripts.download_b2b_dataset import download


ROOT = Path(os.environ.get("FINANCE_ROOT", "/opt/airflow/data/finance"))
SOURCE = ROOT / "external" / "b2b_invoices"
REPORT_DATE = os.environ.get("FINANCE_REPORT_DATE", "2026-01-31")
SQL_SERVER_ENDPOINT = os.environ.get("SQL_SERVER_ENDPOINT", "localhost:1433")
DEFAULT_ARGS = {
    "owner": "finance",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


def download_dataset() -> None:
    """Download the complete source dataset unless its manifest is current."""
    download(SOURCE)


def load_dataset() -> None:
    """Stream both complete source CSVs directly into the warehouse database."""
    sources = [SOURCE / name for name in ("train_invoices.csv", "test_invoices.csv")]
    missing = [source for source in sources if not source.is_file()]
    if missing:
        raise FileNotFoundError(f"Complete dataset is required; missing {missing}")
    loader = BatchLoader(ROOT / "finance.db", endpoint=SQL_SERVER_ENDPOINT)
    try:
        loaded = load_external_dataset(loader, sources)
        if loaded == 0:
            raise RuntimeError("No valid invoice rows loaded")
    finally:
        loader.close()


def build_marts() -> None:
    """Materialize local marts after external invoice ingestion."""
    loader = BatchLoader(ROOT / "finance.db", endpoint=SQL_SERVER_ENDPOINT)
    try:
        from datetime import date
        loader.build_marts(ROOT / "marts", date.fromisoformat(REPORT_DATE))
        report = loader.quality_report()
        if report["invoice_count"] == 0:
            raise RuntimeError("No valid invoice rows loaded")
    finally:
        loader.close()


def validate_quality() -> None:
    """Fail the Airflow run when critical warehouse quality checks fail."""
    loader = BatchLoader(ROOT / "finance.db", endpoint=SQL_SERVER_ENDPOINT)
    try:
        report = loader.quality_report()
        if report["invoice_count"] == 0:
            raise RuntimeError("Quality gate failed: no invoices")
        if report["orphan_invoice_count"] > 0:
            raise RuntimeError(f"Quality gate failed: {report['orphan_invoice_count']} orphan invoices")
        if report["negative_invoice_count"] > 0:
            raise RuntimeError(f"Quality gate failed: {report['negative_invoice_count']} negative invoices")
    finally:
        loader.close()


with DAG(
    dag_id="finance_invoice_to_cash",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["finance", "batch"],
) as dag:
    download_task = PythonOperator(task_id="download_complete_dataset", python_callable=download_dataset)
    load_task = PythonOperator(task_id="stage_invoice_dataset", python_callable=load_dataset)
    mart_task = PythonOperator(task_id="build_finance_marts", python_callable=build_marts)
    quality_task = PythonOperator(task_id="validate_quality", python_callable=validate_quality)
    dbt_task = BashOperator(
        task_id="dbt_source_freshness_and_build",
        bash_command=(
            "cd \"$FINANCE_DBT_DIR\" && "
            "test -f profiles.yml || "
            "(echo 'dbt/profiles.yml is required; copy profiles.yml.example and configure it' >&2; exit 1) && "
            "dbt source freshness --profiles-dir \"$FINANCE_DBT_DIR\" && "
            "dbt build --profiles-dir \"$FINANCE_DBT_DIR\" "
            "--vars '{report_date: \"{{ ds }}\"}'"
        ),
        env={
            "FINANCE_DBT_DIR": os.environ.get("FINANCE_DBT_DIR", "/opt/airflow/project/dbt"),
            "GCP_PROJECT_ID": os.environ.get("GCP_PROJECT_ID", ""),
        },
    )
    download_task >> load_task >> mart_task >> quality_task >> dbt_task
