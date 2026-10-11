-- Grain: one row per raw invoice after type normalization.
{{ config(materialized='view') }}

select
  cast(invoice_id as string) as invoice_id,
  cast(customer_id as string) as customer_id,
  cast(invoice_date as date) as invoice_date,
  cast(due_date as date) as due_date,
  cast(coalesce(amount_local, amount_usd) as numeric) as amount_local,
  upper(coalesce(currency, 'USD')) as currency,
  cast(coalesce(fx_rate, 1) as numeric) as fx_rate,
  cast(coalesce(amount_usd, amount_local * coalesce(fx_rate, 1)) as numeric) as amount_usd,
  lower(cast(status as string)) as status,
  cast(paid_date as date) as paid_date
from {{ source('raw', 'invoices') }}
