"""Contacts window: search, list, add/edit/delete, and dial-by-contact.

Deliberately a plain QWidget (not a dialog) so it can stay open alongside
the tray while the user works through their contact list, mirroring how
CallPopupWindow is a standalone top-level window rather than modal.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dashphone.state.contacts_controller import Contact, ContactsController


class ContactsWindow(QWidget):
    def __init__(
        self,
        controller: ContactsController,
        on_dial: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Contacts")
        self.resize(420, 520)

        self._controller = controller
        self._on_dial = on_dial
        self._contacts: list[Contact] = []

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search name or number\u2026")
        self._search_box.textChanged.connect(self._refresh_list)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.itemDoubleClicked.connect(lambda _item: self._dial_selected())

        self._dial_button = QPushButton("Dial")
        self._dial_button.clicked.connect(self._dial_selected)

        self._add_button = QPushButton("Add\u2026")
        self._add_button.clicked.connect(self._prompt_add)

        self._edit_button = QPushButton("Edit\u2026")
        self._edit_button.clicked.connect(self._prompt_edit_selected)

        self._delete_button = QPushButton("Delete")
        self._delete_button.clicked.connect(self._delete_selected)

        self._refresh_button = QPushButton("Refresh")
        self._refresh_button.clicked.connect(self._controller.refresh)

        button_row = QHBoxLayout()
        for button in (self._dial_button, self._add_button, self._edit_button, self._delete_button, self._refresh_button):
            button_row.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search_box)
        layout.addWidget(self._list)
        layout.addLayout(button_row)

        self._controller.contacts_updated.connect(self._on_contacts_updated)
        self._controller.operation_failed.connect(self._on_operation_failed)

    def show_and_refresh(self) -> None:
        """Open the window and immediately request the latest contact list
        from the phone, so it never shows a stale cache from a previous
        session."""
        self._controller.refresh()
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_contacts_updated(self, contacts: list[Contact]) -> None:
        self._contacts = contacts
        self._refresh_list()

    def _on_operation_failed(self, error: str) -> None:
        QMessageBox.warning(self, "Contacts", f"That didn't work: {error}")

    def _refresh_list(self) -> None:
        query = self._search_box.text()
        filtered = ContactsController.filter_contacts(self._contacts, query)
        self._list.clear()
        for contact in filtered:
            label = f"{contact.name}  \u2014  {contact.number}" if contact.name else contact.number
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, contact)
            self._list.addItem(item)

    def _selected_contact(self) -> Contact | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _dial_selected(self) -> None:
        contact = self._selected_contact()
        if contact is not None and contact.number:
            self._on_dial(contact.number)

    def _prompt_add(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Contact", "Name:")
        if not ok or not name.strip():
            return
        number, ok = QInputDialog.getText(self, "Add Contact", "Phone number:")
        if not ok or not number.strip():
            return
        self._controller.add(name.strip(), number.strip())

    def _prompt_edit_selected(self) -> None:
        contact = self._selected_contact()
        if contact is None:
            return
        name, ok = QInputDialog.getText(self, "Edit Contact", "Name:", text=contact.name)
        if not ok:
            return
        number, ok = QInputDialog.getText(self, "Edit Contact", "Phone number:", text=contact.number)
        if not ok:
            return
        self._controller.update(contact.contact_id, name.strip(), number.strip())

    def _delete_selected(self) -> None:
        contact = self._selected_contact()
        if contact is None:
            return
        confirm = QMessageBox.question(
            self,
            "Delete Contact",
            f"Delete {contact.name or contact.number}?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._controller.delete(contact.contact_id)
