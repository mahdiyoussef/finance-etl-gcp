"""Optional Apache Beam ticket-event pipeline contract."""

from __future__ import annotations

import json
from typing import Any

try:
    import apache_beam as beam
except ImportError:  # pragma: no cover - exercised when Beam is not installed
    beam = None


REQUIRED = ("event_id", "ticket_id", "customer_id", "event_type", "status",
            "category", "priority", "event_ts")


def parse_event(raw: bytes | str) -> dict[str, Any]:
    """Decode and validate one ticket event from Pub/Sub payload data."""
    value = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    if any(not value.get(field) for field in REQUIRED):
        raise ValueError("missing required ticket event field")
    return value


def build_pipeline(options: object, subscription: str, output: str, dead_letter: str) -> object:
    """Build a Beam pipeline that validates events and writes valid/DLQ output.

    Args:
        options: Beam pipeline options, including streaming and runner settings.
        subscription: Fully qualified Pub/Sub subscription name.
        output: Destination prefix for valid event output.
        dead_letter: Destination prefix for rejected event output.

    Returns:
        An Apache Beam pipeline ready for ``run``.

    Raises:
        RuntimeError: If Apache Beam is not installed.
    """
    if beam is None:
        raise RuntimeError("apache-beam is required to build the streaming pipeline")

    class Parse(beam.DoFn):
        """Validate Pub/Sub messages and route malformed payloads to the DLQ."""

        def process(self, message: bytes):
            """Yield a valid event or a structured dead-letter record."""
            try:
                yield parse_event(message)
            except (ValueError, json.JSONDecodeError) as exc:
                yield beam.pvalue.TaggedOutput("dead_letter", {
                    "raw": message.decode("utf-8", errors="replace"),
                    "error": str(exc),
                })

    pipeline = beam.Pipeline(options=options)
    parsed = (
        pipeline
        | "ReadPubSub" >> beam.io.ReadFromPubSub(subscription=subscription)
        | "ValidateEvents" >> beam.ParDo(Parse()).with_outputs("dead_letter", main="valid")
    )
    parsed.valid | "WriteRawEvents" >> beam.io.WriteToText(output)
    parsed.dead_letter | "WriteDeadLetters" >> beam.io.WriteToText(dead_letter)
    return pipeline
