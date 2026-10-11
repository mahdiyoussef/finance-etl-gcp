-- Grain: one row per customer with ticket volume, SLA breaches, and cost.
{{ config(materialized='table') }}

with ticket_lifecycle as (
  select
    customer_id,
    ticket_id,
    max_by(status, event_ts) as latest_status,
    max_by(priority, event_ts) as latest_priority,
    min(event_ts) as created_at,
    max(if(status = 'closed', event_ts, null)) as closed_at
  from {{ ref('stg_ticket_events') }}
  group by customer_id, ticket_id
)
select
  customer_id,
  count(*) as ticket_count,
  countif(latest_priority = 'high' and latest_status != 'closed')
    as open_high_priority_events,
  countif(closed_at is not null
    and closed_at > timestamp_add(created_at, interval 24 hour)) as sla_breach_count,
  round(count(*) * 25, 2) as support_cost_usd
from ticket_lifecycle
group by customer_id
