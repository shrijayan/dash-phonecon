"""Unit tests for TrayIcon's bind-error status handling.

QSystemTrayIcon needs a real QApplication (not just QCoreApplication) even
under QT_QPA_PLATFORM=offscreen - constructing one under QCoreApplication
alone segfaults. No real tray/display is required beyond that; showMessage()
is confirmed callable without raising under the offscreen platform.

Run with:  QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m unittest discover -s tests -t . -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import QApplication

from dashphone.state import CallState
from dashphone.ui.tray_icon import TrayIcon

_app = QApplication.instance() or QApplication(sys.argv[:1])


def _make_tray() -> TrayIcon:
    return TrayIcon(on_hangup=lambda: None, on_quit=lambda: None, device_label="This device: 192.168.1.5:8765")


class TrayIconBindErrorTests(unittest.TestCase):
    def test_starts_with_not_connected_status(self) -> None:
        tray = _make_tray()
        self.assertEqual(tray._status_action.text(), "Not Connected")

    def test_bind_error_overrides_status_label(self) -> None:
        tray = _make_tray()
        tray.set_bind_error("Port 8765 unavailable: [Errno 98] Address already in use")
        self.assertEqual(
            tray._status_action.text(),
            "Port 8765 unavailable: [Errno 98] Address already in use",
        )

    def test_bind_error_overrides_tooltip(self) -> None:
        tray = _make_tray()
        tray.set_bind_error("Port 8765 unavailable")
        self.assertIn("Port 8765 unavailable", tray.toolTip())

    def test_bind_error_persists_across_connection_changes(self) -> None:
        """Once bound has failed, the server never actually calls
        connection_changed - but guard against a stale/late signal still
        clobbering the error message back to a misleading "Not Connected"."""
        tray = _make_tray()
        tray.set_bind_error("Port 8765 unavailable")
        tray.set_connected(False)
        self.assertEqual(tray._status_action.text(), "Port 8765 unavailable")

    def test_bind_error_does_not_raise_calling_show_message(self) -> None:
        tray = _make_tray()
        try:
            tray.set_bind_error("Port 8765 unavailable")
        except Exception as error:  # pragma: no cover - failure path
            self.fail(f"set_bind_error raised unexpectedly: {error}")

    def test_normal_status_labels_unaffected_when_no_bind_error(self) -> None:
        tray = _make_tray()
        tray.set_connected(True)
        self.assertEqual(tray._status_action.text(), "Connected \u2014 No Active Call")
        tray.set_state(CallState.idle())
        self.assertEqual(tray._status_action.text(), "Connected \u2014 No Active Call")

    def test_notify_missed_call_does_not_raise(self) -> None:
        tray = _make_tray()
        try:
            tray.notify_missed_call("John Doe", "+155****4567")
        except Exception as error:  # pragma: no cover - failure path
            self.fail(f"notify_missed_call raised unexpectedly: {error}")

    def test_notify_missed_call_falls_back_to_number_without_name(self) -> None:
        tray = _make_tray()
        # Just needs to not raise and not require a name - showMessage's
        # actual displayed text isn't introspectable via QSystemTrayIcon's
        # public API, so this asserts the no-name code path is safe.
        try:
            tray.notify_missed_call("", "+155****4567")
        except Exception as error:  # pragma: no cover - failure path
            self.fail(f"notify_missed_call raised unexpectedly: {error}")

    def test_notify_missed_call_falls_back_to_unknown_without_name_or_number(self) -> None:
        tray = _make_tray()
        try:
            tray.notify_missed_call("", "")
        except Exception as error:  # pragma: no cover - failure path
            self.fail(f"notify_missed_call raised unexpectedly: {error}")

    def test_device_label_reflects_constructor_initial_value(self) -> None:
        tray = _make_tray()
        self.assertEqual(tray._device_action.text(), "This device: 192.168.1.5:8765")

    def test_set_device_label_updates_the_menu_item(self) -> None:
        tray = _make_tray()
        tray.set_device_label("This device: 10.0.0.7:8765")
        self.assertEqual(tray._device_action.text(), "This device: 10.0.0.7:8765")

    def test_set_device_label_reflects_no_network_case(self) -> None:
        tray = _make_tray()
        tray.set_device_label("myhost: no network connection")
        self.assertEqual(tray._device_action.text(), "myhost: no network connection")


if __name__ == "__main__":
    unittest.main()
