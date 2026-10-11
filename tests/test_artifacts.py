import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class DeploymentArtifactTest(unittest.TestCase):
    """Verify deployment, warehouse, and orchestration artifact contracts."""

    def test_deployment_workflow_uses_wif(self) -> None:
        """Require OIDC/WIF authentication and Terraform apply steps."""
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
        self.assertIn("google-github-actions/auth@v2", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("terraform -chdir=terraform/envs/dev apply", workflow)

    def test_terraform_has_workload_service_account_and_alert(self) -> None:
        """Require dedicated workload IAM and quarantine monitoring."""
        iam = (ROOT / "terraform/envs/dev/iam.tf").read_text(encoding="utf-8")
        monitoring = (ROOT / "terraform/envs/dev/monitoring.tf").read_text(encoding="utf-8")
        self.assertIn("google_service_account", iam)
        self.assertIn("google_monitoring_alert_policy", monitoring)
        pubsub = (ROOT / "terraform/envs/dev/data_platform_resources.tf").read_text(encoding="utf-8")
        self.assertIn("dead_letter_policy", pubsub)
        self.assertIn("google_pubsub_subscription", pubsub)

    def test_budget_and_local_airflow_instructions_exist(self) -> None:
        """Require budget controls and a documented local Airflow command."""
        self.assertTrue((ROOT / "terraform/envs/dev/budget.tf").is_file())
        airflow = (ROOT / "airflow/README.md").read_text(encoding="utf-8")
        self.assertIn("airflow dags test", airflow)

    def test_warehouse_contract_and_airflow_compose_exist(self) -> None:
        """Require BigQuery DDL and reproducible Airflow container artifacts."""
        ddl = (ROOT / "warehouse/ddl/bigquery_warehouse_schema.sql").read_text(encoding="utf-8")
        compose = (ROOT / "docker-compose.airflow.yml").read_text(encoding="utf-8")
        self.assertIn("finpulse_raw.invoices", ddl)
        self.assertIn("require_partition_filter", ddl)
        self.assertIn("apache/airflow:2.10.5-python3.12", compose)
        dag = (ROOT / "dags/finpulse_pipeline.py").read_text(encoding="utf-8")
        self.assertIn("dbt source freshness", dag)
        self.assertIn("dbt build", dag)
        self.assertIn("profiles.yml is required", dag)

    def test_gcp_services_are_declared(self) -> None:
        """Require Terraform declarations for APIs used by the platform."""
        dev = (ROOT / "terraform/envs/dev/services.tf").read_text(encoding="utf-8")
        prod = (ROOT / "terraform/envs/prod/services.tf").read_text(encoding="utf-8")
        self.assertIn("google_project_service", dev)
        self.assertIn("google_project_service", prod)

    def test_developer_commands_and_release_checklist_exist(self) -> None:
        """Require one-command development workflows and release guidance."""
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        checklist = (ROOT / "docs/release-checklist.md").read_text(encoding="utf-8")
        self.assertIn("PYTHONPATH=src $(PYTHON) -m unittest", makefile)
        self.assertIn("Workload Identity Federation", checklist)

    def test_dbt_contract_files_exist(self) -> None:
        """Require the complete dbt model and source contract."""
        for path in (
            "dbt/dbt_project.yml",
            "dbt/models/staging/stg_invoices.sql",
            "dbt/models/core/fct_invoices.sql",
            "dbt/models/marts/mart_ar_aging.sql",
            "dbt/models/schema.yml",
        ):
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertTrue((ROOT / "dbt/models/marts/mart_dso.sql").is_file())
        self.assertTrue((ROOT / "dbt/models/marts/mart_invoice_risk.sql").is_file())
        self.assertTrue((ROOT / "dbt/models/marts/mart_support_cost.sql").is_file())
        self.assertTrue((ROOT / "dbt/models/staging/sources.yml").is_file())

    def test_production_environment_is_protected(self) -> None:
        """Require production labels and dataset deletion protection."""
        main = (ROOT / "terraform/envs/prod/data_platform_resources.tf").read_text(encoding="utf-8")
        self.assertIn("environment = \"prod\"", main)
        self.assertIn("delete_contents_on_destroy = false", main)
