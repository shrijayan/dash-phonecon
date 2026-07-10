"""Unit tests for the merged PhoneWindow: DIAL is no longer a separate
tab/feature - it's a compact entry row inside the Contacts tab, and there
are exactly 2 tabs (Contacts, Call Log)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import QApplication

from dashphone.state.call_log_controller import CallLogController
from dashphone.state.contacts_controller import ContactsController
from dashphone.ui.phone_window import PhoneWindow, _DialEntryRow

_app = QApplication.instance() or QApplication(sys.argv[:1])


class PhoneWindowMergeTests(unittest.TestCase):
    def _make_window(self) -> PhoneWindow:
        return PhoneWindow(
            contacts_controller=ContactsController(send_json=lambda m: None),
            call_log_controller=CallLogController(send_json=lambda m: None),
            on_dial=lambda number: None,
        )

    def test_exactly_two_tabs_no_standalone_dialer(self) -> None:
        window = self._make_window()
        self.assertEqual(window._tabs.count(), 2)
        labels = [window._tabs.tabText(i) for i in range(window._tabs.count())]
        self.assertTrue(any("Contacts" in label for label in labels))
        self.assertTrue(any("Call Log" in label for label in labels))
        self.assertFalse(any("Dialer" in label for label in labels))

    def test_dial_entry_row_dials_and_clears(self) -> None:
        dialed = []
        row = _DialEntryRow(on_dial=lambda number: dialed.append(number))
        row._entry.setText("5551234567")
        row._dial()
        self.assertEqual(dialed, ["5551234567"])
        self.assertEqual(row._entry.text(), "")

    def test_dial_entry_row_ignores_blank(self) -> None:
        dialed = []
        row = _DialEntryRow(on_dial=lambda number: dialed.append(number))
        row._entry.setText("   ")
        row._dial()
        self.assertEqual(dialed, [])


if __name__ == "__main__":
    unittest.main()
