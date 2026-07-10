"""Turns incoming protocol messages into CallState changes, and outgoing
CallState/user actions into protocol messages.

This is the only class that understands what CALL_RINGING/CALL_ACTIVE/...
*mean*. The network layer below it only knows how to move bytes; the UI
layer above it only knows how to draw a CallState. That separation is what
lets each piece be tested and changed independently.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

from PySide6.QtCore import QObject, Signal

from dashphone.protocol import FIELD_NAME, FIELD_NUMBER, MessageType, parse_message_type
from dashphone.state.call_state import CallPhase, CallState

logger = logging.getLogger(__name__)

# A function that takes a JSON-serialisable dict and sends it to the phone.
# Using a plain Callable (instead of importing CallServer here) keeps this
# module decoupled from the transport - it can be unit tested with a fake.
CommandSender = Callable[[dict], None]


class CallStateController(QObject):
    state_changed = Signal(object)  # emits a CallState
    call_missed = Signal(str, str)  # emits (name, number) for a missed call

    def __init__(self, send_json: CommandSender, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._send_json = send_json
        self._state = CallState.idle()

    @property
    def state(self) -> CallState:
        return self._state

    def handle_event(self, message: dict) -> None:
        """Called whenever a JSON message arrives from the phone."""
        message_type = parse_message_type(message)

        if message_type is MessageType.CALL_RINGING:
            number = message.get(FIELD_NUMBER, "") or ""
            name = message.get(FIELD_NAME, "") or ""
            logger.info("Call ringing: %s (%s)", name or "Unknown", number)
            self._set_state(CallState.ringing(number=number, name=name))

        elif message_type is MessageType.CALL_ACTIVE:
            logger.info("Call active")
            self._set_state(CallState.active(start_time=datetime.now()))

        elif message_type is MessageType.CALL_ENDED:
            logger.info("Call ended")
            # self._state still holds the *previous* phase here - CALL_ENDED
            # while still RINGING (no CALL_ACTIVE in between) means the call
            # rang out or was declined on the phone itself, without this
            # app's user ever answering it. Distinguish that from a normal
            # "call was active, then hung up" ending before overwriting it.
            if self._state.phase is CallPhase.RINGING:
                self.call_missed.emit(self._state.name, self._state.number)
            self._set_state(CallState.idle())

        elif message_type is MessageType.PING:
            self.send_command(MessageType.PONG)

        else:
            # Every controller receives every incoming message (see CallServer
            # broadcasting all messages to all handlers) and ignores the ones
            # it doesn't own - e.g. CONTACTS_RESULT/CALL_LOG_RESULT are handled
            # by ContactsController/CallLogController, not here. debug (not
            # warning) since "unknown to this controller" is expected traffic,
            # not an actual problem.
            logger.debug("Ignoring message not handled by CallStateController: %r", message_type)

    def send_command(self, message_type: MessageType) -> None:
        """Send a bare {"type": "..."} command to the phone (ANSWER/REJECT/HANGUP/PONG)."""
        self._send_json({"type": message_type.value})

    def dial(self, number: str) -> None:
        """Ask the phone to place an outgoing call to ``number`` (dial-from-desktop).

        Kept separate from send_command since DIAL carries a payload field
        (FIELD_NUMBER) rather than being a bare {"type": ...} message.
        """
        self._send_json({"type": MessageType.DIAL.value, FIELD_NUMBER: number})

    def _set_state(self, new_state: CallState) -> None:
        self._state = new_state
        self.state_changed.emit(new_state)
