"""Finds this computer's LAN IP address, so the tray menu can tell you what
to type into the Android app - no more guessing or running `ip addr`.
"""

from __future__ import annotations

import socket

from dashphone.network.call_server import DEFAULT_PORT


def local_ip_address() -> str | None:
    """Best-effort local IP address.

    Opens a UDP socket "connected" to a public address and reads back which
    local interface the OS would use to reach it. No packets are actually
    sent for a UDP connect(), so this works offline-safely and needs no
    special permissions. Returns None if there is no network route at all.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
    except OSError:
        return None


def device_label() -> str:
    """A one-line label for the tray menu, e.g. 'This device: 192.168.1.23:8765'."""
    ip_address = local_ip_address()
    if ip_address is None:
        return f"{socket.gethostname()}: no network connection"
    return f"This device: {ip_address}:{DEFAULT_PORT}"
