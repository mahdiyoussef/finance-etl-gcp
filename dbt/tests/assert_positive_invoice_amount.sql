select invoice_id
from {{ ref('fct_invoices') }}
where amount_usd <= 0
