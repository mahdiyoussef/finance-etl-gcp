"""Command-line interface for local Finance ETL execution."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.extract.synthetic_data_generator import generate_landing
from pipeline.load.batch_warehouse_loader import BatchLoader


def main() -> None:
    """Parse CLI arguments and execute the requested local pipeline command."""
    parser = argparse.ArgumentParser(description="Run the local Finance ETL MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--output", type=Path, default=Path("data/demo"))
    run.add_argument("--customers", type=int, default=25)
    run.add_argument("--invoices", type=int, default=100)
    run.add_argument("--report-date", default="2026-01-31")
    run.add_argument("--endpoint", default=None, help="SQL Server endpoint (e.g. localhost:1433)")
    args = parser.parse_args()
    if args.command == "run":
        root = generate_landing(args.output, args.customers, args.invoices)
        loader = BatchLoader(root / "finance.db", endpoint=args.endpoint)
        try:
            loader.load(root / "landing")
            from datetime import date
            loader.build_marts(root / "marts", date.fromisoformat(args.report_date))
            print(f"Quality report: {loader.quality_report()}")
            print(f"Pipeline completed: {root}")
        finally:
            loader.close()
