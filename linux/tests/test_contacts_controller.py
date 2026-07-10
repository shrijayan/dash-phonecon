"""Unit tests for ContactsController: CRUD message shapes, CONTACTS_RESULT
parsing, CONTACT_OP_RESULT error handling, and the pure filter_contacts()
search helper.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from dashphone.state.contacts_controller import Contact, ContactsController

_app = QApplication.instance() or QApplication([])


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def __call__(self, message: dict) -> None:
        self.sent.append(message)


class ContactsControllerOutgoingTests(unittest.TestCase):
    def test_refresh_sends_request_contacts(self) -> None:
        sender = FakeSender()
        controller = ContactsController(send_json=sender)
        controller.refresh()
        self.assertEqual(sender.sent, [{"type": "REQUEST_CONTACTS"}])

    def test_add_sends_name_and_number(self) -> None:
        sender = FakeSender()
        controller = ContactsController(send_json=sender)
        controller.add("Alice", "+15551234567")
        self.assertEqual(
            sender.sent, [{"type": "CONTACT_ADD", "name": "Alice", "number": "+15551234567"}]
        )

    def test_update_sends_contact_id(self) -> None:
        sender = FakeSender()
        controller = ContactsController(send_json=sender)
        controller.update("42", "Bob", "+15559876543")
        self.assertEqual(
            sender.sent,
            [{"type": "CONTACT_UPDATE", "contact_id": "42", "name": "Bob", "number": "+15559876543"}],
        )

    def test_delete_sends_contact_id(self) -> None:
        sender = FakeSender()
        controller = ContactsController(send_json=sender)
        controller.delete("42")
        self.assertEqual(sender.sent, [{"type": "CONTACT_DELETE", "contact_id": "42"}])


class ContactsControllerIncomingTests(unittest.TestCase):
    def test_contacts_result_populates_cache(self) -> None:
        controller = ContactsController(send_json=FakeSender())
        received = []
        controller.contacts_updated.connect(received.append)

        controller.handle_event(
            {
                "type": "CONTACTS_RESULT",
                "contacts": [
                    {"contact_id": "1", "name": "Alice", "number": "+1111"},
                    {"contact_id": "2", "name": "Bob", "number": "+2222"},
                ],
            }
        )

        self.assertEqual(len(controller.contacts), 2)
        self.assertEqual(controller.contacts[0], Contact("1", "Alice", "+1111"))
        self.assertEqual(len(received), 1)

    def test_contacts_result_with_empty_list(self) -> None:
        controller = ContactsController(send_json=FakeSender())
        controller.handle_event({"type": "CONTACTS_RESULT", "contacts": []})
        self.assertEqual(controller.contacts, [])

    def test_contact_op_result_failure_emits_operation_failed(self) -> None:
        controller = ContactsController(send_json=FakeSender())
        errors = []
        controller.operation_failed.connect(errors.append)

        controller.handle_event({"type": "CONTACT_OP_RESULT", "success": False, "error": "boom"})

        self.assertEqual(errors, ["boom"])

    def test_contact_op_result_success_does_not_emit_operation_failed(self) -> None:
        controller = ContactsController(send_json=FakeSender())
        errors = []
        controller.operation_failed.connect(errors.append)

        controller.handle_event({"type": "CONTACT_OP_RESULT", "success": True})

        self.assertEqual(errors, [])

    def test_unrelated_message_types_are_ignored(self) -> None:
        controller = ContactsController(send_json=FakeSender())
        controller.handle_event({"type": "CALL_RINGING", "number": "+1", "name": ""})
        self.assertEqual(controller.contacts, [])


class FilterContactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contacts = [
            Contact("1", "Alice Smith", "+15551234567"),
            Contact("2", "Bob Jones", "+15559876543"),
            Contact("3", "", "+15550001111"),
        ]

    def test_empty_query_returns_all(self) -> None:
        self.assertEqual(ContactsController.filter_contacts(self.contacts, ""), self.contacts)

    def test_matches_name_case_insensitively(self) -> None:
        result = ContactsController.filter_contacts(self.contacts, "alice")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].contact_id, "1")

    def test_matches_number_substring(self) -> None:
        result = ContactsController.filter_contacts(self.contacts, "9876")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].contact_id, "2")

    def test_no_match_returns_empty(self) -> None:
        self.assertEqual(ContactsController.filter_contacts(self.contacts, "zzz"), [])

    def test_contact_with_no_name_still_searchable_by_number(self) -> None:
        result = ContactsController.filter_contacts(self.contacts, "0001111")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].contact_id, "3")


if __name__ == "__main__":
    unittest.main()
