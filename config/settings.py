"""Centralised environment configuration for the Finance ETL pipeline.

All runtime settings are read from environment variables with safe defaults
so the pipeline can run locally without cloud credentials.
"""
from __future__ import annotations

import os
from pathlib import Path


# ── Root paths ───────────────────────────────────────────────────────────────
PIPELINE_ROOT: Path = Path(
    os.environ.get("FINANCE_ROOT", "/opt/airflow/data/finance")
)
LOCAL_DATA_ROOT: Path = Path(os.environ.get("LOCAL_DATA_ROOT", "data/demo"))
DBT_DIR: Path = Path(
    os.environ.get("FINANCE_DBT_DIR", "/opt/airflow/project/dbt")
)

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_NAME: str = os.environ.get("FINANCE_DB_NAME", "finance.db")

# ── Reporting ─────────────────────────────────────────────────────────────────
REPORT_DATE: str = os.environ.get("FINANCE_REPORT_DATE", "2026-01-31")

# ── GCP ───────────────────────────────────────────────────────────────────────
GCP_PROJECT_ID: str = os.environ.get("GCP_PROJECT_ID", "")
BQ_RAW_DATASET: str = os.environ.get("BQ_RAW_DATASET", "finance_raw")
BQ_CORE_DATASET: str = os.environ.get("BQ_CORE_DATASET", "finance_core")
BQ_MARTS_DATASET: str = os.environ.get("BQ_MARTS_DATASET", "finance_marts")

# ── Ingestion ─────────────────────────────────────────────────────────────────
BATCH_SIZE: int = int(os.environ.get("INGEST_BATCH_SIZE", "10000"))
DEFAULT_FX_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "CAD": 0.74,
    "AUD": 0.66,
}

# ── Quality gates ─────────────────────────────────────────────────────────────
MAX_QUARANTINE_RATE: float = float(
    os.environ.get("MAX_QUARANTINE_RATE", "0.05")
)  # 5 % quarantine triggers a pipeline failure

