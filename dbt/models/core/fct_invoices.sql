-- Grain: one row per invoice, incrementally merged by invoice_id.
-- amount_usd is derived upstream from amount_local, currency, and fx_rate.
{{ config(
    materialized='incremental',
    unique_key='invoice_id',
    partition_by={'field': 'invoice_date', 'data_type': 'date'},
    cluster_by=['customer_id', 'status']
) }}

select
  invoice_id, customer_id, invoice_date, due_date, amount_local, currency,
  fx_rate, amount_usd, status, paid_date,
  current_timestamp() as _modeled_at
from {{ ref('stg_invoices') }}
{% if is_incremental() %}
where invoice_date >= date_sub(current_date(), interval 7 day)
{% endif %}
