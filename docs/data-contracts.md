# Data contracts

## Invoice source contract

The external source contains 31 columns. FinPulse consumes the following
canonical fields:

| Canonical field | Source aliases | Type | Required |
|---|---|---|---|
| `invoice_id` | `invoice_id`, `id` | string | yes |
| `customer_id` | `customer_id`, `customer`, `client_id` | string | yes |
| `customer_name` | `customer_name`, `customer` | string | no |
| `invoice_date` | `invoice_date`, `issue_date`, `date` | date | yes |
| `due_date` | `due_date`, `payment_due_date` | date | yes |
| `amount_local` | `amount_local`, `total_amount`, `amount` | numeric | yes |
| `currency` | `currency`, `currency_code` | string | no, defaults to USD |
| `amount_usd` | derived from `amount_local * fx_rate` | numeric | yes |
| `status` | `status`, `payment_status` | string | yes |
| `paid_date` | `paid_date`, `payment_date` | date | no |

The source may contain additional columns. Unknown columns are not silently
promoted into curated facts; they remain available in the original landing
file for schema-drift investigation.

## Ticket-event contract

Every event must contain:

```json
{
  "event_id": "evt-123",
  "ticket_id": "ticket-123",
  "customer_id": "customer-123",
  "event_type": "status_changed",
  "status": "open",
  "category": "billing",
  "priority": "high",
  "event_ts": "2026-01-31T12:00:00Z"
}
```

`event_id` is the idempotency key. `event_ts` is the event-time field used for
ordering lifecycle state. Pub/Sub message IDs are transport metadata and must
not replace the business event ID.

FX conversion uses a versioned rate snapshot for the invoice date. A missing
rate is quarantined; source amounts are never relabeled as USD.

## Metadata contract

Curated raw rows should include:

```text
_ingested_at   timestamp
_source_file   string
_schema_version string
_record_hash   string
```

These fields support replay, lineage, deduplication, and incident analysis.

## Compatibility policy

- Adding a nullable source column is backward compatible.
- Renaming a source column requires an alias update and fixture coverage.
- Removing a required field is a breaking change.
- Changing invoice-key semantics requires a migration and historical impact
  assessment.

## AR aging contract

The AR aging mart is evaluated as of the requested report date. Open invoices
are assigned to exactly one bucket: `current`, `1-30`, `31-60`, `61-90`, or
`90+`. Paid, cancelled, and disputed invoices are not included in open AR.
