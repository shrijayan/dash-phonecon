"""Unit tests for normalize_dial_number (pure logic, no Qt needed) - still
used by PhoneWindow's merged dial entry now that the standalone tray
"Dial..." menu action and PhoneWindow Dialer tab have been removed (dialing
lives in the Contacts tab's dial-entry row instead, see phone_window.py)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dashphone.ui.tray_icon import normalize_dial_number


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


if __name__ == "__main__":
    unittest.main()
