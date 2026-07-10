"""Turns incoming CONTACTS_RESULT/CONTACT_OP_RESULT messages from the phone
into a local contacts cache, and user CRUD actions into outgoing protocol
messages - the same request/response split CallStateController uses for
call state, kept in its own file since contacts are a separate concern.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, Signal

from dashphone.protocol import (
    FIELD_CONTACT_ID,
    FIELD_CONTACTS,
    FIELD_ERROR,
    FIELD_NAME,
    FIELD_NUMBER,
    FIELD_SUCCESS,
    MessageType,
    parse_message_type,
)

logger = logging.getLogger(__name__)

CommandSender = Callable[[dict], None]


@dataclass(frozen=True)
class Contact:
    contact_id: str
    name: str
    number: str


class ContactsController(QObject):
    contacts_updated = Signal(list)  # emits list[Contact], full replace of the local cache
    operation_failed = Signal(str)  # emits an error message when an add/update/delete fails

    def __init__(self, send_json: CommandSender, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._send_json = send_json
        self._contacts: list[Contact] = []

    @property
    def contacts(self) -> list[Contact]:
        return list(self._contacts)

    def handle_event(self, message: dict) -> None:
        """Called for every JSON message from the phone - ignores anything
        that isn't a contacts-related reply, same pattern as
        CallStateController.handle_event."""
        message_type = parse_message_type(message)

        if message_type is MessageType.CONTACTS_RESULT:
            raw_contacts = message.get(FIELD_CONTACTS, []) or []
            seen: set[tuple[str, str]] = set()
            contacts: list[Contact] = []
            for item in raw_contacts:
                if not isinstance(item, dict):
                    continue
                contact = Contact(
                    contact_id=str(item.get(FIELD_CONTACT_ID, "")),
                    name=str(item.get(FIELD_NAME, "")),
                    number=str(item.get(FIELD_NUMBER, "")),
                )
                # Defense-in-depth: the phone already dedupes, but some
                # sync sources send the same contact with a masked number
                # variant too (e.g. "+91 6383 589 862" vs "+916****9862")
                # - exact-string matching wouldn't catch that, so key on
                # the last 4 digits (masking always preserves the suffix)
                # instead of the full number.
                digits = "".join(ch for ch in contact.number if ch.isdigit())
                dedupe_key = (contact.name, digits[-4:] if digits else contact.number)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                contacts.append(contact)
            self._contacts = contacts
            logger.info("Received %d contacts from phone", len(self._contacts))
            self.contacts_updated.emit(self.contacts)

        elif message_type is MessageType.CONTACT_OP_RESULT:
            success = bool(message.get(FIELD_SUCCESS, False))
            if not success:
                error = str(message.get(FIELD_ERROR, "Unknown error"))
                logger.warning("Contact operation failed: %s", error)
                self.operation_failed.emit(error)

    def refresh(self) -> None:
        """Ask the phone to send its full contact list."""
        self._send_json({"type": MessageType.REQUEST_CONTACTS.value})

    def add(self, name: str, number: str) -> None:
        self._send_json({"type": MessageType.CONTACT_ADD.value, FIELD_NAME: name, FIELD_NUMBER: number})

    def update(self, contact_id: str, name: str, number: str) -> None:
        self._send_json(
            {
                "type": MessageType.CONTACT_UPDATE.value,
                FIELD_CONTACT_ID: contact_id,
                FIELD_NAME: name,
                FIELD_NUMBER: number,
            }
        )

    def delete(self, contact_id: str) -> None:
        self._send_json({"type": MessageType.CONTACT_DELETE.value, FIELD_CONTACT_ID: contact_id})

    @staticmethod
    def filter_contacts(contacts: list[Contact], query: str) -> list[Contact]:
        """Case-insensitive substring match against name or number - pure
        function so search behavior is testable without any Qt widgets."""
        query = query.strip().lower()
        if not query:
            return list(contacts)
        return [c for c in contacts if query in c.name.lower() or query in c.number.lower()]
