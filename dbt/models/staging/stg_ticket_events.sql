-- Grain: one row per raw ticket event after type normalization.
{{ config(materialized='view') }}

select
  cast(event_id as string) as event_id,
  cast(ticket_id as string) as ticket_id,
  cast(customer_id as string) as customer_id,
  cast(event_type as string) as event_type,
  lower(cast(status as string)) as status,
  cast(category as string) as category,
  lower(cast(priority as string)) as priority,
  cast(event_ts as timestamp) as event_ts,
  cast(_ingested_at as timestamp) as _ingested_at
from {{ source('raw', 'ticket_events') }}
