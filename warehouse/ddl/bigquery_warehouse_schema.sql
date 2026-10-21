-- Finance ETL BigQuery raw-layer table and dataset contract.
create schema if not exists `${PROJECT_ID}.finance_raw`;
create schema if not exists `${PROJECT_ID}.finance_core`;
create schema if not exists `${PROJECT_ID}.finance_marts`;

create table if not exists `${PROJECT_ID}.finance_raw.invoices` (
  invoice_id string not null,
  customer_id string,
  invoice_date date not null,
  due_date date,
  amount_local numeric,
  currency string,
  fx_rate numeric,
  amount_usd numeric,
  status string,
  paid_date date,
  _ingested_at timestamp not null,
  _source_file string not null
)
partition by invoice_date
cluster by customer_id, status
options (require_partition_filter = true);

create table if not exists `${PROJECT_ID}.finance_raw.ticket_events` (
  event_id string not null,
  ticket_id string not null,
  customer_id string not null,
  event_type string not null,
  status string not null,
  category string not null,
  priority string not null,
  event_ts timestamp not null,
  _ingested_at timestamp not null
)
partition by date(event_ts)
cluster by customer_id, category
options (require_partition_filter = true);
