-- FinPulse BigQuery ML late-payment prediction model contract.
-- BigQuery ML contract. Run after dbt builds finpulse_core.fct_invoices.
create or replace model `${PROJECT_ID}.finpulse_ml.late_payment_model`
options (
  model_type = 'logistic_reg',
  input_label_cols = ['is_late'],
  auto_class_weights = true
) as
select
  amount_usd,
  date_diff(due_date, invoice_date, day) as payment_terms_days,
  extract(month from invoice_date) as invoice_month,
  if(status in ('overdue', 'late'), 1, 0) as is_late
from `${PROJECT_ID}.finpulse_core.fct_invoices`
where paid_date is not null;
