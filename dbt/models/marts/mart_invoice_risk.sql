-- Grain: one row per invoice with a deterministic report-date risk band.
{{ config(materialized='table') }}

{% set report_date = var('report_date', modules.datetime.date.today()) %}

select
  invoice_id,
  customer_id,
  amount_usd,
  due_date,
  case
    when status = 'open' and due_date < date('{{ report_date }}') then 'high'
    when status = 'open' then 'medium'
    else 'low'
  end as risk_band
from {{ ref('fct_invoices') }}
