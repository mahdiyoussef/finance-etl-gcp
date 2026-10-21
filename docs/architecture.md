# Finance ETL — Architecture Overview

## System Purpose

End-to-end data engineering pipeline for a B2B SaaS company that unifies
invoice, payment, customer, and support event data to power AR aging,
DSO, invoice risk, and support cost analytics.

## Architecture Diagram

![GCP Finance ETL Architecture](../GCP%20Finance%20ETL.jpg)

## Data Flow

```text
External Sources (Kaggle / ERP / API)
    ↓
Cloud Storage (GCS) — Landing zone & manifests
    ↓
Cloud Composer (Airflow) — Orchestration & scheduling
    ├── Batch path
    │   ↓
    │   Dataflow (Beam) — Validation, type casting, quarantine
    │   ↓
    │   BigQuery raw layer — finance_raw.*
    │   ↓
    │   dbt — staging → intermediate → marts
    │   ↓
    │   BigQuery core/marts — finance_core.*, finance_marts.*
    │   ↓
    │   Looker Studio — Executive dashboards
    │
    └── Streaming path
        ↓
        Pub/Sub — ticket_events topic
        ↓
        Dataflow (Beam streaming) — parse_event, DLQ routing
        ↓
        BigQuery — finance_raw.ticket_events (append-only)
```

## Layer Definitions

| Layer | Location | Purpose |
|---|---|---|
| Extract | `pipeline/extract/` | Generate synthetic data; load external CSVs |
| Load | `pipeline/load/` | Batch warehouse loading; mart materialisation |
| Stream | `pipeline/stream/` | Pub/Sub event parsing; Beam pipeline contract |
| Staging | `dbt/models/staging/` | Type normalisation; no business logic |
| Intermediate | `dbt/models/intermediate/` | Customer enrichment; derived columns |
| Marts | `dbt/models/marts/` | Aggregated analytical surfaces |
| Snapshots | `dbt/snapshots/` | SCD Type 2 status history |

## Quality Gate

The pipeline applies a multi-level quality gate:

1. **Row validation** — missing keys, negative amounts, invalid dates → quarantine table
2. **Orphan FK check** — invoices without a matching customer → pipeline failure
3. **Quarantine rate** — configurable threshold (default 5 %) → pipeline failure
4. **dbt tests** — `not_null`, `unique`, custom `assert_*` tests → build failure

## Infrastructure

Provisioned with Terraform under `infra/terraform/`:
- GCS landing bucket
- BigQuery datasets: `finance_raw`, `finance_core`, `finance_marts`, `finance_ml`
- Pub/Sub topic + DLQ subscription
- Service account with least-privilege IAM
- Budget alert (configurable threshold)
- Quarantine-rate monitoring alert policy

