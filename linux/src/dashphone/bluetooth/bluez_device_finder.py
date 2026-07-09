"""Finds a paired Android phone via BlueZ over D-Bus.

Only handles discovery ("which paired device is a phone"). Talking to
`pactl` to actually move audio to/from that device lives in
audio_router.py; the two are combined by hfp_manager.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import dbus

_BLUEZ_SERVICE = "org.bluez"
_DEVICE_INTERFACE = "org.bluez.Device1"
_OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"

# Bluetooth "Class of Device" is a 24-bit field; bits 8-12 hold the Major
# Device Class. 0x02 is "Phone". Same bit math as isPhoneClass() in the
# macOS app's HFPManager.swift, so both apps agree on what counts as a phone.
_MAJOR_DEVICE_CLASS_MASK = 0x1F
_MAJOR_DEVICE_CLASS_SHIFT = 8
_PHONE_MAJOR_DEVICE_CLASS = 0x02


@dataclass(frozen=True)
class BluetoothPhone:
    mac_address: str
    name: str
    connected: bool


def _major_device_class(class_of_device: int) -> int:
    return (class_of_device >> _MAJOR_DEVICE_CLASS_SHIFT) & _MAJOR_DEVICE_CLASS_MASK


def _to_phone(device_properties: dict) -> BluetoothPhone:
    return BluetoothPhone(
        mac_address=str(device_properties.get("Address", "")),
        name=str(device_properties.get("Alias") or device_properties.get("Name") or "unnamed"),
        connected=bool(device_properties.get("Connected", False)),
    )


def paired_phones() -> list[BluetoothPhone]:
    """All paired devices that identify themselves as a phone. Raises
    dbus.exceptions.DBusException if bluetoothd is not reachable - callers
    treat that as "Bluetooth audio routing is unavailable right now"."""
    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object(_BLUEZ_SERVICE, "/"), _OBJECT_MANAGER_INTERFACE)
    managed_objects = manager.GetManagedObjects()

    phones = []
    for interfaces in managed_objects.values():
        device = interfaces.get(_DEVICE_INTERFACE)
        if device is None or not bool(device.get("Paired", False)):
            continue
        if _major_device_class(int(device.get("Class", 0))) != _PHONE_MAJOR_DEVICE_CLASS:
            continue
        phones.append(_to_phone(device))
    return phones


def find_paired_phone() -> BluetoothPhone | None:
    """The phone to route call audio for: the connected one if there is
    exactly one, otherwise the first paired phone found."""
    phones = paired_phones()
    if not phones:
        return None
    phones.sort(key=lambda phone: phone.connected, reverse=True)
    return phones[0]
