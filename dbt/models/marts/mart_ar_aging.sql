-- Grain: one row per customer with current and overdue receivables.
{{ config(materialized='table') }}

{% set report_date = var('report_date', modules.datetime.date.today()) %}

select
  customer_id,
  sum(if(status = 'open' and due_date >= date('{{ report_date }}'), amount_usd, 0)) as current_amount,
  sum(if(status = 'open' and date_diff(date('{{ report_date }}'), due_date, day) between 1 and 30,
    amount_usd, 0)) as d1_30_amount,
  sum(if(status = 'open' and date_diff(date('{{ report_date }}'), due_date, day) between 31 and 60,
    amount_usd, 0)) as d31_60_amount,
  sum(if(status = 'open' and date_diff(date('{{ report_date }}'), due_date, day) between 61 and 90,
    amount_usd, 0)) as d61_90_amount,
  sum(if(status = 'open' and date_diff(date('{{ report_date }}'), due_date, day) > 90,
    amount_usd, 0)) as d90_plus_amount,
  sum(if(status = 'open' and due_date < date('{{ report_date }}'), amount_usd, 0)) as overdue_amount
from {{ ref('fct_invoices') }}
group by customer_id
