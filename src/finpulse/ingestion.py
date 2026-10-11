"""Streaming ingestion adapters for external invoice files."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import date
from pathlib import Path


FIELD_ALIASES = {
    "invoice_id": ("invoice_id", "id"),
    "customer_id": ("customer_id", "customer", "client_id"),
    "customer_name": ("customer_name", "customer"),
    "customer_region": ("customer_country", "customer_state", "region"),
    "invoice_date": ("invoice_date", "issue_date", "date"),
    "due_date": ("due_date", "payment_due_date"),
    "amount": ("amount_usd", "total_amount", "amount", "invoice_amount"),
    "currency": ("currency", "currency_code"),
    "status": ("status", "payment_status"),
    "paid_date": ("paid_date", "payment_date"),
}
SUPPORTED_STATUSES = {"open", "paid", "overdue", "disputed", "cancelled"}
DEFAULT_FX_RATES = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.74, "AUD": 0.66}


def _value(row: dict[str, str], candidates: Iterable[str]) -> str:
    """Return the first populated source value matching a field alias."""
    return next((row[name].strip() for name in candidates if name in row), "")


def load_external_dataset(
    loader: object,
    files: list[Path],
    batch_size: int = 10_000,
    fx_rates: dict[str, float] | None = None,
) -> int:
    """Stream source CSVs into the warehouse without creating a combined file.

    Args:
        loader: Batch loader exposing a SQLite connection and quarantine method.
        files: Complete source CSV paths, normally train and test splits.
        batch_size: Number of invoices/customers flushed per database batch.

    Returns:
        Number of source rows accepted for insertion.
    """
    connection = loader.connection
    pending_customers: dict[str, tuple[str, str]] = {}
    invoice_batch: list[tuple[object, ...]] = []
    rates = fx_rates or DEFAULT_FX_RATES
    stats = {"source_rows": 0, "valid_rows": 0, "inserted_rows": 0,
             "duplicate_rows": 0, "quarantined_rows": 0}
    for source in files:
        with source.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                stats["source_rows"] += 1
                invoice_id = _value(row, FIELD_ALIASES["invoice_id"])
                customer_id = _value(row, FIELD_ALIASES["customer_id"]) or "UNKNOWN"
                customer_name = _value(row, FIELD_ALIASES["customer_name"]) or customer_id
                region = _value(row, FIELD_ALIASES["customer_region"]) or "Unknown"
                pending_customers[customer_id] = (customer_name, region)
                try:
                    amount_local = float(_value(row, FIELD_ALIASES["amount"]))
                    currency = (_value(row, FIELD_ALIASES["currency"]) or "USD").upper()
                    invoice_date = _value(row, FIELD_ALIASES["invoice_date"])
                    due_date = _value(row, FIELD_ALIASES["due_date"])
                    if not invoice_id or not invoice_date or not due_date:
                        raise ValueError("missing invoice identity or dates")
                    issued = date.fromisoformat(invoice_date)
                    due = date.fromisoformat(due_date)
                    if amount_local <= 0:
                        raise ValueError("invoice amount must be positive")
                    if due < issued:
                        raise ValueError("due date precedes invoice date")
                    if currency not in rates:
                        raise ValueError(f"missing FX rate for currency: {currency}")
                    status = _value(row, FIELD_ALIASES["status"]).lower() or "open"
                    if status not in SUPPORTED_STATUSES:
                        raise ValueError(f"unsupported invoice status: {status}")
                    paid_date = _value(row, FIELD_ALIASES["paid_date"]) or None
                    if paid_date and date.fromisoformat(paid_date) < issued:
                        raise ValueError("paid date precedes invoice date")
                    invoice_batch.append((
                        invoice_id, customer_id, invoice_date, due_date, amount_local,
                        currency, rates[currency], amount_local * rates[currency],
                        status, paid_date,
                    ))
                    stats["valid_rows"] += 1
                except (TypeError, ValueError, OverflowError) as exc:
                    loader._quarantine("external_invoices", row, str(exc))
                    stats["quarantined_rows"] += 1
                if len(invoice_batch) >= batch_size:
                    inserted, duplicate = _flush(connection, invoice_batch)
                    stats["inserted_rows"] += inserted
                    stats["duplicate_rows"] += duplicate
                    invoice_batch.clear()
                if len(pending_customers) >= batch_size:
                    _flush_customers(connection, pending_customers)
                    pending_customers.clear()
    if invoice_batch:
        inserted, duplicate = _flush(connection, invoice_batch)
        stats["inserted_rows"] += inserted
        stats["duplicate_rows"] += duplicate
    if pending_customers:
        _flush_customers(connection, pending_customers)
    connection.commit()
    loader._refresh_latest_tickets()
    loader.last_load_stats = stats
    return stats["valid_rows"]


def _flush(connection: object, rows: list[tuple[object, ...]]) -> tuple[int, int]:
    """Insert a bounded invoice batch and return inserted and duplicate counts."""
    before = connection.total_changes
    connection.executemany(
        """insert or ignore into invoices
        (invoice_id, customer_id, invoice_date, due_date, amount_local,
         currency, fx_rate, amount_usd, status, paid_date)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows
    )
    inserted = connection.total_changes - before
    return inserted, len(rows) - inserted


def _flush_customers(connection: object, customers: dict[str, tuple[str, str]]) -> None:
    """Insert a bounded customer batch with source-derived region values."""
    connection.executemany(
        "insert or replace into customers values (?, ?, ?, ?)",
        [(key, name, "Unknown", region) for key, (name, region) in customers.items()],
    )
