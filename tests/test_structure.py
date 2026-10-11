import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class StructureTest(unittest.TestCase):
    """Verify source layout and DAG parseability without Airflow installed."""

    def test_airflow_dag_is_valid_python(self) -> None:
        """Parse the DAG source as Python syntax."""
        source = (ROOT / "dags" / "finpulse_pipeline.py").read_text(encoding="utf-8")
        ast.parse(source)

    def test_professional_directories_exist(self) -> None:
        """Require the documented top-level project directories."""
        for directory in ("src/finpulse", "dags", "scripts", "tests", "docs", "dbt"):
            self.assertTrue((ROOT / directory).is_dir(), directory)
