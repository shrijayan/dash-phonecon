"""Unit tests for CallLogController: outgoing REQUEST_CALL_LOG shape,
incoming CALL_LOG_RESULT parsing, and CallLogEntry display helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from dashphone.state.call_log_controller import CALL_TYPE_INCOMING, CALL_TYPE_MISSED, CALL_TYPE_OUTGOING, CallLogController, CallLogEntry

_app = QApplication.instance() or QApplication([])


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def __call__(self, message: dict) -> None:
        self.sent.append(message)


class CallLogControllerOutgoingTests(unittest.TestCase):
    def test_refresh_sends_request_call_log(self) -> None:
        sender = FakeSender()
        controller = CallLogController(send_json=sender)
        controller.refresh()
        self.assertEqual(sender.sent, [{"type": "REQUEST_CALL_LOG"}])


class CallLogControllerIncomingTests(unittest.TestCase):
    def test_call_log_result_populates_entries(self) -> None:
        controller = CallLogController(send_json=FakeSender())
        received = []
        controller.call_log_updated.connect(received.append)

        controller.handle_event({
            "type": "CALL_LOG_RESULT",
            "calls": [
                {"number": "+1111", "name": "Alice", "call_type": CALL_TYPE_INCOMING, "timestamp": 1000, "duration": 30},
                {"number": "+2222", "name": "", "call_type": CALL_TYPE_MISSED, "timestamp": 2000, "duration": 0},
            ],
        })

        self.assertEqual(len(controller.entries), 2)
        self.assertEqual(controller.entries[0].number, "+1111")
        self.assertEqual(len(received), 1)

    def test_empty_call_log_result(self) -> None:
        controller = CallLogController(send_json=FakeSender())
        controller.handle_event({"type": "CALL_LOG_RESULT", "calls": []})
        self.assertEqual(controller.entries, [])

    def test_unrelated_message_types_ignored(self) -> None:
        controller = CallLogController(send_json=FakeSender())
        controller.handle_event({"type": "CONTACTS_RESULT", "contacts": []})
        self.assertEqual(controller.entries, [])


class CallLogEntryDisplayTests(unittest.TestCase):
    def test_call_type_label_incoming(self) -> None:
        entry = CallLogEntry("+1", "", CALL_TYPE_INCOMING, 0, 0)
        self.assertEqual(entry.call_type_label, "Incoming")

    def test_call_type_label_outgoing(self) -> None:
        entry = CallLogEntry("+1", "", CALL_TYPE_OUTGOING, 0, 0)
        self.assertEqual(entry.call_type_label, "Outgoing")

    def test_call_type_label_missed(self) -> None:
        entry = CallLogEntry("+1", "", CALL_TYPE_MISSED, 0, 0)
        self.assertEqual(entry.call_type_label, "Missed")

    def test_call_type_label_unknown_falls_back(self) -> None:
        entry = CallLogEntry("+1", "", 99, 0, 0)
        self.assertEqual(entry.call_type_label, "Unknown")

    def test_display_name_prefers_name(self) -> None:
        entry = CallLogEntry("+1555", "Alice", CALL_TYPE_INCOMING, 0, 0)
        self.assertEqual(entry.display_name, "Alice")

    def test_display_name_falls_back_to_number(self) -> None:
        entry = CallLogEntry("+1555", "", CALL_TYPE_INCOMING, 0, 0)
        self.assertEqual(entry.display_name, "+1555")


if __name__ == "__main__":
    unittest.main()
