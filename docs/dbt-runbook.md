# dbt runbook

## Model execution order

```text
raw sources
  -> stg_invoices / stg_ticket_events
  -> fct_invoices
  -> mart_ar_aging / mart_dso / mart_invoice_risk / mart_support_cost
```

From the repository root:

```bash
python -m pip install -r requirements-dbt.txt
cd dbt
cp profiles.yml.example ~/.dbt/profiles.yml
export GCP_PROJECT_ID="your-project-id"
dbt debug
dbt source freshness
dbt build --vars '{report_date: "2026-01-31"}'
```

For the Airflow container, copy the example file to `dbt/profiles.yml` and
configure the project before running the DAG. The repository's `dbt/profiles.yml`
is a non-secret local default and reads the project from `GCP_PROJECT_ID`.

The service account or user running dbt needs BigQuery job creation access and
read access to `finpulse_raw`, plus write access to the target core and marts
datasets. Run `dbt build` only after the raw tables have been loaded.

## Useful commands

```bash
dbt ls
dbt compile --vars '{report_date: "2026-01-31"}'
dbt test
dbt source freshness
dbt build --select +mart_ar_aging
dbt docs generate
dbt docs serve
```

## Failure interpretation

- `source freshness` failure means ingestion is late or `_ingested_at` is
  missing; inspect Airflow and raw-load metadata.
- A uniqueness failure means a business-key merge or source deduplication
  regression.
- A relationship failure means a dimension or foreign-key load is incomplete.
- A custom singular-test failure means invalid status or non-positive amount.

Use `--select` for targeted recovery, then run the complete build before
promoting a release.
