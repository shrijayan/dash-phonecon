"""Turns incoming CALL_LOG_RESULT messages from the phone into a local
call-history cache. Read-only mirror of ContactsController's request/reply
pattern - no CRUD, the phone is always the source of truth for its own
call log.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, Signal

from dashphone.protocol import FIELD_CALL_TYPE, FIELD_CALLS, FIELD_DURATION, FIELD_NAME, FIELD_NUMBER, FIELD_TIMESTAMP, MessageType, parse_message_type

# Mirrors android.provider.CallLog.Calls type constants.
CALL_TYPE_INCOMING = 1
CALL_TYPE_OUTGOING = 2
CALL_TYPE_MISSED = 3

_CALL_TYPE_LABELS = {
    CALL_TYPE_INCOMING: "Incoming",
    CALL_TYPE_OUTGOING: "Outgoing",
    CALL_TYPE_MISSED: "Missed",
}


@dataclass(frozen=True)
class CallLogEntry:
    number: str
    name: str
    call_type: int
    timestamp_ms: int
    duration_seconds: int

    @property
    def call_type_label(self) -> str:
        return _CALL_TYPE_LABELS.get(self.call_type, "Unknown")

    @property
    def display_name(self) -> str:
        return self.name if self.name else self.number


class CallLogController(QObject):
    call_log_updated = Signal(list)  # list[CallLogEntry]

    def __init__(self, send_json: Callable[[dict], None]) -> None:
        super().__init__()
        self._send_json = send_json
        self.entries: list[CallLogEntry] = []

    def refresh(self) -> None:
        self._send_json({"type": MessageType.REQUEST_CALL_LOG.value})

    def handle_event(self, message: dict) -> None:
        message_type = parse_message_type(message)
        if message_type != MessageType.CALL_LOG_RESULT:
            return
        entries = [
            CallLogEntry(
                number=str(raw.get(FIELD_NUMBER, "")),
                name=str(raw.get(FIELD_NAME, "")),
                call_type=int(raw.get(FIELD_CALL_TYPE, 0)),
                timestamp_ms=int(raw.get(FIELD_TIMESTAMP, 0)),
                duration_seconds=int(raw.get(FIELD_DURATION, 0)),
            )
            for raw in message.get(FIELD_CALLS, [])
        ]
        self.entries = entries
        self.call_log_updated.emit(entries)
