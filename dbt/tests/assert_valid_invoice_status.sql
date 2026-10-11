select invoice_id
from {{ ref('fct_invoices') }}
where status not in ('paid', 'open', 'overdue', 'disputed', 'late')
