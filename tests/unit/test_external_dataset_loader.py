import csv
import tempfile
import unittest
from pathlib import Path

from pipeline.extract.external_dataset_loader import load_external_dataset
from pipeline.load.batch_warehouse_loader import BatchLoader


class ExternalIngestionTest(unittest.TestCase):
    """Verify normalization of multiple external invoice file formats."""

    def test_streams_and_normalizes_multiple_source_files(self) -> None:
        """Ensure train/test-shaped files stream into common warehouse columns."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = []
            for name, invoice_id in (("train.csv", "1"), ("test.csv", "2")):
                path = root / name
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=[
                        "invoice_id", "customer_id", "customer_name", "customer_country",
                        "invoice_date", "due_date", "total_amount", "payment_status", "payment_date",
                    ])
                    writer.writeheader()
                    writer.writerow({
                        "invoice_id": invoice_id, "customer_id": "C1",
                        "customer_name": "Acme", "customer_country": "US",
                        "invoice_date": "2025-01-01", "due_date": "2025-01-31",
                        "total_amount": "100.50", "payment_status": "Paid",
                        "payment_date": "2025-01-15",
                    })
                files.append(path)
            loader = BatchLoader(root / "test.db")
            try:
                self.assertEqual(load_external_dataset(loader, files, batch_size=1), 2)
                self.assertEqual(loader.connection.execute(
                    "select count(*) from invoices").fetchone()[0], 2)
                self.assertEqual(loader.connection.execute(
                    "select status from invoices where invoice_id = '1'").fetchone()[0], "paid")
                self.assertEqual(loader.connection.execute(
                    "select region from customers where customer_id = 'C1'").fetchone()[0], "US")
                amount = loader.connection.execute(
                    "select amount_local, currency, fx_rate, amount_usd from invoices where invoice_id = '1'"
                ).fetchone()
                self.assertEqual(tuple(amount), (100.5, "USD", 1.0, 100.5))
                self.assertEqual(loader.last_load_stats["inserted_rows"], 2)
            finally:
                loader.close()

    def test_converts_supported_currency_and_quarantines_invalid_rows(self) -> None:
        """Convert a non-USD source amount and reject invalid business values."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "invoice_id", "customer_id", "invoice_date", "due_date",
                    "total_amount", "currency", "payment_status", "payment_date",
                ])
                writer.writeheader()
                writer.writerows([
                    {"invoice_id": "EUR-1", "customer_id": "C1", "invoice_date": "2025-01-01",
                     "due_date": "2025-01-31", "total_amount": "100", "currency": "EUR",
                     "payment_status": "paid", "payment_date": "2025-01-15"},
                    {"invoice_id": "BAD-1", "customer_id": "C1", "invoice_date": "2025-01-01",
                     "due_date": "2024-12-31", "total_amount": "100", "currency": "USD",
                     "payment_status": "open", "payment_date": ""},
                ])
            loader = BatchLoader(Path(directory) / "test.db")
            try:
                self.assertEqual(load_external_dataset(loader, [path]), 1)
                row = loader.connection.execute(
                    "select amount_local, currency, fx_rate, amount_usd from invoices"
                ).fetchone()
                self.assertEqual(row[0], 100)
                self.assertEqual(row[1], "EUR")
                self.assertEqual(row[2], 1.08)
                self.assertEqual(row[3], 108)
                self.assertEqual(loader.last_load_stats["quarantined_rows"], 1)
            finally:
                loader.close()
