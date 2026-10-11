# Release checklist

## Before development deployment

- [ ] Configure `GCP_PROJECT_ID`.
- [ ] Create and configure the dev Terraform state bucket.
- [ ] Set `TF_VAR_billing_account_id`.
- [ ] Configure Monitoring notification channels.
- [ ] Run `terraform -chdir=terraform/envs/dev plan`.
- [ ] Review the plan for region, bucket names, and dataset deletion behavior.

## Before production deployment

- [ ] Create a separate production state bucket.
- [ ] Configure a protected GitHub `prod` environment.
- [ ] Configure Workload Identity Federation.
- [ ] Grant only deployment-service-account permissions.
- [ ] Review `terraform/envs/prod` with an approver.
- [ ] Run `dbt source freshness`.
- [ ] Run `dbt build --vars '{report_date: "YYYY-MM-DD"}'`.
- [ ] Verify quarantine and freshness metrics.
- [ ] Capture query bytes scanned and pipeline duration for the project results.
- [ ] Confirm Looker Studio uses marts rather than raw tables.

## Rollback

- Roll back the application/DAG commit first.
- Do not destroy production datasets as a rollback mechanism.
- Restore a prior Terraform state only through the approved state-recovery
  procedure.
