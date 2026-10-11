"""Deterministic synthetic source-data generation."""

from __future__ import annotations

import csv
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def generate_landing(output: Path, customers: int = 25, invoices: int = 100, seed: int = 7) -> Path:
    """Generate deterministic source files with known dirty records.

    Args:
        output: Root directory receiving the landing files.
        customers: Number of synthetic customer dimension rows.
        invoices: Number of valid synthetic invoice rows.
        seed: Random seed used to make reruns reproducible.

    Returns:
        The normalized output root path.
    """
    rng = random.Random(seed)
    landing = output / "landing"
    landing.mkdir(parents=True, exist_ok=True)
    run_date = date(2026, 1, 31)
    customer_rows = [
        {"customer_id": f"C{i:04d}", "customer_name": f"Customer {i:04d}",
         "segment": rng.choice(["SMB", "Mid-market", "Enterprise"]),
         "region": rng.choice(["NA", "EMEA", "APAC"])}
        for i in range(1, customers + 1)
    ]
    with (landing / "customers.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=customer_rows[0].keys())
        writer.writeheader()
        writer.writerows(customer_rows)

    invoice_rows: list[dict[str, str]] = []
    for i in range(1, invoices + 1):
        issued = run_date - timedelta(days=rng.randint(0, 90))
        amount = round(rng.uniform(100, 10000), 2)
        customer = rng.choice(customer_rows)
        paid = rng.random() < 0.72
        paid_date = issued + timedelta(days=rng.randint(5, 75)) if paid else None
        invoice_rows.append({
            "invoice_id": f"I{i:06d}", "customer_id": customer["customer_id"],
            "invoice_date": issued.isoformat(), "due_date": (issued + timedelta(days=30)).isoformat(),
            "amount_usd": f"{amount:.2f}", "status": "paid" if paid else "open",
            "paid_date": paid_date.isoformat() if paid_date else "",
        })
    invoice_rows.append(dict(invoice_rows[0]))  # intentional duplicate
    invoice_rows.append({**invoice_rows[1], "invoice_id": "I-BAD", "amount_usd": "not-a-number"})
    with (landing / "invoices_2026-01-31.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=invoice_rows[0].keys())
        writer.writeheader()
        writer.writerows(invoice_rows)

    events: list[dict[str, str]] = []
    for i in range(1, max(2, invoices // 5)):
        ticket = f"T{i:05d}"
        customer = rng.choice(customer_rows)["customer_id"]
        created = datetime(2026, 1, 30, 12, tzinfo=timezone.utc) + timedelta(hours=i)
        close_delay = 48 if i % 3 == 0 else 6
        events.extend([
            {"event_id": f"E{i:05d}-1", "ticket_id": ticket, "customer_id": customer,
             "event_type": "created", "status": "open", "category": "billing",
             "priority": "high" if i % 3 == 0 else "normal", "event_ts": created.isoformat()},
            {"event_id": f"E{i:05d}-2", "ticket_id": ticket, "customer_id": customer,
             "event_type": "closed", "status": "closed", "category": "billing",
             "priority": "high" if i % 3 == 0 else "normal",
             "event_ts": (created + timedelta(hours=close_delay)).isoformat()},
        ])
    events.append(dict(events[0]))  # intentional streaming duplicate
    with (landing / "ticket_events_2026-01-31.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")
        handle.write('{"event_id":"BAD","ticket_id":"","customer_id":"C0001"}\n')
    return output
