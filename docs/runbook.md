# Finance ETL — Operational Runbook

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Pipeline runtime |
| Terraform | 1.6+ | Infrastructure provisioning |
| dbt-bigquery | 1.8–2.0 | Transformation layer |
| Apache Airflow | 2.10.5 | Orchestration |
| Kaggle CLI | 1.6+ | Dataset download |

## Local Quick-Start

```bash
# 1. Install pipeline package
pip install -e .

# 2. Run the local demo
make demo

# 3. Run tests
make test
```

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

| Variable | Default | Description |
|---|---|---|
| `GCP_PROJECT_ID` | — | GCP project to deploy to |
| `FINANCE_ROOT` | `/opt/airflow/data/finance` | Pipeline working directory |
| `FINANCE_REPORT_DATE` | `2026-01-31` | Analytical report date |
| `FINANCE_DB_NAME` | `finance.db` | SQLite database filename (local only) |
| `FINANCE_DBT_DIR` | `/opt/airflow/project/dbt` | Path to dbt project |
| `BQ_RAW_DATASET` | `finance_raw` | BigQuery raw dataset name |
| `BQ_CORE_DATASET` | `finance_core` | BigQuery core dataset name |
| `TF_VAR_billing_account_id` | — | GCP billing account for budget alerts |

## GCP Deployment

```bash
# 1. Authenticate
gcloud auth application-default login

# 2. Initialise Terraform (first time)
terraform -chdir=infra/terraform/envs/dev init

# 3. Plan and review
TF_VAR_project_id=<YOUR_PROJECT> terraform -chdir=infra/terraform/envs/dev plan

# 4. Apply
terraform -chdir=infra/terraform/envs/dev apply
```

## Airflow / Cloud Composer

```bash
# Local
docker compose -f docker-compose.airflow.yml up

# Then open http://localhost:8080 and trigger: finance_invoice_to_cash
```

## dbt

```bash
# Configure credentials
cp dbt/profiles.yml.example dbt/profiles.yml
# Edit dbt/profiles.yml with your GCP project

# Run
dbt source freshness --profiles-dir dbt/
dbt build --profiles-dir dbt/
```

## Incident Response

### High quarantine rate (> 5 %)
1. Check `quarantine` table: `SELECT source, error, COUNT(*) FROM quarantine GROUP BY 1,2`
2. Identify the source file with the most rejections
3. Fix the upstream data issue or update field aliases in `external_dataset_loader.py`
4. Re-run the affected DAG task

### Orphan invoices
1. Check: `SELECT i.customer_id FROM invoices i LEFT JOIN customers c USING(customer_id) WHERE c.customer_id IS NULL`
2. The customers file may be missing or malformed
3. Re-download and reprocess the customers CSV, then re-run

### Pipeline failure
1. Check Airflow logs for the failed task
2. Check the `quarantine` table
3. Re-trigger the failed task after fixing the root cause
4. All tasks are idempotent — safe to re-run

