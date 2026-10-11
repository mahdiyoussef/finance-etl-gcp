import tempfile
import unittest
from datetime import date
from pathlib import Path

from finpulse.generator import generate_landing
from finpulse.pipeline import BatchLoader


class PipelineTest(unittest.TestCase):
    """Verify local loading, quality controls, and mart materialization."""

    def test_dirty_data_is_quarantined_and_reruns_are_idempotent(self) -> None:
        """Ensure dirty records are quarantined and reruns do not duplicate data."""
        with tempfile.TemporaryDirectory() as directory:
            root = generate_landing(Path(directory), customers=5, invoices=20)
            loader = BatchLoader(root / "finpulse.db")
            try:
                loader.load(root / "landing")
                first = loader.connection.execute("select count(*) from invoices").fetchone()[0]
                first_events = loader.connection.execute("select count(*) from ticket_events").fetchone()[0]
                quarantined = loader.connection.execute("select count(*) from quarantine").fetchone()[0]
                loader.load(root / "landing")
                self.assertEqual(first, loader.connection.execute("select count(*) from invoices").fetchone()[0])
                self.assertEqual(first_events, loader.connection.execute("select count(*) from ticket_events").fetchone()[0])
                self.assertGreaterEqual(quarantined, 2)
                loader.build_marts(root / "marts")
                self.assertTrue((root / "marts" / "ar_aging.csv").exists())
                self.assertTrue((root / "marts" / "dso.csv").exists())
                self.assertTrue((root / "marts" / "invoice_risk.csv").exists())
                self.assertTrue((root / "marts" / "support_cost.csv").exists())
                quality = loader.quality_report()
                self.assertGreater(quality["quarantine_count"], 0)
                self.assertEqual(quality["orphan_invoice_count"], 0)
                self.assertEqual(quality["negative_invoice_count"], 0)
                latest = loader.connection.execute("select count(*) from tickets_latest").fetchone()[0]
                self.assertGreater(latest, 0)
            finally:
                loader.close()

    def test_load_uses_report_date_for_landing_filenames(self) -> None:
        """Load generated files for a non-default date without code changes."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            landing = root / "landing"
            landing.mkdir()
            (landing / "customers.csv").write_text(
                "customer_id,customer_name,segment,region\nC1,Acme,SMB,NA\n",
                encoding="utf-8",
            )
            (landing / "invoices_2026-02-01.csv").write_text(
                "invoice_id,customer_id,invoice_date,due_date,amount_usd,status,paid_date\n"
                "I1,C1,2026-02-01,2026-03-01,10,open,\n",
                encoding="utf-8",
            )
            (landing / "ticket_events_2026-02-01.jsonl").write_text("", encoding="utf-8")
            loader = BatchLoader(root / "finpulse.db")
            try:
                loader.load(landing, date(2026, 2, 1))
                self.assertEqual(
                    loader.connection.execute("select count(*) from invoices").fetchone()[0], 1
                )
            finally:
                loader.close()


if __name__ == "__main__":
    unittest.main()
