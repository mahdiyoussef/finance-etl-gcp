# dbt layer

The local SQLite marts are the executable baseline. The next GCP adapter should
mirror them with BigQuery dbt models:

```text
models/staging/stg_invoices.sql
models/core/fct_invoices.sql
models/marts/mart_ar_aging.sql
models/marts/mart_dso.sql
models/marts/mart_invoice_risk.sql
models/marts/mart_support_cost.sql
models/marts/mart_support_cost.sql
```

Each model must define its grain, partition strategy, and uniqueness tests.
