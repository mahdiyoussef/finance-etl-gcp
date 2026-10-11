# Interview and demo guide

## Two-minute demo

1. State the business problem: finance needs DSO, aging, payment risk, and
   support cost in one governed platform.
2. Show the repository layout and explain the separation of ingestion,
   orchestration, transformation, infrastructure, and serving.
3. Run `make test` and show intentional dirty-data tests.
4. Show the Airflow DAG dependency chain.
5. Show the dbt models and freshness/test gates.
6. Explain Terraform dev/prod separation and WIF.
7. Show the generated AR aging, DSO, risk, and support-cost marts.
8. Close with measured results and the next GCP deployment step.

## Questions this project prepares you for

### How is the pipeline idempotent?

Invoice and event business keys are unique. Replays use `insert or ignore`
locally and `MERGE`/incremental unique keys in BigQuery/dbt. File manifests
prevent redundant source downloads.

### Why retain raw events?

Current ticket state cannot explain duration, late arrival, or historical
corrections. The append-only event fact preserves those audit details.

### How do you handle bad data?

Malformed records are quarantined with their original serialized payload and
validation error. Critical referential and financial checks fail the quality
gate rather than producing success-shaped output.

### Why Airflow and dbt together?

Airflow coordinates external side effects and task dependencies. dbt owns
warehouse SQL, lineage, tests, incremental models, and source freshness.

### How would this scale?

Move landing to GCS, replace local batch loading with BigQuery load jobs or
Dataflow, use BigQuery partitioning/clustering, retain event-time Beam
processing, and run the same dbt contracts in Composer.

### What would you measure?

- Source-to-mart freshness
- Accepted, duplicate, and quarantined rows
- Bytes scanned per dashboard query
- Dataflow worker duration
- DSO and overdue AR
- SLA breach rate
- High-risk invoice amount

