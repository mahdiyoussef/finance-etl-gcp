# Governance and observability

## Data classification

| Field category | Examples | Control |
|---|---|---|
| Public/synthetic | Invoice IDs, synthetic amounts | Normal dataset IAM |
| Internal finance | Payment status, AR aging | Finance group access |
| Customer PII | Name, email, city | Policy tags and masking |
| Operational metadata | Ingestion time, source file | Analyst read access |

The public dataset is synthetic, but the controls mirror production practice.

## Identity and access

- Use one service account per workload: ingestion, transformation, and
  dashboard access.
- Grant raw write access only to ingestion identities.
- Grant marts read access to analysts and Looker Studio.
- Use Workload Identity Federation for GitHub Actions; never store JSON keys.

## Sensitive data

Customer email and names must receive BigQuery policy tags in production.
Development datasets should use masked or synthetic values. The current
public dataset is synthetic but still should not be treated as a reason to
skip access controls.

## Operational signals

Track accepted rows, quarantined rows, duplicate rows, source freshness, and
mart completion timestamp. Alert when quarantine rate exceeds 1%, a source is
more than 24 hours late, or a critical mart has no rows.

## Incident response

1. Stop downstream promotion if the quality gate fails.
2. Inspect the Airflow task log and `quarantine` records.
3. Identify whether the issue is source corruption, schema drift, or code.
4. Replay the affected source after correction.
5. Re-run dbt tests and freshness checks.
6. Record the incident, affected logical date, and remediation.
