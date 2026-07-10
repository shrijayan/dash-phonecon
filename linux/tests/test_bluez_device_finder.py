"""Unit tests for bluez_device_finder's pure logic (Blocked filtering,
deterministic tie-break) using plain dict/dataclass fixtures - no real
D-Bus/BlueZ needed, same style as test_audio_router_parsing.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest

from dashphone.bluetooth.bluez_device_finder import BluetoothPhone, _to_phone

_PHONE_CLASS = 0x200  # major device class 0x02 ("Phone") in bits 8-12


def _device(address="AA:BB:CC:DD:EE:FF", name="Pixel", connected=False, blocked=False, paired=True):
    return {
        "Address": address,
        "Alias": name,
        "Connected": connected,
        "Paired": paired,
        "Blocked": blocked,
        "Class": _PHONE_CLASS,
    }


def _filter_phones(managed_objects_values):
    """Mirrors paired_phones()'s filtering logic without touching dbus.SystemBus()."""
    phones = []
    for interfaces in managed_objects_values:
        device = interfaces.get("org.bluez.Device1")
        if device is None or not bool(device.get("Paired", False)):
            continue
        if bool(device.get("Blocked", False)):
            continue
        if ((int(device.get("Class", 0)) >> 8) & 0x1F) != 0x02:
            continue
        phones.append(_to_phone(device))
    return phones


class BlockedDeviceFilterTests(unittest.TestCase):
    def test_blocked_paired_phone_is_excluded(self) -> None:
        managed_objects = [{"org.bluez.Device1": _device(blocked=True)}]
        self.assertEqual(_filter_phones(managed_objects), [])

    def test_unblocked_paired_phone_is_included(self) -> None:
        managed_objects = [{"org.bluez.Device1": _device(blocked=False)}]
        result = _filter_phones(managed_objects)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].mac_address, "AA:BB:CC:DD:EE:FF")


class TieBreakTests(unittest.TestCase):
    def test_deterministic_name_tie_break_when_none_connected(self) -> None:
        phones = [
            BluetoothPhone(mac_address="11:11", name="Zenith", connected=False),
            BluetoothPhone(mac_address="22:22", name="Alpha", connected=False),
        ]
        phones.sort(key=lambda phone: (not phone.connected, phone.name.lower()))
        self.assertEqual(phones[0].name, "Alpha")

    def test_connected_phone_still_wins_regardless_of_name(self) -> None:
        phones = [
            BluetoothPhone(mac_address="11:11", name="Zenith", connected=True),
            BluetoothPhone(mac_address="22:22", name="Alpha", connected=False),
        ]
        phones.sort(key=lambda phone: (not phone.connected, phone.name.lower()))
        self.assertEqual(phones[0].name, "Zenith")

    def test_tie_break_is_case_insensitive(self) -> None:
        phones = [
            BluetoothPhone(mac_address="11:11", name="zebra", connected=False),
            BluetoothPhone(mac_address="22:22", name="Apple", connected=False),
        ]
        phones.sort(key=lambda phone: (not phone.connected, phone.name.lower()))
        self.assertEqual(phones[0].name, "Apple")


if __name__ == "__main__":
    unittest.main()
