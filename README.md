# Finance ETL: Invoice-to-Cash & Support Cost Intelligence

Finance ETL is an end-to-end data engineering project for a fictional
B2B SaaS company. It unifies invoice, payment, customer, vendor, and support
event data so finance and support leaders can answer:

1. What is DSO and AR aging by customer, segment, and region?
2. Which invoices are at risk of becoming late?
3. Which records are duplicates, malformed, or anomalous?
4. Which billing tickets correlate with delayed payment?
5. What is support cost per customer and SLA breach rate?
6. How much revenue is exposed by open escalations?

The repository contains a fully runnable local implementation and cloud-ready
contracts for BigQuery, Cloud Storage, Pub/Sub, Dataflow, Cloud Composer,
Terraform, dbt, BigQuery ML, and Looker Studio. The local path is deliberately
complete so it can be tested without cloud credentials:

```text
generator -> landing CSV -> batch loader -> SQLite raw/core -> marts
                                      \-> ticket events -> deduplicated facts
```

## Architecture

![Finance ETL GCP Architecture](./GCP%20Finance%20ETL.jpg)

The architecture uses Google Cloud service nodes for Cloud Storage, Cloud
Composer/Airflow, Pub/Sub, Dataflow, BigQuery, dbt, Looker Studio, and the
cross-cutting Terraform/IAM/Monitoring controls. It separates the idempotent
batch path from the event-time streaming path and shows where validation,
quarantine, dbt transformations, and serving occur.

## Quick start: local MVP

```bash
PYTHONPATH=. python -m pipeline run --output data/demo --customers 25 --invoices 100
python -m pytest tests/ -v
```

The run produces:

- `data/demo/landing/invoices_YYYY-MM-DD.csv`
- `data/demo/landing/ticket_events_YYYY-MM-DD.jsonl`
- `data/demo/finance.db`
- `data/demo/marts/ar_aging.csv`
- `data/demo/marts/dso.csv`
- `data/demo/marts/invoice_risk.csv`
- `data/demo/marts/support_cost.csv`

The report date is explicit so backfills and tests are reproducible:

```bash
python -m pipeline run --output data/demo --report-date 2026-01-31
```

The CLI prints a quality report containing accepted row counts, quarantine
counts, orphan foreign keys, and invalid amounts.

Ticket events are retained as an append-only fact and materialized into
`tickets_latest`; the support mart also reports tickets breaching the
24-hour synthetic SLA.

The generator deliberately emits duplicates, invalid rows, and late ticket
events. The loader quarantines invalid records and uses business keys to make
re-runs idempotent.

## Project Structure

```text
pipeline/               Python application package (extract / load / stream / utils)
  extract/              Synthetic data generator and external CSV loader
  load/                 Batch warehouse loader and mart materialisation
  stream/               Pub/Sub ticket event processor (Beam contract)
  utils/                Shared data quality helpers
config/                 Centralised environment configuration
dags/                   Apache Airflow DAGs / Cloud Composer entrypoints
scripts/                Operational CLIs, dataset download, env validation
tests/
  unit/                 Unit tests for each pipeline layer
  integration/          Integration tests for project structure and artifacts
dbt/
  models/staging/       Type normalisation models
  models/intermediate/  Customer enrichment layer
  models/marts/         Aggregated analytical surfaces
  snapshots/            SCD Type 2 status history
  macros/               Reusable dbt macros
infra/terraform/        GCP infrastructure (dev and prod environments)
  modules/              Reusable Terraform modules
  envs/dev/             Development environment
  envs/prod/            Production environment
docs/                   Architecture overview, data dictionary, runbook
warehouse/ddl/          BigQuery dataset and table DDL
data/                   Ignored local data and generated artifacts
```

## Business grain and metrics

| Dataset | Grain | Primary key | Purpose |
|---|---|---|---|
| `invoices` | One row per invoice | `invoice_id` | Invoice amount, due date, status |
| `ticket_events` | One row per status-change event | `event_id` | Immutable support history |
| `tickets_latest` | One row per ticket's latest state | `ticket_id` | Current support workload |
| `ar_aging` | One row per segment and region | `segment, region` | Current and overdue receivables |
| `dso` | One row per segment and region | `segment, region` | Weighted days to pay |
| `invoice_risk` | One row per invoice | `invoice_id` | Deterministic risk band |
| `support_cost` | One row per customer | `customer_id` | Ticket volume, SLA, estimated cost |

The local support-cost estimate is `ticket_count * 25`. It is a transparent
synthetic assumption, not an accounting charge. Replace it with agent labor
minutes, loaded hourly cost, and vendor charges in a production implementation.

## End-to-end execution

```text
Kaggle source files
    -> Airflow download task
    -> bounded CSV streaming and normalization
    -> raw/core warehouse tables
    -> quarantine and quality gate
    -> dbt source freshness
    -> dbt incremental facts and marts
    -> Looker Studio / ML consumers
```

The source dataset is synthetic and contains two complete files:

```text
train_invoices.csv
test_invoices.csv
```

Both files are required. The loader processes them sequentially and never
creates a second combined 1.3 GB CSV.

## Data quality and idempotency

The pipeline intentionally handles realistic failure modes:

- Duplicate invoice IDs are ignored on retry.
- Duplicate ticket event IDs are ignored.
- Invalid numeric values are quarantined.
- Missing dates and business keys are quarantined.
- Orphan foreign keys fail the quality gate.
- Negative invoice amounts fail the quality gate.
- A matching dataset manifest skips a redundant 1.3 GB download.
- The Airflow DAG retries transient failures twice.

The `quarantine` table stores the source name, serialized record, and error
message. It is an operational investigation surface, not a silent discard.

## GCP mapping

| Local component | GCP implementation |
|---|---|
| Landing directory | GCS |
| SQLite raw/core tables | BigQuery datasets |
| `BatchLoader` | Composer task / Cloud Run Job |
| `ticket_event_processor` | Beam Dataflow pipeline |
| CSV marts | dbt BigQuery marts |

The local implementation is the executable contract for those later adapters.
The full external dataset is processed by streaming each source CSV in batches;
the pipeline never creates a second 1.3 GB combined staging file.
Source amounts are retained as `amount_local`; `amount_usd` is derived with the
configured FX snapshot and unsupported currencies are quarantined.

## Infrastructure

Terraform configurations are in [`infra/terraform/`](./infra/terraform).
The first infrastructure environment is in
[`infra/terraform/envs/dev`](./infra/terraform/envs/dev). It provisions labeled GCS,
BigQuery raw/core datasets, and Pub/Sub event/DLQ topics. It intentionally
requires an explicit project ID and a pre-created remote-state bucket before
apply.

The dbt contract is in [`dbt/`](./dbt), and the optional Beam contract is in
[`pipeline/stream/ticket_event_processor.py`](./pipeline/stream/ticket_event_processor.py).
These are validated in CI without requiring cloud credentials.

## Full B2B dataset download

The selected public source is the Global B2B Invoice & Payments dataset. It
contains large `train_invoices.csv` and `test_invoices.csv` files. The project
does not commit this multi-gigabyte data or credentials. To download the
complete dataset, create a Kaggle API token, place it at
`~/.kaggle/kaggle.json`, and run:

```bash
python scripts/download_b2b_dataset.py
```

The command uses the Kaggle CLI with `--unzip`, verifies both expected files,
and writes a size manifest. It fails rather than silently accepting a partial
download.

Repeated runs are idempotent: a matching manifest skips the 1.3 GB download.
Use `--force` only when intentionally refreshing the source.

The downloader writes `manifest.json` with the dataset identifier and exact
file sizes. This protects Airflow retries from needless downloads and catches
partial extraction before ingestion begins.

## Local Airflow with Docker

```bash
docker compose -f docker-compose.airflow.yml up
```

Then open `http://localhost:8080` and run `finance_invoice_to_cash`.

Apache Airflow orchestration is defined in
[`dags/finance_pipeline.py`](./dags/finance_pipeline.py). Install Airflow
using the matching constraints file for your Python version, then initialize
Airflow with `AIRFLOW_HOME` and run the `finance_invoice_to_cash` DAG. The
DAG downloads the full dataset, streams both source files into the warehouse
database, and builds the marts. In Cloud Composer, replace
`/opt/airflow/data/finance` with a
GCS-backed staging strategy and move the download task to a secure worker.
After the quality gate, the DAG runs dbt source freshness and dbt build against
BigQuery.

For a direct DAG validation:

```bash
export AIRFLOW_HOME="$PWD/.airflow"
export PYTHONPATH="$PWD"
airflow db migrate
airflow dags list
airflow dags test finance_invoice_to_cash 2026-01-31
```

The final dbt task requires a configured `dbt/profiles.yml`, a
`GCP_PROJECT_ID`, and BigQuery credentials. The local Python/SQLite tasks can
be tested without those cloud prerequisites.

## Deployment workflow

### Development

1. Create a dedicated GCP project or use a sandbox project.
2. Create a remote Terraform state bucket.
3. Set `TF_VAR_project_id` and `TF_VAR_billing_account_id`.
4. Run `terraform -chdir=infra/terraform/envs/dev init`.
5. Review `terraform plan`.
6. Apply only after confirming region, bucket names, IAM, and budget alerts.
7. Configure Airflow/Composer to use the deployed bucket and service account.
8. Run dbt freshness and build checks.

### Production

Production uses a separate state prefix, datasets with deletion protection,
separate Pub/Sub resources, and a protected GitHub environment. Deployment is
performed through GitHub OIDC and Workload Identity Federation rather than a
long-lived JSON key.

Before deploying, verify the Terraform plan, IAM bindings, budget alerts,
remote-state bucket, WIF configuration, and production deletion protection.
The repository's README, Airflow guide, dbt guide, Terraform files, and CI
workflow contain the operating instructions.

## Developer commands

```bash
make test
make unit-test
make integration-test
make compile
make demo
make download
make airflow-up
make validate-env
```

Use [`.env.example`](./.env.example) for configuration names and
review the Terraform plan before applying any GCP environment.

For BigQuery transformations, configure `dbt/profiles.yml` and run
`dbt source freshness` followed by `dbt build` after the Airflow load task.
