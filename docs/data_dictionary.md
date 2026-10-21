# Finance ETL — Data Dictionary

## Source Tables (`finance_raw`)

### `finance_raw.invoices`

| Column | Type | Description |
|---|---|---|
| `invoice_id` | STRING | Unique invoice identifier (business key) |
| `customer_id` | STRING | FK to `customers.customer_id` |
| `invoice_date` | DATE | Date the invoice was issued |
| `due_date` | DATE | Payment due date |
| `amount_local` | NUMERIC | Invoice amount in the source currency |
| `currency` | STRING | ISO 4217 currency code (e.g. USD, EUR) |
| `fx_rate` | NUMERIC | Exchange rate to USD at ingestion time |
| `amount_usd` | NUMERIC | `amount_local × fx_rate` |
| `status` | STRING | `open` / `paid` / `overdue` / `disputed` / `cancelled` |
| `paid_date` | DATE | Date payment was received (nullable) |
| `_ingested_at` | TIMESTAMP | Pipeline load timestamp |
| `_source_file` | STRING | Source CSV filename |

### `finance_raw.ticket_events`

| Column | Type | Description |
|---|---|---|
| `event_id` | STRING | Unique event identifier |
| `ticket_id` | STRING | Groups events belonging to one support ticket |
| `customer_id` | STRING | FK to `customers.customer_id` |
| `event_type` | STRING | `created` / `updated` / `escalated` / `closed` |
| `status` | STRING | `open` / `in_progress` / `escalated` / `closed` |
| `category` | STRING | `billing` / `technical` / `general` |
| `priority` | STRING | `high` / `normal` / `low` |
| `event_ts` | TIMESTAMP | When the status change occurred |
| `_ingested_at` | TIMESTAMP | Pipeline load timestamp |

## Mart Tables (`finance_marts`)

### `mart_ar_aging`

Grain: one row per customer segment × region combination.

| Column | Description |
|---|---|
| `segment` | Customer segment (SMB / Mid-market / Enterprise) |
| `region` | Geographic region (NA / EMEA / APAC) |
| `current_amt` | Open invoices not yet due |
| `d1_30` | Overdue 1–30 days |
| `d31_60` | Overdue 31–60 days |
| `d61_90` | Overdue 61–90 days |
| `d90_plus` | Overdue 90+ days |
| `overdue_amt` | Total overdue amount |

### `mart_dso`

Grain: one row per customer segment × region. DSO = weighted average days from invoice date to payment date.

### `mart_invoice_risk`

Grain: one row per invoice. `risk_band` = `high` (overdue open) / `medium` (open, not yet due) / `low` (paid/cancelled).

### `mart_support_cost`

Grain: one row per customer. Support cost is estimated at \$25 per ticket (configurable in production).

## Quarantine Table

The `quarantine` table captures every rejected source record with its validation error message and source filename for operational investigation.

## Quality Metrics

| Metric | Threshold | Action |
|---|---|---|
| `quarantine_rate` | > 5 % | Pipeline failure |
| `orphan_invoice_count` | > 0 | Pipeline failure |
| `negative_invoice_count` | > 0 | Pipeline failure |
| `invoice_count` | = 0 | Pipeline failure |

