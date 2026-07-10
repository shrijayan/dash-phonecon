"""Unit tests for normalize_dial_number (pure logic, no Qt needed) and the
tray's dial action wiring."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import QApplication

from dashphone.ui.tray_icon import TrayIcon, normalize_dial_number

_app = QApplication.instance() or QApplication(sys.argv[:1])


class NormalizeDialNumberTests(unittest.TestCase):
    def test_plain_digits_unchanged(self) -> None:
        self.assertEqual(normalize_dial_number("5551234567"), "5551234567")

    def test_strips_spaces_dashes_and_parens(self) -> None:
        self.assertEqual(normalize_dial_number("(555) 123-4567"), "5551234567")

    def test_keeps_leading_plus_for_international_format(self) -> None:
        self.assertEqual(normalize_dial_number("+1 555-123-4567"), "+15551234567")

    def test_blank_input_returns_empty(self) -> None:
        self.assertEqual(normalize_dial_number("   "), "")

    def test_no_digits_returns_empty(self) -> None:
        self.assertEqual(normalize_dial_number("+---"), "")


def _make_tray(on_dial=None) -> TrayIcon:
    return TrayIcon(
        on_hangup=lambda: None,
        on_quit=lambda: None,
        device_label="This device: 192.168.1.5:8765",
        on_dial=on_dial,
    )


class TrayIconDialActionTests(unittest.TestCase):
    def test_dial_action_present_in_menu(self) -> None:
        tray = _make_tray()
        self.assertIn(tray._dial_action, tray.contextMenu().actions())

    def test_dial_action_enabled_by_default(self) -> None:
        tray = _make_tray()
        self.assertTrue(tray._dial_action.isEnabled())


if __name__ == "__main__":
    unittest.main()
