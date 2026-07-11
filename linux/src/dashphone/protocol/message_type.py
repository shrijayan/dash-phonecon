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
    DIAL = "DIAL"  # this app -> phone: place an outgoing call to FIELD_NUMBER via the phone's TelecomManager
    MUTE = "MUTE"  # this app -> phone: FIELD_MUTED true/false - mute/unmute the phone's mic during an active call

    # Contacts CRUD - bidirectional, always initiated by this app, phone replies
    REQUEST_CONTACTS = "REQUEST_CONTACTS"  # this app -> phone: "send me your full contact list"
    CONTACTS_RESULT = "CONTACTS_RESULT"  # phone -> this app: FIELD_CONTACTS = [{id, name, number}, ...]
    CONTACT_ADD = "CONTACT_ADD"  # this app -> phone: create a contact from FIELD_NAME/FIELD_NUMBER
    CONTACT_UPDATE = "CONTACT_UPDATE"  # this app -> phone: FIELD_CONTACT_ID + new FIELD_NAME/FIELD_NUMBER
    CONTACT_DELETE = "CONTACT_DELETE"  # this app -> phone: delete FIELD_CONTACT_ID
    CONTACT_OP_RESULT = "CONTACT_OP_RESULT"  # phone -> this app: FIELD_SUCCESS + optional FIELD_ERROR

    # Call log - this app -> phone request, phone -> this app reply
    REQUEST_CALL_LOG = "REQUEST_CALL_LOG"  # this app -> phone: "send me recent call history"
    CALL_LOG_RESULT = "CALL_LOG_RESULT"  # phone -> this app: FIELD_CALLS = [{number, name, type, time, duration}, ...]


# JSON field keys (kept as plain constants, matching FIELD_* in MessageType.kt)
FIELD_TYPE = "type"
FIELD_NUMBER = "number"
FIELD_NAME = "name"
FIELD_CONTACTS = "contacts"
FIELD_CONTACT_ID = "contact_id"
FIELD_SUCCESS = "success"
FIELD_ERROR = "error"
FIELD_CALLS = "calls"
FIELD_CALL_TYPE = "call_type"
FIELD_TIMESTAMP = "timestamp"
FIELD_DURATION = "duration"
FIELD_MUTED = "muted"


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
