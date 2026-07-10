"""Tests for HfpManager.start()'s bounded startup-scan retry behavior."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dbus.exceptions import DBusException
from PySide6.QtCore import QCoreApplication

from dashphone.bluetooth import hfp_manager as hfp_manager_module
from dashphone.bluetooth.bluez_device_finder import BluetoothPhone
from dashphone.bluetooth.hfp_manager import HfpManager

_APP = QCoreApplication.instance() or QCoreApplication([])


def _run_timers_synchronously(fn, *args, **kwargs):
    """Patch QTimer.singleShot to invoke its callback immediately, so
    the bounded retry loop runs to completion within a single test
    without needing a real Qt event loop wait."""
    with patch.object(hfp_manager_module.QTimer, "singleShot", staticmethod(lambda _ms, callback: callback())):
        return fn(*args, **kwargs)


class HfpManagerStartupScanRetryTests(unittest.TestCase):
    def test_retries_on_dbus_exception_then_succeeds(self):
        phone = BluetoothPhone(name="Pixel", mac_address="AA:BB:CC:DD:EE:FF", connected=True)
        calls = {"count": 0}

        def fake_find_paired_phone():
            calls["count"] += 1
            if calls["count"] < 3:
                raise DBusException("BlueZ not reachable yet")
            return phone

        manager = HfpManager()
        statuses = []
        manager.status_changed.connect(statuses.append)

        with patch.object(hfp_manager_module, "find_paired_phone", side_effect=fake_find_paired_phone):
            _run_timers_synchronously(manager.start)

        self.assertEqual(calls["count"], 3)
        self.assertEqual(manager._phone, phone)
        self.assertEqual(statuses, ["Found paired phone: Pixel"])

    def test_gives_up_after_max_attempts(self):
        def fake_find_paired_phone():
            raise DBusException("BlueZ never comes up")

        manager = HfpManager()
        statuses = []
        manager.status_changed.connect(statuses.append)

        with patch.object(hfp_manager_module, "find_paired_phone", side_effect=fake_find_paired_phone) as mocked:
            _run_timers_synchronously(manager.start)
            self.assertEqual(mocked.call_count, hfp_manager_module._STARTUP_SCAN_ATTEMPTS)

        self.assertIsNone(manager._phone)
        # No paired-phone status should be emitted - this is a
        # BlueZ-unreachable failure, not a "zero phones paired" result.
        self.assertEqual(statuses, [])

    def test_no_retry_when_zero_paired_phones_found(self):
        manager = HfpManager()
        statuses = []
        manager.status_changed.connect(statuses.append)

        with patch.object(hfp_manager_module, "find_paired_phone", return_value=None) as mocked:
            _run_timers_synchronously(manager.start)
            self.assertEqual(mocked.call_count, 1)

        self.assertIsNone(manager._phone)
        self.assertEqual(statuses, ["No paired phone found"])


class HfpManagerPactlNotInstalledTests(unittest.TestCase):
    def test_gives_up_immediately_when_pactl_not_installed(self):
        phone = BluetoothPhone(name="Pixel", mac_address="AA:BB:CC:DD:EE:FF", connected=True)
        manager = HfpManager()
        manager._phone = phone
        manager._routing_active = True

        statuses = []
        manager.status_changed.connect(statuses.append)

        with patch.object(
            hfp_manager_module.audio,
            "list_cards",
            side_effect=hfp_manager_module.audio.PactlNotInstalledError(
                "pactl is not installed (package: pulseaudio-utils)"
            ),
        ) as mocked, self.assertLogs(hfp_manager_module.logger, level="WARNING") as logs:
            _run_timers_synchronously(manager._attempt_switch, 1)

        # Only one attempt should have happened - no retry loop for a
        # permanent condition.
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(len(logs.records), 1)
        self.assertTrue(any("pactl is not installed" in status for status in statuses))

    def test_still_retries_on_transient_audio_router_error(self):
        phone = BluetoothPhone(name="Pixel", mac_address="AA:BB:CC:DD:EE:FF", connected=True)
        manager = HfpManager()
        manager._phone = phone
        manager._routing_active = True

        with patch.object(
            hfp_manager_module.audio,
            "list_cards",
            side_effect=hfp_manager_module.audio.AudioRouterError("transient failure"),
        ) as mocked:
            _run_timers_synchronously(manager._attempt_switch, 1)

        self.assertEqual(mocked.call_count, hfp_manager_module._MAX_ATTEMPTS)


if __name__ == "__main__":
    unittest.main()
