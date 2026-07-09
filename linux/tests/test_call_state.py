"""Unit tests for CallStateController: message-in -> state-out, and
command-out -> JSON-out. No Qt event loop, no network, no display needed.

Run with:  python3 -m unittest discover -s linux/tests -t linux
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import QCoreApplication

from dashphone.protocol import MessageType
from dashphone.state import CallPhase, CallStateController

# QObject signal/slot plumbing wants an application instance to exist,
# even for tests that never enter an event loop.
_app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])


class CallStateControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sent_messages: list[dict] = []
        self.controller = CallStateController(send_json=self.sent_messages.append)

    def test_starts_idle(self) -> None:
        self.assertEqual(self.controller.state.phase, CallPhase.IDLE)

    def test_call_ringing_sets_number_and_name(self) -> None:
        self.controller.handle_event(
            {"type": "CALL_RINGING", "number": "+15551234567", "name": "John Doe"}
        )
        state = self.controller.state
        self.assertEqual(state.phase, CallPhase.RINGING)
        self.assertEqual(state.number, "+15551234567")
        self.assertEqual(state.name, "John Doe")

    def test_call_ringing_with_missing_name_shows_unknown(self) -> None:
        self.controller.handle_event({"type": "CALL_RINGING", "number": "+15551234567"})
        self.assertEqual(self.controller.state.display_name, "Unknown")

    def test_call_active_sets_start_time(self) -> None:
        self.controller.handle_event({"type": "CALL_ACTIVE"})
        state = self.controller.state
        self.assertEqual(state.phase, CallPhase.ACTIVE)
        self.assertIsNotNone(state.start_time)

    def test_call_ended_returns_to_idle(self) -> None:
        self.controller.handle_event({"type": "CALL_ACTIVE"})
        self.controller.handle_event({"type": "CALL_ENDED"})
        self.assertEqual(self.controller.state.phase, CallPhase.IDLE)

    def test_ping_replies_with_pong(self) -> None:
        self.controller.handle_event({"type": "PING"})
        self.assertEqual(self.sent_messages, [{"type": "PONG"}])
        # PING must not change call state
        self.assertEqual(self.controller.state.phase, CallPhase.IDLE)

    def test_unknown_message_type_is_ignored(self) -> None:
        self.controller.handle_event({"type": "SOMETHING_FROM_THE_FUTURE"})
        self.assertEqual(self.controller.state.phase, CallPhase.IDLE)
        self.assertEqual(self.sent_messages, [])

    def test_message_without_type_is_ignored(self) -> None:
        self.controller.handle_event({"number": "123"})
        self.assertEqual(self.controller.state.phase, CallPhase.IDLE)

    def test_send_command_emits_type_only_payload(self) -> None:
        self.controller.send_command(MessageType.ANSWER)
        self.assertEqual(self.sent_messages, [{"type": "ANSWER"}])

    def test_state_changed_signal_fires_on_every_transition(self) -> None:
        seen_phases: list[CallPhase] = []
        self.controller.state_changed.connect(lambda state: seen_phases.append(state.phase))

        self.controller.handle_event({"type": "CALL_RINGING", "number": "1", "name": "A"})
        self.controller.handle_event({"type": "CALL_ACTIVE"})
        self.controller.handle_event({"type": "CALL_ENDED"})

        self.assertEqual(seen_phases, [CallPhase.RINGING, CallPhase.ACTIVE, CallPhase.IDLE])


if __name__ == "__main__":
    unittest.main()
