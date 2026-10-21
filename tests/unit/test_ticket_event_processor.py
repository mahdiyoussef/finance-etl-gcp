import unittest
import json

from pipeline.stream.ticket_event_processor import parse_event


class StreamingContractTest(unittest.TestCase):
    """Verify the ticket-event validation contract."""

    def test_valid_event_is_parsed(self) -> None:
        """Accept a complete event payload without changing its fields."""
        event = {
            "event_id": "e1", "ticket_id": "t1", "customer_id": "c1",
            "event_type": "created", "status": "open", "category": "billing",
            "priority": "high", "event_ts": "2026-01-01T00:00:00+00:00",
        }
        self.assertEqual(parse_event(json.dumps(event)), event)

    def test_invalid_event_is_rejected(self) -> None:
        """Reject payloads missing required event identity fields."""
        with self.assertRaises(ValueError):
            parse_event('{"event_id": "e1"}')
