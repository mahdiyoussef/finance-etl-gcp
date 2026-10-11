-- Grain: one row per customer with paid-invoice weighted average days to pay.
{{ config(materialized='table') }}

select
  customer_id,
  round(
    safe_divide(
      sum(if(paid_date is not null,
        amount_usd * date_diff(paid_date, invoice_date, day), 0)),
      sum(if(paid_date is not null, amount_usd, 0))
    ), 2
  ) as dso
from {{ ref('fct_invoices') }}
group by customer_id
