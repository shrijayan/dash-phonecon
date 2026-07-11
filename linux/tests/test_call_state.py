"""Unit tests for CallStateController: message-in -> state-out, and
command-out -> JSON-out. No Qt event loop, no network, no display needed.

Run with:  python3 -m unittest discover -s linux/tests -t linux
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import QApplication

from dashphone.protocol import MessageType
from dashphone.state import CallPhase, CallStateController

# QObject signal/slot plumbing wants an application instance to exist, even
# for tests that never enter an event loop. Use QApplication (not just
# QCoreApplication) so that if this module happens to run first during
# `discover`, other test modules in the same process (e.g. test_tray_icon.py,
# which constructs a QSystemTrayIcon) inherit a GUI-capable singleton instead
# of a bare QCoreApplication - the latter segfaults QSystemTrayIcon.
_app = QApplication.instance() or QApplication(sys.argv[:1])


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

    def test_dial_emits_dial_type_with_number(self) -> None:
        self.controller.dial("+15551234567")
        self.assertEqual(self.sent_messages, [{"type": "DIAL", "number": "+15551234567"}])

    def test_toggle_mute_sends_mute_true_and_updates_state(self) -> None:
        self.controller.handle_event({"type": "CALL_ACTIVE"})
        self.controller.toggle_mute()
        self.assertEqual(self.sent_messages[-1], {"type": "MUTE", "muted": True})
        self.assertTrue(self.controller.state.is_muted)

    def test_toggle_mute_twice_unmutes(self) -> None:
        self.controller.handle_event({"type": "CALL_ACTIVE"})
        self.controller.toggle_mute()
        self.controller.toggle_mute()
        self.assertEqual(self.sent_messages[-1], {"type": "MUTE", "muted": False})
        self.assertFalse(self.controller.state.is_muted)

    def test_new_call_starts_unmuted(self) -> None:
        """Mute must not leak from one call into the next."""
        self.controller.handle_event({"type": "CALL_ACTIVE"})
        self.controller.toggle_mute()
        self.controller.handle_event({"type": "CALL_ENDED"})
        self.controller.handle_event({"type": "CALL_ACTIVE"})
        self.assertFalse(self.controller.state.is_muted)

    def test_state_changed_signal_fires_on_every_transition(self) -> None:
        seen_phases: list[CallPhase] = []
        self.controller.state_changed.connect(lambda state: seen_phases.append(state.phase))

        self.controller.handle_event({"type": "CALL_RINGING", "number": "1", "name": "A"})
        self.controller.handle_event({"type": "CALL_ACTIVE"})
        self.controller.handle_event({"type": "CALL_ENDED"})

        self.assertEqual(seen_phases, [CallPhase.RINGING, CallPhase.ACTIVE, CallPhase.IDLE])

    def test_call_missed_fires_when_ringing_ends_without_going_active(self) -> None:
        missed: list[tuple[str, str]] = []
        self.controller.call_missed.connect(lambda name, number: missed.append((name, number)))

        self.controller.handle_event(
            {"type": "CALL_RINGING", "number": "+155****4567", "name": "John Doe"}
        )
        self.controller.handle_event({"type": "CALL_ENDED"})

        self.assertEqual(missed, [("John Doe", "+155****4567")])
        self.assertEqual(self.controller.state.phase, CallPhase.IDLE)

    def test_call_missed_does_not_fire_for_a_completed_call(self) -> None:
        missed: list[tuple[str, str]] = []
        self.controller.call_missed.connect(lambda name, number: missed.append((name, number)))

        self.controller.handle_event(
            {"type": "CALL_RINGING", "number": "+155****4567", "name": "John Doe"}
        )
        self.controller.handle_event({"type": "CALL_ACTIVE"})
        self.controller.handle_event({"type": "CALL_ENDED"})

        self.assertEqual(missed, [])

    def test_call_missed_does_not_fire_when_ending_from_idle(self) -> None:
        """A stray CALL_ENDED with no prior RINGING/ACTIVE shouldn't be
        reported as a missed call - there was never a call to miss."""
        missed: list[tuple[str, str]] = []
        self.controller.call_missed.connect(lambda name, number: missed.append((name, number)))

        self.controller.handle_event({"type": "CALL_ENDED"})

        self.assertEqual(missed, [])


if __name__ == "__main__":
    unittest.main()
