"""Wireless screen mirroring, so you can see (and even control) the phone's
screen from this computer without ever touching it - the same "phone stays
in another room" goal as the rest of this app, extended from call popups to
the full screen.

Implementation: shells out to `scrcpy` (https://github.com/Genymobile/scrcpy),
pointed at the phone over `adb connect <ip>:5555` using the *same* IP address
the phone is already using for the CALL_RINGING/CALL_ACTIVE WebSocket link
(see CallServer.phone_ip_address) - no second IP to type in anywhere.

This deliberately does NOT go over our own WebSocket protocol: video needs a
real H264/adb transport, and scrcpy already solves "reconnect cleanly when
the phone drops off WiFi and comes back" - re-implementing that in our own
protocol would just be reinventing scrcpy badly. See linux/README.md for the
one-time "wireless debugging" setup this requires on the phone.

Auto-reconnect: once you click "Screen Share Phone", this manager keeps
trying (with backoff) until it's up, and re-launches automatically if the
phone drops off WiFi and comes back or scrcpy's window gets closed by a
transient disconnect - the same "no clicking required to recover" behaviour
HfpManager already uses for Bluetooth audio. Only an explicit stop() (Quit,
or picking the tray item again while active) turns this off.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from enum import Enum, auto
from typing import Callable, Optional

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from dashphone.settings import load_adb_port

logger = logging.getLogger(__name__)

ADB_WIRELESS_PORT = 5555  # fallback default; overridden by settings.load_adb_port() at call time
_ADB_CONNECT_TIMEOUT_SECONDS = 5
_RETRY_INTERVAL_MS = 3000
_MAX_AUTO_RETRIES = 20  # ~1 minute of retrying before giving up until the next manual click


class ScreenShareState(Enum):
    IDLE = auto()  # not running
    CONNECTING = auto()  # adb connect in progress (initial or retry)
    ACTIVE = auto()  # scrcpy window is up
    FAILED = auto()  # gave up after _MAX_AUTO_RETRIES; needs a manual click to try again


class ScreenShareManager(QObject):
    """Owns the scrcpy subprocess. One screen-share session at a time."""

    state_changed = Signal(object)  # emits a ScreenShareState
    error = Signal(str)  # human-readable failure reason, for a notification/dialog

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._state = ScreenShareState.IDLE
        self._wanted = False  # True from start() until an explicit stop()
        self._phone_ip_getter: Optional[Callable[[], Optional[str]]] = None
        self._retry_count = 0

    @property
    def state(self) -> ScreenShareState:
        return self._state

    @staticmethod
    def is_available() -> bool:
        """True if both `scrcpy` and `adb` are on PATH - checked up front so
        the tray menu can grey out the option with a clear reason instead of
        failing silently mid-click."""
        return shutil.which("scrcpy") is not None and shutil.which("adb") is not None

    def start(self, phone_ip_getter: Callable[[], Optional[str]]) -> None:
        """Start (or resume) screen sharing. `phone_ip_getter` is called
        fresh on every attempt - not just once - so retries pick up the
        phone's current IP/connection state rather than a stale snapshot
        from the moment you clicked.

        Safe to call while already running/retrying - a no-op, so a second
        click on the tray menu doesn't spawn a duplicate mirroring window."""
        if self._wanted:
            logger.info("Screen share already running/retrying - ignoring duplicate start()")
            return

        if not self.is_available():
            self._fail("scrcpy/adb not installed - see linux/README.md for setup")
            return

        self._wanted = True
        self._phone_ip_getter = phone_ip_getter
        self._retry_count = 0
        self._attempt_connect()

    def stop(self) -> None:
        """Turn off screen sharing and close the scrcpy window, if running.
        This is the only thing that stops auto-reconnect - call it explicitly
        (tray toggle, app quit) rather than relying on a failed attempt."""
        self._wanted = False
        self._phone_ip_getter = None
        if self._process is not None:
            self._process.kill()
            self._process = None
        self._set_state(ScreenShareState.IDLE)

    # -- internals --

    def _attempt_connect(self) -> None:
        if not self._wanted:
            return  # stop() was called while a retry was pending

        self._set_state(ScreenShareState.CONNECTING)
        phone_ip_address = self._phone_ip_getter() if self._phone_ip_getter else None

        if not phone_ip_address:
            self._retry_or_give_up("No phone connected yet - waiting for WiFi connection")
            return

        address = f"{phone_ip_address}:{load_adb_port()}"
        try:
            result = subprocess.run(
                ["adb", "connect", address],
                capture_output=True,
                text=True,
                timeout=_ADB_CONNECT_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            self._retry_or_give_up(self._locked_phone_hint(address))
            return
        except OSError as connect_error:
            self._retry_or_give_up(f"Could not reach the phone over adb at {address}: {connect_error}")
            return

        output = (result.stdout or "") + (result.stderr or "")
        if "connected to" not in output.lower() and "already connected" not in output.lower():
            if self._looks_like_locked_phone(output):
                self._retry_or_give_up(self._locked_phone_hint(address))
            else:
                self._retry_or_give_up(
                    f"adb connect to {address} failed - is Wireless debugging enabled on the phone? "
                    f"({output.strip() or 'no output'})"
                )
            return

        self._retry_count = 0
        self._launch_scrcpy(address)

    @staticmethod
    def _looks_like_locked_phone(adb_output: str) -> bool:
        """adb's error text when the phone is locked/screen-off varies by
        Android version and OEM, but these substrings cover the common
        cases: refused connections (nothing is listening because Wireless
        debugging turned itself off), and the couple of phrasings some
        vendors log about the device being asleep/locked."""
        lowered = adb_output.lower()
        return any(
            phrase in lowered
            for phrase in (
                "connection refused",
                "no route to host",
                "device offline",
                "device unauthorized",
            )
        )

    @staticmethod
    def _locked_phone_hint(address: str) -> str:
        return (
            f"Could not reach the phone at {address} - Android turns off Wireless "
            "debugging automatically whenever the screen is locked. Unlock the "
            "phone and re-check Settings → Developer options → Wireless debugging "
            "(and update the port here if it changed - pairing-code mode picks a "
            "new one each time)."
        )

    def _retry_or_give_up(self, reason: str) -> None:
        self._retry_count += 1
        if self._retry_count > _MAX_AUTO_RETRIES:
            self._fail(f"{reason} - gave up after {_MAX_AUTO_RETRIES} attempts, click again to retry")
            return
        logger.debug("Screen share retry %s/%s: %s", self._retry_count, _MAX_AUTO_RETRIES, reason)
        QTimer.singleShot(_RETRY_INTERVAL_MS, self._attempt_connect)

    def _launch_scrcpy(self, address: str) -> None:
        process = QProcess(self)
        process.setProgram("scrcpy")
        process.setArguments(
            [
                "-s",
                address,
                "--window-title",
                "Phone Screen",
                "--no-audio",
            ]
        )
        process.finished.connect(self._on_process_finished)
        process.errorOccurred.connect(lambda _err: self._on_process_finished(-1, QProcess.ExitStatus.CrashExit))
        process.start()
        self._process = process
        self._set_state(ScreenShareState.ACTIVE)

    def _on_process_finished(self, _exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._process = None
        if not self._wanted:
            self._set_state(ScreenShareState.IDLE)
            return
        # scrcpy exited (e.g. the phone dropped off WiFi) but we still want
        # screen share - go straight back into the retry loop instead of
        # requiring another manual click.
        logger.info("scrcpy exited while screen share still wanted - reconnecting")
        self._retry_count = 0
        QTimer.singleShot(_RETRY_INTERVAL_MS, self._attempt_connect)

    def _fail(self, message: str) -> None:
        logger.warning("Screen share failed: %s", message)
        self._wanted = False
        self._set_state(ScreenShareState.FAILED)
        self.error.emit(message)

    def _set_state(self, new_state: ScreenShareState) -> None:
        self._state = new_state
        self.state_changed.emit(new_state)
