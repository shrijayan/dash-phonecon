"""Best-effort Bluetooth call-audio routing (Phase 4).

When a call becomes active, tries to switch the system's default
microphone/speaker to the paired Android phone's Bluetooth Hands-Free
connection, so you can talk through this computer's speakers/mic instead
of the phone itself - the same idea as a car kit. When the call ends,
switches back to whatever was active before.

This is deliberately best-effort: if no phone is paired, `pactl`/BlueZ are
unavailable, or the phone's Android/OEM Bluetooth stack does not allow the
"Phone calls" toggle for this computer, routing simply does not happen and
everything else in the app (popup, answer/decline/hang up over WiFi) keeps
working normally - see linux/README.md for the manual pairing steps this
depends on and how to check what went wrong.
"""

from __future__ import annotations

import logging

from dbus.exceptions import DBusException
from PySide6.QtCore import QObject, QTimer, Signal

from dashphone.bluetooth import audio_router as audio
from dashphone.bluetooth.bluez_device_finder import BluetoothPhone, find_paired_phone

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 20
_RETRY_INTERVAL_MS = 1000


class HfpManager(QObject):
    status_changed = Signal(str)  # human-readable status, surfaced in logs today

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._phone: BluetoothPhone | None = None
        self._routing_active = False
        self._saved_sink: str | None = None
        self._saved_source: str | None = None

    def start(self) -> None:
        """Look for a paired phone once, at app startup."""
        try:
            self._phone = find_paired_phone()
        except DBusException as error:
            logger.info("Bluetooth audio routing disabled (BlueZ not reachable): %s", error)
            return

        if self._phone is None:
            logger.info("No paired phone found - Bluetooth call audio routing is disabled")
            self._emit_status("No paired phone found")
        else:
            logger.info("Paired phone for call audio: %s (%s)", self._phone.name, self._phone.mac_address)
            self._emit_status(f"Found paired phone: {self._phone.name}")

    def open_audio(self) -> None:
        """Call when CALL_ACTIVE arrives."""
        if self._phone is None:
            return
        self._routing_active = True
        self._save_current_devices()
        self._attempt_switch(attempt=1)

    def close_audio(self) -> None:
        """Call when CALL_ENDED arrives."""
        self._routing_active = False
        self._restore_devices()

    # -- internals --

    def _attempt_switch(self, attempt: int) -> None:
        if not self._routing_active or self._phone is None:
            return

        if self._try_switch_now():
            return

        if attempt >= _MAX_ATTEMPTS:
            logger.info("Gave up waiting for '%s' to appear as an audio device", self._phone.name)
            self._emit_status(
                "Phone did not appear as an audio device - "
                "check Android's Bluetooth 'Phone calls' toggle for this computer"
            )
            return

        logger.debug("Phone audio device not ready yet (attempt %s/%s) - retrying in 1s", attempt, _MAX_ATTEMPTS)
        QTimer.singleShot(_RETRY_INTERVAL_MS, lambda: self._attempt_switch(attempt + 1))

    def _try_switch_now(self) -> bool:
        assert self._phone is not None
        try:
            card = audio.find_card_for_mac(audio.list_cards(), self._phone.mac_address)
            if card is None:
                return False

            profile = audio.pick_handsfree_profile(card)
            if profile is not None and card.get("active_profile") != profile:
                audio.set_card_profile(card["name"], profile)

            sink = audio.find_endpoint_for_mac(audio.list_sinks(), self._phone.mac_address)
            source = audio.find_endpoint_for_mac(audio.list_sources(), self._phone.mac_address)
            if sink is None and source is None:
                return False

            if sink is not None:
                audio.set_default_sink(sink["name"])
            if source is not None:
                audio.set_default_source(source["name"])

            logger.info("Switched system audio to '%s'", self._phone.name)
            self._emit_status(f"Speaking through {self._phone.name}")
            return True
        except audio.AudioRouterError as error:
            logger.warning("Could not switch audio to phone: %s", error)
            return False

    def _save_current_devices(self) -> None:
        try:
            self._saved_sink = audio.get_default_sink()
            self._saved_source = audio.get_default_source()
        except audio.AudioRouterError as error:
            logger.warning("Could not read current default audio devices: %s", error)
            self._saved_sink = None
            self._saved_source = None

    def _restore_devices(self) -> None:
        if self._saved_sink is None and self._saved_source is None:
            return  # nothing was ever switched (e.g. call was rejected before going active)

        try:
            if self._saved_sink:
                audio.set_default_sink(self._saved_sink)
            if self._saved_source:
                audio.set_default_source(self._saved_source)
            logger.info("Restored original audio devices")
        except audio.AudioRouterError as error:
            logger.warning("Could not restore original audio devices: %s", error)
        finally:
            self._saved_sink = None
            self._saved_source = None

    def _emit_status(self, message: str) -> None:
        self.status_changed.emit(message)
