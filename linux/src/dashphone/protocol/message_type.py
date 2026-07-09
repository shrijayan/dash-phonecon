"""The wire protocol shared by the Android phone and this app.

This file must stay in sync with:
  - android/app/src/main/java/com/dash/phonecon/MessageType.kt
  - macos/DashPhone/Models/MessageType.swift

Every message is a single-line JSON object with at least a "type" field,
sent over the WebSocket connection on port 8765. Keep this file as the
single source of truth for the string values used on the Ubuntu side.
"""

from __future__ import annotations

from enum import Enum


class MessageType(str, Enum):
    """Inheriting from str lets us drop straight into JSON (e.g. json.dumps({"type": MessageType.ANSWER}))."""

    # Phone -> this app
    CALL_RINGING = "CALL_RINGING"
    CALL_ACTIVE = "CALL_ACTIVE"
    CALL_ENDED = "CALL_ENDED"
    PING = "PING"

    # This app -> phone
    ANSWER = "ANSWER"
    REJECT = "REJECT"
    HANGUP = "HANGUP"
    PONG = "PONG"


# JSON field keys (kept as plain constants, matching FIELD_* in MessageType.kt)
FIELD_TYPE = "type"
FIELD_NUMBER = "number"
FIELD_NAME = "name"


def parse_message_type(raw: dict) -> MessageType | None:
    """Return the MessageType for a decoded JSON message, or None if unknown/missing.

    Returning None (instead of raising) lets callers ignore messages from a
    future protocol version without crashing - the same "default: break"
    behaviour used on the Mac and Android sides.
    """
    raw_type = raw.get(FIELD_TYPE)
    try:
        return MessageType(raw_type)
    except ValueError:
        return None
