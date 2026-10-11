"""Command-line interface for local FinPulse execution."""

from __future__ import annotations

import argparse
from pathlib import Path

from .generator import generate_landing
from .pipeline import BatchLoader


def main() -> None:
    """Parse CLI arguments and execute the requested local pipeline command."""
    parser = argparse.ArgumentParser(description="Run the local FinPulse MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--output", type=Path, default=Path("data/demo"))
    run.add_argument("--customers", type=int, default=25)
    run.add_argument("--invoices", type=int, default=100)
    run.add_argument("--report-date", default="2026-01-31")
    args = parser.parse_args()
    if args.command == "run":
        root = generate_landing(args.output, args.customers, args.invoices)
        loader = BatchLoader(root / "finpulse.db")
        try:
            loader.load(root / "landing")
            from datetime import date
            loader.build_marts(root / "marts", date.fromisoformat(args.report_date))
            print(f"Quality report: {loader.quality_report()}")
            print(f"Pipeline completed: {root}")
        finally:
            loader.close()
