"""Unit tests for media_ducker.py's pure matching logic (is_mpris_service)
and the MediaDucker pause/resume bookkeeping, using a fake D-Bus session bus
so no real media player is needed to run these.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dashphone import media_ducker
from dashphone.media_ducker import MediaDucker


class IsMprisServiceTests(unittest.TestCase):
    def test_recognizes_mpris_service_names(self) -> None:
        self.assertTrue(media_ducker.is_mpris_service("org.mpris.MediaPlayer2.spotify"))
        self.assertTrue(media_ducker.is_mpris_service("org.mpris.MediaPlayer2.vlc"))

    def test_rejects_unrelated_service_names(self) -> None:
        self.assertFalse(media_ducker.is_mpris_service("org.freedesktop.DBus"))
        self.assertFalse(media_ducker.is_mpris_service("org.bluez"))


class FakePlayer:
    """Stands in for one MPRIS2 player's D-Bus object + Properties/Player
    interfaces, tracking PlaybackStatus and Pause()/Play() calls."""

    def __init__(self, playback_status: str) -> None:
        self.playback_status = playback_status
        self.paused_calls = 0
        self.played_calls = 0

    def pause(self) -> None:
        self.paused_calls += 1
        self.playback_status = "Paused"

    def play(self) -> None:
        self.played_calls += 1
        self.playback_status = "Playing"


def _fake_bus(players: dict[str, FakePlayer], service_names: list[str] | None = None):
    """A MagicMock standing in for dbus.SessionBus(), wired so
    list_names()/get_object()/Interface(...).Get/Pause/Play all route to the
    given FakePlayer objects, keyed by service name."""
    bus = MagicMock()
    bus.list_names.return_value = list(service_names if service_names is not None else players.keys())

    def get_object(service_name: str, _path: str):
        obj = MagicMock()
        obj._service_name = service_name
        return obj

    bus.get_object.side_effect = get_object
    return bus


def _fake_interface_factory(players: dict[str, FakePlayer]):
    """Builds a replacement for dbus.Interface(obj, interface_name) that
    dispatches Get/Pause/Play to the right FakePlayer based on the mock
    object's _service_name (set by _fake_bus's get_object)."""

    def make_interface(obj, interface_name: str):
        player = players[obj._service_name]
        iface = MagicMock()
        if interface_name == media_ducker._PROPERTIES_INTERFACE:
            iface.Get.side_effect = lambda _iface, _prop: player.playback_status
        else:
            iface.Pause.side_effect = player.pause
            iface.Play.side_effect = player.play
        return iface

    return make_interface


class MediaDuckerTests(unittest.TestCase):
    def test_pauses_only_currently_playing_players(self) -> None:
        players = {
            "org.mpris.MediaPlayer2.spotify": FakePlayer("Playing"),
            "org.mpris.MediaPlayer2.vlc": FakePlayer("Paused"),
        }
        bus = _fake_bus(players)

        with patch("dashphone.media_ducker.dbus.SessionBus", return_value=bus), patch(
            "dashphone.media_ducker.dbus.Interface", side_effect=_fake_interface_factory(players)
        ):
            ducker = MediaDucker()
            ducker.duck_others()

        self.assertEqual(players["org.mpris.MediaPlayer2.spotify"].paused_calls, 1)
        self.assertEqual(players["org.mpris.MediaPlayer2.vlc"].paused_calls, 0)

    def test_restore_only_resumes_players_it_paused(self) -> None:
        players = {
            "org.mpris.MediaPlayer2.spotify": FakePlayer("Playing"),
            "org.mpris.MediaPlayer2.vlc": FakePlayer("Paused"),
        }
        bus = _fake_bus(players)

        with patch("dashphone.media_ducker.dbus.SessionBus", return_value=bus), patch(
            "dashphone.media_ducker.dbus.Interface", side_effect=_fake_interface_factory(players)
        ):
            ducker = MediaDucker()
            ducker.duck_others()
            ducker.restore_others()

        self.assertEqual(players["org.mpris.MediaPlayer2.spotify"].played_calls, 1)
        self.assertEqual(players["org.mpris.MediaPlayer2.vlc"].played_calls, 0)

    def test_restore_is_a_no_op_when_nothing_was_paused(self) -> None:
        players = {"org.mpris.MediaPlayer2.vlc": FakePlayer("Paused")}
        bus = _fake_bus(players)

        with patch("dashphone.media_ducker.dbus.SessionBus", return_value=bus), patch(
            "dashphone.media_ducker.dbus.Interface", side_effect=_fake_interface_factory(players)
        ):
            ducker = MediaDucker()
            ducker.duck_others()
            ducker.restore_others()

        self.assertEqual(players["org.mpris.MediaPlayer2.vlc"].played_calls, 0)

    def test_ignores_non_mpris_services_on_the_bus(self) -> None:
        players = {"org.mpris.MediaPlayer2.spotify": FakePlayer("Playing")}
        bus = _fake_bus(players, service_names=["org.mpris.MediaPlayer2.spotify", "org.bluez", "org.freedesktop.DBus"])

        with patch("dashphone.media_ducker.dbus.SessionBus", return_value=bus), patch(
            "dashphone.media_ducker.dbus.Interface", side_effect=_fake_interface_factory(players)
        ):
            ducker = MediaDucker()
            ducker.duck_others()

        self.assertEqual(players["org.mpris.MediaPlayer2.spotify"].paused_calls, 1)

    def test_duck_others_disabled_gracefully_when_session_bus_unreachable(self) -> None:
        with patch(
            "dashphone.media_ducker.dbus.SessionBus",
            side_effect=media_ducker.DBusException("no session bus"),
        ):
            ducker = MediaDucker()
            ducker.duck_others()  # must not raise
            ducker.restore_others()  # must not raise either


    def test_duplicate_call_active_does_not_forget_already_paused_players(self) -> None:
        """Regression test: confirmed against a real Android device that
        CALL_ACTIVE can be delivered twice in a row for one call. Before this
        was fixed, the second duck_others() call re-scanned players, found
        the already-paused one no longer "Playing", and silently dropped it
        from the resume list - so restore_others() never resumed it."""
        players = {"org.mpris.MediaPlayer2.spotify": FakePlayer("Playing")}
        bus = _fake_bus(players)

        with patch("dashphone.media_ducker.dbus.SessionBus", return_value=bus), patch(
            "dashphone.media_ducker.dbus.Interface", side_effect=_fake_interface_factory(players)
        ):
            ducker = MediaDucker()
            ducker.duck_others()
            ducker.duck_others()  # duplicate CALL_ACTIVE
            ducker.restore_others()

        self.assertEqual(players["org.mpris.MediaPlayer2.spotify"].paused_calls, 1)
        self.assertEqual(players["org.mpris.MediaPlayer2.spotify"].played_calls, 1)

    def test_duplicate_call_ended_is_a_no_op(self) -> None:
        players = {"org.mpris.MediaPlayer2.spotify": FakePlayer("Playing")}
        bus = _fake_bus(players)

        with patch("dashphone.media_ducker.dbus.SessionBus", return_value=bus), patch(
            "dashphone.media_ducker.dbus.Interface", side_effect=_fake_interface_factory(players)
        ):
            ducker = MediaDucker()
            ducker.duck_others()
            ducker.restore_others()
            ducker.restore_others()  # duplicate CALL_ENDED

        self.assertEqual(players["org.mpris.MediaPlayer2.spotify"].played_calls, 1)


if __name__ == "__main__":
    unittest.main()
