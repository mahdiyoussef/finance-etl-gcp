# FinPulse operations runbook

## Prerequisites

- Python 3.10 or newer
- Kaggle account and accepted dataset terms
- Kaggle API credentials at `~/.kaggle/kaggle.json`
- Docker for local Airflow, or an existing Airflow/Composer environment
- Terraform for GCP deployment
- dbt-bigquery for warehouse transformations
- A GCP project and billing account for cloud resources

Never commit API tokens, service-account keys, Terraform state, or generated
dataset files.

## Download the complete source

```bash
PATH=.venv/bin:$PATH python scripts/download_b2b_dataset.py \
  --destination data/external/b2b_invoices
```

Verify that both files exist and match `manifest.json`:

```bash
find data/external/b2b_invoices -maxdepth 1 -type f -printf '%f %s bytes\n'
```

## Run locally

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m finpulse run --output data/demo
```

Expected quality output includes invoice count, ticket-event count, quarantine
count, orphan count, and negative amount count. A successful demo should have
zero orphan and negative amount records; quarantine records are intentional
fixtures.

## Run Airflow

Install Apache Airflow with the official constraints file for the selected
Python version. Configure `AIRFLOW_HOME`, copy the repository DAG into the
Airflow DAG directory, and set the DAG's `ROOT` to a writable worker path.
The DAG must see the Kaggle credentials through a secret backend or worker
mount; do not commit `kaggle.json`.

The DAG fails when either train or test file is missing. This prevents partial
dataset processing.

### Task responsibilities

| Task | Responsibility | Failure behavior |
|---|---|---|
| `download_complete_dataset` | Download/verify complete source | Retry; fail on partial files |
| `stage_invoice_dataset` | Stream and normalize both CSVs | Quarantine bad rows |
| `build_finpulse_marts` | Produce local analytical CSVs | Fail if no invoices |
| `validate_quality` | Enforce critical checks | Stop downstream dbt |
| `dbt_source_freshness_and_build` | Build BigQuery models | Fail on stale source/tests |

## Deploy infrastructure

Set `TF_VAR_project_id` and configure the GCS backend bucket, then run:

```bash
terraform -chdir=terraform/envs/dev init
terraform -chdir=terraform/envs/dev plan
terraform -chdir=terraform/envs/dev apply
```

Production uses `terraform/envs/prod` and has deletion protection on its
datasets. Use a separate state bucket and require a protected GitHub
environment approval before applying production.

GitHub deployment uses Workload Identity Federation. Configure repository or
environment variables `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT`, and
`GCP_PROJECT_ID`; no JSON key is used.

## Recovery

- Retry `download_complete_dataset` if the manifest is missing.
- Retry `stage_invoice_dataset`; inserts are idempotent by `invoice_id`.
- Inspect the `quarantine` table before promoting marts.
- Delete only the local `data/` directory to rebuild from a clean state.

## Backfill procedure

1. Set `FINPULSE_REPORT_DATE` to the desired reporting date.
2. Run the Airflow task for that logical date.
3. Confirm the manifest still contains both source files.
4. Re-run ingestion; business-key inserts make the operation idempotent.
5. Run dbt with the same `report_date`.
6. Compare row counts and quarantine metrics with the original run.

Do not delete production data to perform a backfill. Use a new partition or
controlled `MERGE` operation.
