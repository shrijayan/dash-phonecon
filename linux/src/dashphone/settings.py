"""Tiny persisted app settings (currently: the wireless-debugging adb port
for screen share). A single small JSON file under XDG_CONFIG_HOME - not a
full settings system, just enough to remember one value across restarts.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_ADB_PORT = 5555


def _settings_path() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    directory = config_home / "dash-phonecon"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "settings.json"


def load_adb_port() -> int:
    """The port to use for `adb connect <phone-ip>:<port>` when starting
    screen share. Defaults to 5555 (the fixed port `adb tcpip 5555` uses),
    but Android 11+'s "Wireless debugging" toggle (paired via QR/pairing
    code, no USB) assigns a random port each time instead - there's no
    public API for an app to read that back, so this is a user-set override
    (see TrayIcon's "Set Screen Share Port…" action) persisted here."""
    try:
        data = json.loads(_settings_path().read_text())
        port = int(data.get("adb_port", DEFAULT_ADB_PORT))
        if 1 <= port <= 65535:
            return port
        logger.warning("Ignoring out-of-range stored adb_port=%s - using default", port)
    except FileNotFoundError:
        pass
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        logger.warning("Ignoring unreadable settings file (%s) - using default adb_port", error)
    return DEFAULT_ADB_PORT


def save_adb_port(port: int) -> None:
    _settings_path().write_text(json.dumps({"adb_port": port}))
    logger.info("Screen share adb port set to %s", port)
