"""Best-effort media ducking: pauses other media players (Spotify, Firefox,
VLC, etc.) when a call becomes active, and resumes only the ones this app
paused once the call ends.

Uses the MPRIS2 D-Bus spec (https://specifications.freedesktop.org/mpris-spec/)
that most Linux media players implement, so there is no player-specific
integration to write or maintain. Deliberately best-effort, same philosophy
as bluetooth/hfp_manager.py: if the session bus is unavailable or a player
does not respond, ducking simply does not happen and the call itself is
unaffected.

Independent of Bluetooth call-audio routing - this works over the WiFi
call-control link alone, so it still ducks media even when no phone is
paired for Bluetooth audio.
"""

from __future__ import annotations

import logging

import dbus
from dbus.exceptions import DBusException

logger = logging.getLogger(__name__)

_MPRIS_PREFIX = "org.mpris.MediaPlayer2."
_MPRIS_OBJECT_PATH = "/org/mpris/MediaPlayer2"
_MPRIS_PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
_PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
_PLAYING_STATUS = "Playing"


def is_mpris_service(service_name: str) -> bool:
    """Whether a D-Bus service name identifies an MPRIS2 media player."""
    return service_name.startswith(_MPRIS_PREFIX)


def list_player_services(bus: dbus.SessionBus) -> list[str]:
    """All MPRIS2 player service names currently on the session bus."""
    names = bus.list_names() or []
    return [name for name in names if is_mpris_service(str(name))]


def get_playback_status(bus: dbus.SessionBus, service_name: str) -> str | None:
    """'Playing', 'Paused', or 'Stopped' - or None if the player did not answer."""
    try:
        obj = bus.get_object(service_name, _MPRIS_OBJECT_PATH)
        props = dbus.Interface(obj, _PROPERTIES_INTERFACE)
        return str(props.Get(_MPRIS_PLAYER_INTERFACE, "PlaybackStatus"))
    except DBusException as error:
        logger.debug("Could not read PlaybackStatus from %s: %s", service_name, error)
        return None


def pause_player(bus: dbus.SessionBus, service_name: str) -> bool:
    try:
        obj = bus.get_object(service_name, _MPRIS_OBJECT_PATH)
        dbus.Interface(obj, _MPRIS_PLAYER_INTERFACE).Pause()
        return True
    except DBusException as error:
        logger.debug("Could not pause %s: %s", service_name, error)
        return False


def play_player(bus: dbus.SessionBus, service_name: str) -> bool:
    try:
        obj = bus.get_object(service_name, _MPRIS_OBJECT_PATH)
        dbus.Interface(obj, _MPRIS_PLAYER_INTERFACE).Play()
        return True
    except DBusException as error:
        logger.debug("Could not resume %s: %s", service_name, error)
        return False


class MediaDucker:
    """Pauses currently-playing MPRIS players on `duck_others()`, resumes only
    those same players on `restore_others()` - so a player that was already
    paused before the call (or one opened during the call) is left alone.

    `duck_others()`/`restore_others()` are each idempotent: phone-side call
    state can (and in practice does - confirmed against a real Android
    device) deliver the same CALL_ACTIVE or CALL_ENDED event more than once
    in a row. Without guarding for that, a repeated CALL_ACTIVE would wipe
    the bookkeeping of what we already paused (finding it non-"Playing" the
    second time round and forgetting about it), so the matching CALL_ENDED
    would never resume it.
    """

    def __init__(self) -> None:
        self._paused_services: list[str] = []
        self._ducking = False

    def duck_others(self) -> None:
        """Call when CALL_ACTIVE arrives. Safe to call again while already
        ducking (e.g. a duplicate CALL_ACTIVE) - it will not re-scan and
        forget players it already paused."""
        if self._ducking:
            return

        try:
            bus = dbus.SessionBus()
        except DBusException as error:
            logger.info("Media ducking disabled (session bus not reachable): %s", error)
            return

        self._ducking = True
        self._paused_services = []
        for service_name in list_player_services(bus):
            if get_playback_status(bus, service_name) != _PLAYING_STATUS:
                continue
            if pause_player(bus, service_name):
                self._paused_services.append(service_name)
                logger.info("Paused media player for call: %s", service_name)

    def restore_others(self) -> None:
        """Call when CALL_ENDED arrives. Safe to call again once already
        restored (e.g. a duplicate CALL_ENDED) - it is a no-op the second
        time round."""
        if not self._ducking:
            return
        self._ducking = False

        if not self._paused_services:
            return

        try:
            bus = dbus.SessionBus()
        except DBusException as error:
            logger.info("Could not resume paused media players: %s", error)
            self._paused_services = []
            return

        for service_name in self._paused_services:
            if play_player(bus, service_name):
                logger.info("Resumed media player after call: %s", service_name)
        self._paused_services = []
