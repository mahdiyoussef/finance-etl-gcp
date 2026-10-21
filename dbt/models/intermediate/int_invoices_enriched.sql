-- Grain: one row per invoice, enriched with customer dimension attributes.
-- This layer sits between staging and marts so mart queries remain thin.
{{ config(materialized='view') }}

select
  i.invoice_id,
  i.customer_id,
  c.customer_name,
  c.segment,
  c.region,
  i.invoice_date,
  i.due_date,
  i.amount_local,
  i.currency,
  i.fx_rate,
  i.amount_usd,
  i.status,
  i.paid_date,
  date_diff(i.due_date, i.invoice_date, day)                          as payment_terms_days,
  case
    when i.status = 'open' and i.due_date < current_date()           then 'high'
    when i.status = 'open'                                            then 'medium'
    else 'low'
  end                                                                  as risk_band,
  case
    when i.paid_date is not null
      then date_diff(i.paid_date, i.invoice_date, day)
    else null
  end                                                                  as days_to_pay
from {{ ref('stg_invoices') }} i
left join {{ source('raw', 'customers') }} c
  on c.customer_id = i.customer_id

