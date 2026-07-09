"""Wraps `pactl` (PipeWire's PulseAudio-compatible CLI) so we can find the
phone's Bluetooth audio device and switch the system's default
microphone/speaker to it, then switch back when the call ends.

The matching/parsing functions here are pure (take already-decoded JSON and
return a result) so they can be unit tested with recorded `pactl` output,
without needing a real paired phone attached to run the tests.
"""

from __future__ import annotations

import json
import logging
import subprocess

logger = logging.getLogger(__name__)

_PACTL_TIMEOUT_SECONDS = 3

# Substrings that identify a "this computer is the Hands-Free head unit for
# a phone call" profile. Matched by substring (not one fixed name) because
# the exact profile identifier has changed across PipeWire/PulseAudio
# releases - see linux/README.md for the versions this was verified against.
_HANDSFREE_PROFILE_HINTS = ("head_unit", "head-unit", "handsfree", "hands-free", "hfp")


class AudioRouterError(RuntimeError):
    """Raised when `pactl` is missing, times out, or a command fails."""


def mac_to_pactl_token(mac_address: str) -> str:
    """'AA:BB:CC:DD:EE:FF' -> 'AA_BB_CC_DD_EE_FF', how PipeWire/BlueZ name
    Bluetooth cards/sinks/sources."""
    return mac_address.upper().replace(":", "_")


def find_card_for_mac(cards: list[dict], mac_address: str) -> dict | None:
    token = mac_to_pactl_token(mac_address)
    return next((card for card in cards if token in card.get("name", "")), None)


def pick_handsfree_profile(card: dict) -> str | None:
    """Pick the profile that makes this computer the phone's Hands-Free
    head unit, preferring one that is actually available right now."""
    profiles: dict = card.get("profiles", {})
    matches = [
        key
        for key, details in profiles.items()
        if any(hint in f"{key} {details.get('description', '')}".lower() for hint in _HANDSFREE_PROFILE_HINTS)
    ]
    available = [key for key in matches if profiles[key].get("available", True)]
    return (available or matches or [None])[0]


def find_endpoint_for_mac(endpoints: list[dict], mac_address: str) -> dict | None:
    """Find a sink or source (from list_sinks()/list_sources()) that belongs
    to the phone's Bluetooth MAC address."""
    token = mac_to_pactl_token(mac_address)
    return next((endpoint for endpoint in endpoints if token in endpoint.get("name", "")), None)


def _run_pactl(*args: str) -> str:
    try:
        result = subprocess.run(
            ["pactl", *args],
            capture_output=True,
            text=True,
            timeout=_PACTL_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as error:
        raise AudioRouterError("pactl is not installed (package: pulseaudio-utils)") from error
    except subprocess.TimeoutExpired as error:
        raise AudioRouterError(f"pactl {' '.join(args)} timed out") from error

    if result.returncode != 0:
        raise AudioRouterError(f"pactl {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _list_json(entity: str) -> list[dict]:
    raw = _run_pactl("-f", "json", "list", entity)
    try:
        return json.loads(raw)
    except ValueError as error:
        raise AudioRouterError(f"Could not parse pactl output for '{entity}'") from error


def list_cards() -> list[dict]:
    return _list_json("cards")


def list_sinks() -> list[dict]:
    return _list_json("sinks")


def list_sources() -> list[dict]:
    return _list_json("sources")


def get_default_sink() -> str:
    return _run_pactl("get-default-sink").strip()


def get_default_source() -> str:
    return _run_pactl("get-default-source").strip()


def set_default_sink(name: str) -> None:
    _run_pactl("set-default-sink", name)


def set_default_source(name: str) -> None:
    _run_pactl("set-default-source", name)


def set_card_profile(card_name: str, profile: str) -> None:
    _run_pactl("set-card-profile", card_name, profile)
