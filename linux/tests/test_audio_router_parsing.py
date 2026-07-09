"""Unit tests for the pure matching/parsing helpers in audio_router.py,
using recorded-shape `pactl -f json` output as fixtures. No real Bluetooth
phone or `pactl` binary is needed to run these.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dashphone.bluetooth import audio_router

PHONE_MAC = "AA:BB:CC:DD:EE:FF"
PHONE_TOKEN = "AA_BB_CC_DD_EE_FF"

SAMPLE_CARDS = [
    {
        "index": 53,
        "name": "alsa_card.pci-0000_00_1f.3-platform-skl_hda_dsp_generic",
        "properties": {"device.description": "Built-in Audio"},
        "active_profile": "HiFi",
        "profiles": {"off": {"description": "Off", "available": True}},
    },
    {
        "index": 99,
        "name": f"bluez_card.{PHONE_TOKEN}",
        "properties": {"device.description": "Galaxy A31"},
        "active_profile": "off",
        "profiles": {
            "off": {"description": "Off", "available": True},
            "a2dp-sink": {"description": "High Fidelity Playback (A2DP Sink)", "available": False},
            "headset-head-unit": {"description": "Headset Head Unit (HSP/HFP)", "available": True},
        },
    },
]

SAMPLE_SINKS = [
    {"index": 60, "name": "alsa_output.built-in.speaker", "description": "Built-in Speaker"},
    {"index": 200, "name": f"bluez_output.{PHONE_TOKEN}.1", "description": "Galaxy A31"},
]

SAMPLE_SOURCES = [
    {"index": 61, "name": "alsa_input.built-in.mic", "description": "Built-in Microphone"},
    {"index": 201, "name": f"bluez_input.{PHONE_TOKEN}.1", "description": "Galaxy A31"},
]


class MacToPactlTokenTests(unittest.TestCase):
    def test_upper_cases_and_replaces_colons_with_underscores(self) -> None:
        self.assertEqual(audio_router.mac_to_pactl_token("aa:bb:cc:dd:ee:ff"), PHONE_TOKEN)


class FindCardForMacTests(unittest.TestCase):
    def test_finds_the_bluez_card_by_mac(self) -> None:
        card = audio_router.find_card_for_mac(SAMPLE_CARDS, PHONE_MAC)
        self.assertIsNotNone(card)
        self.assertEqual(card["index"], 99)

    def test_returns_none_when_phone_not_paired(self) -> None:
        card = audio_router.find_card_for_mac(SAMPLE_CARDS, "11:22:33:44:55:66")
        self.assertIsNone(card)


class PickHandsfreeProfileTests(unittest.TestCase):
    def test_picks_the_available_head_unit_profile_over_a2dp(self) -> None:
        card = audio_router.find_card_for_mac(SAMPLE_CARDS, PHONE_MAC)
        profile = audio_router.pick_handsfree_profile(card)
        self.assertEqual(profile, "headset-head-unit")

    def test_returns_none_when_card_has_no_handsfree_profile(self) -> None:
        card = {"profiles": {"off": {"description": "Off", "available": True}}}
        self.assertIsNone(audio_router.pick_handsfree_profile(card))


class FindEndpointForMacTests(unittest.TestCase):
    def test_finds_sink_by_mac(self) -> None:
        sink = audio_router.find_endpoint_for_mac(SAMPLE_SINKS, PHONE_MAC)
        self.assertIsNotNone(sink)
        self.assertEqual(sink["index"], 200)

    def test_finds_source_by_mac(self) -> None:
        source = audio_router.find_endpoint_for_mac(SAMPLE_SOURCES, PHONE_MAC)
        self.assertIsNotNone(source)
        self.assertEqual(source["index"], 201)

    def test_returns_none_when_no_endpoint_matches(self) -> None:
        self.assertIsNone(audio_router.find_endpoint_for_mac(SAMPLE_SINKS, "11:22:33:44:55:66"))


if __name__ == "__main__":
    unittest.main()
