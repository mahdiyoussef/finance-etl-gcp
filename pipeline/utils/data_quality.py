"""Data quality helpers shared across extract, load, and stream layers.

These utilities enforce the quality gate thresholds defined in
``config.settings`` and expose a structured report for CI and operational logs.
"""
from __future__ import annotations

from config.settings import MAX_QUARANTINE_RATE


def build_quality_report(connection: object) -> dict[str, int | float]:
    """Return measurable data-quality checks for CI and operational logs.

    Args:
        connection: An open SQLite (or BigQuery) connection exposing
            ``execute`` and ``fetchone``.

    Returns:
        Mapping of metric names to their current values.
    """
    invoice_count: int = connection.execute(
        "select count(*) from invoices"
    ).fetchone()[0]
    ticket_event_count: int = connection.execute(
        "select count(*) from ticket_events"
    ).fetchone()[0]
    quarantine_count: int = connection.execute(
        "select count(*) from quarantine"
    ).fetchone()[0]
    orphan_invoice_count: int = connection.execute("""
        select count(*) from invoices i
        left join customers c on c.customer_id = i.customer_id
        where c.customer_id is null
    """).fetchone()[0]
    negative_invoice_count: int = connection.execute(
        "select count(*) from invoices where amount_usd <= 0"
    ).fetchone()[0]

    total = invoice_count or 1
    quarantine_rate: float = round(quarantine_count / total, 4)

    return {
        "invoice_count": invoice_count,
        "ticket_event_count": ticket_event_count,
        "quarantine_count": quarantine_count,
        "quarantine_rate": quarantine_rate,
        "orphan_invoice_count": orphan_invoice_count,
        "negative_invoice_count": negative_invoice_count,
    }


def assert_quality_gate(report: dict[str, int | float]) -> None:
    """Raise ``RuntimeError`` when any critical quality threshold is breached.

    Args:
        report: Output of ``build_quality_report``.

    Raises:
        RuntimeError: If invoice count is zero, orphan/negative invoices exist,
            or the quarantine rate exceeds ``MAX_QUARANTINE_RATE``.
    """
    if report["invoice_count"] == 0:
        raise RuntimeError("Quality gate failed: no invoices loaded")
    if report["orphan_invoice_count"] > 0:
        raise RuntimeError(
            f"Quality gate failed: {report['orphan_invoice_count']} orphan invoices"
        )
    if report["negative_invoice_count"] > 0:
        raise RuntimeError(
            f"Quality gate failed: {report['negative_invoice_count']} negative invoices"
        )
    if report["quarantine_rate"] > MAX_QUARANTINE_RATE:
        raise RuntimeError(
            f"Quality gate failed: quarantine rate {report['quarantine_rate']:.1%} "
            f"exceeds threshold {MAX_QUARANTINE_RATE:.1%}"
        )

