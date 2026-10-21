-- SCD Type 2 snapshot: captures invoice status changes over time.
-- Run daily so status transitions (open → overdue → paid) are preserved.
{% snapshot snap_invoice_status %}

{{
  config(
    target_schema = 'finance_snapshots',
    unique_key    = 'invoice_id',
    strategy      = 'check',
    check_cols    = ['status', 'paid_date', 'amount_usd']
  )
}}

select
  invoice_id,
  customer_id,
  invoice_date,
  due_date,
  amount_usd,
  status,
  paid_date
from {{ source('raw', 'invoices') }}

{% endsnapshot %}

