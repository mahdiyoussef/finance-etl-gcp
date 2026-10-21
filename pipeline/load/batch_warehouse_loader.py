"""Batch warehouse loader: load validated landing data and materialize analytical marts in SQL Server."""

from __future__ import annotations

import csv
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .db_engine import (
    DatabaseEndpointConfig,
    WarehouseConnection,
    create_warehouse_connection,
)

logger = logging.getLogger(__name__)


class BatchLoader:
    """Load validated landing data and materialize analytical marts in SQL Server."""

    def __init__(
        self,
        database: Path | str | None = None,
        endpoint: str | None = None,
        config: DatabaseEndpointConfig | None = None,
    ):
        """Open or initialize warehouse connection at SQL Server endpoint or local database."""
        if endpoint is not None:
            endpoint_cfg = config or DatabaseEndpointConfig.from_env()
            endpoint_cfg.endpoint = endpoint
            if ":" in endpoint:
                endpoint_cfg.host = endpoint.split(":")[0]
                endpoint_cfg.port = int(endpoint.split(":")[1])
            else:
                endpoint_cfg.host = endpoint
            self.connection: WarehouseConnection = create_warehouse_connection(
                database=database, config=endpoint_cfg
            )
        elif isinstance(database, WarehouseConnection):
            self.connection = database
        else:
            self.connection = create_warehouse_connection(database=database, config=config)

        self.database = database
        self._migrate_invoice_schema()
        self.last_load_stats = {
            "source_rows": 0, "valid_rows": 0, "inserted_rows": 0,
            "duplicate_rows": 0, "quarantined_rows": 0,
        }

    def _migrate_invoice_schema(self) -> None:
        """Ensure currency and audit columns exist on invoices table."""
        try:
            if getattr(self.connection, "dialect", "sqlite") == "sqlserver":
                columns = {
                    row[0].lower()
                    for row in self.connection.execute(
                        "select column_name from information_schema.columns where table_name = 'invoices'"
                    ).fetchall()
                }
            else:
                columns = {
                    row[1].lower()
                    for row in self.connection.execute("pragma table_info(invoices)").fetchall()
                }
            if "amount_local" not in columns:
                self.connection.execute("alter table invoices add amount_local real")
                self.connection.execute("update invoices set amount_local = amount_usd where amount_local is null")
            if "currency" not in columns:
                self.connection.execute("alter table invoices add currency varchar(3) not null default 'USD'")
            if "fx_rate" not in columns:
                self.connection.execute("alter table invoices add fx_rate real not null default 1.0")
            self.connection.commit()
        except Exception as exc:
            logger.debug("Invoice schema check: %s", exc)

    def _quarantine(self, source: str, record: object, error: str) -> None:
        """Persist a rejected source record and its validation error."""
        self.connection.execute(
            "insert into quarantine values (?, ?, ?)",
            (source, json.dumps(record, sort_keys=True), error),
        )

    def load(self, landing: Path, report_date: date | None = None) -> None:
        """Load landing files for a report date and refresh derived ticket state.

        Args:
            landing: Directory containing customer, invoice, and event files.
            report_date: Date suffix used by generated landing files. When
                omitted, the historical 2026-01-31 default is retained.
        """
        suffix = (report_date or date(2026, 1, 31)).isoformat()
        is_sqlserver = getattr(self.connection, "dialect", "sqlite") == "sqlserver"

        with (landing / "customers.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if is_sqlserver:
                    self.connection.execute(
                        """if not exists (select 1 from customers where customer_id = ?)
                        insert into customers (customer_id, customer_name, segment, region) values (?, ?, ?, ?)
                        else
                        update customers set customer_name = ?, segment = ?, region = ? where customer_id = ?""",
                        (row["customer_id"], row["customer_id"], row["customer_name"], row["segment"], row["region"],
                         row["customer_name"], row["segment"], row["region"], row["customer_id"]),
                    )
                else:
                    self.connection.execute(
                        "insert or replace into customers values (?, ?, ?, ?)",
                        (row["customer_id"], row["customer_name"], row["segment"], row["region"]),
                    )

        with (landing / f"invoices_{suffix}.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                try:
                    if not row["invoice_id"] or not row["customer_id"]:
                        raise ValueError("missing invoice identity")
                    amount = float(row["amount_usd"])
                    invoice_date = date.fromisoformat(row["invoice_date"])
                    due_date = date.fromisoformat(row["due_date"])
                    if amount <= 0:
                        raise ValueError("invoice amount must be positive")
                    if due_date < invoice_date:
                        raise ValueError("due date precedes invoice date")
                    status = row["status"].strip().lower()
                    if status not in {"open", "paid", "overdue", "disputed", "cancelled"}:
                        raise ValueError(f"unsupported invoice status: {status}")
                    paid_date = date.fromisoformat(row["paid_date"]) if row["paid_date"] else None
                    if paid_date and paid_date < invoice_date:
                        raise ValueError("paid date precedes invoice date")

                    if is_sqlserver:
                        self.connection.execute(
                            """if not exists (select 1 from invoices where invoice_id = ?)
                            insert into invoices
                            (invoice_id, customer_id, invoice_date, due_date,
                             amount_local, currency, fx_rate, amount_usd, status, paid_date)
                            values (?, ?, ?, ?, ?, 'USD', 1.0, ?, ?, ?)""",
                            (row["invoice_id"], row["invoice_id"], row["customer_id"], invoice_date.isoformat(),
                             due_date.isoformat(), amount, amount, status,
                             paid_date.isoformat() if paid_date else None),
                        )
                    else:
                        self.connection.execute(
                            """insert or ignore into invoices
                            (invoice_id, customer_id, invoice_date, due_date,
                             amount_local, currency, fx_rate, amount_usd, status, paid_date)
                            values (?, ?, ?, ?, ?, 'USD', 1.0, ?, ?, ?)""",
                            (row["invoice_id"], row["customer_id"], invoice_date.isoformat(),
                             due_date.isoformat(), amount, amount, status,
                             paid_date.isoformat() if paid_date else None),
                        )
                except (KeyError, TypeError, ValueError, OverflowError) as exc:
                    self._quarantine("invoices", row, str(exc))

        with (landing / f"ticket_events_{suffix}.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                try:
                    required = ("event_id", "ticket_id", "customer_id", "event_type", "status",
                                "category", "priority", "event_ts")
                    if any(not row.get(field) for field in required):
                        raise ValueError("missing required ticket event field")
                    datetime.fromisoformat(row["event_ts"])
                    if is_sqlserver:
                        self.connection.execute(
                            """if not exists (select 1 from ticket_events where event_id = ?)
                            insert into ticket_events values (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (row["event_id"], *(row[field] for field in required)),
                        )
                    else:
                        self.connection.execute(
                            "insert or ignore into ticket_events values (?, ?, ?, ?, ?, ?, ?, ?)",
                            tuple(row[field] for field in required),
                        )
                except (KeyError, TypeError, ValueError) as exc:
                    self._quarantine("ticket_events", row, str(exc))

        self.connection.commit()
        self._refresh_latest_tickets()

    def _refresh_latest_tickets(self) -> None:
        """Materialize the latest ticket state from the append-only event fact."""
        self.connection.execute("delete from tickets_latest")
        self.connection.execute("""
          insert into tickets_latest
          with ranked as (
            select e.*,
              row_number() over (
                partition by ticket_id order by event_ts desc, event_id desc
              ) as row_num,
              min(event_ts) over (partition by ticket_id) as first_event_ts,
              max(case when status = 'closed' then event_ts end)
                over (partition by ticket_id) as closed_event_ts
            from ticket_events e
          )
          select ticket_id, customer_id, status, category, priority,
            first_event_ts, closed_event_ts
          from ranked
          where row_num = 1
        """)
        self.connection.commit()

    def build_marts(self, output: Path, report_date: date = date(2026, 1, 31)) -> None:
        """Write AR, DSO, risk, and support marts for a reporting date."""
        output.mkdir(parents=True, exist_ok=True)
        report_date_text = report_date.isoformat()
        is_sqlserver = getattr(self.connection, "dialect", "sqlite") == "sqlserver"

        if is_sqlserver:
            aging_sql = """
              select c.segment, c.region,
                round(sum(case when i.status = 'open' and i.due_date >= ?
                  then i.amount_usd else 0 end), 2) as current_amt,
                round(sum(case when i.status = 'open' and datediff(day, i.due_date, ?) between 1 and 30
                  then i.amount_usd else 0 end), 2) as d1_30,
                round(sum(case when i.status = 'open' and datediff(day, i.due_date, ?) between 31 and 60
                  then i.amount_usd else 0 end), 2) as d31_60,
                round(sum(case when i.status = 'open' and datediff(day, i.due_date, ?) between 61 and 90
                  then i.amount_usd else 0 end), 2) as d61_90,
                round(sum(case when i.status = 'open' and datediff(day, i.due_date, ?) > 90
                  then i.amount_usd else 0 end), 2) as d90_plus,
                round(sum(case when i.status = 'open' and i.due_date < ?
                  then i.amount_usd else 0 end), 2) as overdue_amt
              from invoices i join customers c on c.customer_id = i.customer_id
              group by c.segment, c.region order by c.segment, c.region
            """
            dso_sql = """
              select c.segment, c.region,
                round(sum(case when i.paid_date is not null
                  then i.amount_usd * datediff(day, i.invoice_date, i.paid_date)
                  else 0 end) /
                  nullif(sum(case when i.paid_date is not null then i.amount_usd else 0 end), 0), 2) as dso
              from invoices i join customers c on c.customer_id = i.customer_id
              group by c.segment, c.region order by c.segment, c.region
            """
            support_sql = """
              select c.customer_id, c.segment, c.region,
                count(distinct e.ticket_id) as ticket_count,
                sum(case when e.priority = 'high' and e.status != 'closed' then 1 else 0 end) as open_high_priority_events,
                sum(case when e.status = 'closed'
                  and (datediff(hour, (select min(e2.event_ts) from ticket_events e2 where e2.ticket_id = e.ticket_id), e.event_ts)) > 24
                  then 1 else 0 end) as sla_breach_count,
                round(count(distinct e.ticket_id) * 25.0, 2) as support_cost_usd
              from ticket_events e join customers c on c.customer_id = e.customer_id
              group by c.customer_id, c.segment, c.region order by c.customer_id
            """
        else:
            aging_sql = """
              select c.segment, c.region,
                round(sum(case when i.status = 'open' and i.due_date >= ?
                  then i.amount_usd else 0 end), 2) current_amt,
                round(sum(case when i.status = 'open' and julianday(?) - julianday(i.due_date) between 1 and 30
                  then i.amount_usd else 0 end), 2) d1_30,
                round(sum(case when i.status = 'open' and julianday(?) - julianday(i.due_date) between 31 and 60
                  then i.amount_usd else 0 end), 2) d31_60,
                round(sum(case when i.status = 'open' and julianday(?) - julianday(i.due_date) between 61 and 90
                  then i.amount_usd else 0 end), 2) d61_90,
                round(sum(case when i.status = 'open' and julianday(?) - julianday(i.due_date) > 90
                  then i.amount_usd else 0 end), 2) d90_plus,
                round(sum(case when i.status = 'open' and i.due_date < ?
                  then i.amount_usd else 0 end), 2) overdue_amt
              from invoices i join customers c on c.customer_id = i.customer_id
              group by c.segment, c.region order by c.segment, c.region
            """
            dso_sql = """
              select c.segment, c.region,
                round(sum(case when i.paid_date is not null
                  then i.amount_usd * (julianday(i.paid_date) - julianday(i.invoice_date))
                  else 0 end) /
                  nullif(sum(case when i.paid_date is not null then i.amount_usd else 0 end), 0), 2) dso
              from invoices i join customers c on c.customer_id = i.customer_id
              group by c.segment, c.region order by c.segment, c.region
            """
            support_sql = """
              select c.customer_id, c.segment, c.region,
                count(distinct e.ticket_id) ticket_count,
                sum(case when e.priority = 'high' and e.status != 'closed' then 1 else 0 end)
                  open_high_priority_events,
                sum(case when e.status = 'closed'
                  and (julianday(e.event_ts) - julianday(
                    (select min(e2.event_ts) from ticket_events e2
                     where e2.ticket_id = e.ticket_id))) > 24 then 1 else 0 end) sla_breach_count,
                round(count(distinct e.ticket_id) * 25.0, 2) support_cost_usd
              from ticket_events e join customers c on c.customer_id = e.customer_id
              group by c.customer_id, c.segment, c.region order by c.customer_id
            """

        aging = self.connection.execute(
            aging_sql,
            (report_date_text, report_date_text, report_date_text, report_date_text,
             report_date_text, report_date_text),
        ).fetchall()
        self._write_csv(
            output / "ar_aging.csv",
            ["segment", "region", "current_amt", "d1_30", "d31_60", "d61_90", "d90_plus", "overdue_amt"],
            aging,
        )

        dso = self.connection.execute(dso_sql).fetchall()
        self._write_csv(output / "dso.csv", ["segment", "region", "dso"], dso)

        risk = self.connection.execute("""
          select i.invoice_id, i.customer_id, i.amount_usd, i.due_date,
            case when i.status = 'open' and i.due_date < ? then 'high'
                 when i.status = 'open' then 'medium' else 'low' end risk_band
          from invoices i order by i.invoice_id
        """, (report_date_text,)).fetchall()
        self._write_csv(
            output / "invoice_risk.csv",
            ["invoice_id", "customer_id", "amount_usd", "due_date", "risk_band"],
            risk,
        )

        support = self.connection.execute(support_sql).fetchall()
        self._write_csv(
            output / "support_cost.csv",
            ["customer_id", "segment", "region", "ticket_count",
             "open_high_priority_events", "sla_breach_count",
             "support_cost_usd"],
            support,
        )

    def quality_report(self) -> dict[str, int]:
        """Return measurable data-quality checks for CI and operational logs."""
        checks = {
            "invoice_count": self.connection.execute("select count(*) from invoices").fetchone()[0],
            "ticket_event_count": self.connection.execute(
                "select count(*) from ticket_events").fetchone()[0],
            "quarantine_count": self.connection.execute(
                "select count(*) from quarantine").fetchone()[0],
            "orphan_invoice_count": self.connection.execute("""
                select count(*) from invoices i
                left join customers c on c.customer_id = i.customer_id
                where c.customer_id is null
            """).fetchone()[0],
            "negative_invoice_count": self.connection.execute(
                "select count(*) from invoices where amount_usd <= 0").fetchone()[0],
        }
        return checks

    @staticmethod
    def _write_csv(path: Path, headers: list[str], rows: list[tuple]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)

    def close(self) -> None:
        self.connection.close()
