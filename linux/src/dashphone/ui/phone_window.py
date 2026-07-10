"""The main Phone window: a single tabbed surface (Dialer / Contacts /
Call Log) replacing the separate ad-hoc dialogs. Styled to match the
CallPopupWindow's dark card aesthetic instead of looking like a raw,
unstyled Qt form - this is the app's actual "phone & contacts" UI, not
a debug utility.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from dashphone.state.call_log_controller import CallLogController, CallLogEntry
from dashphone.state.contacts_controller import Contact, ContactsController

_DARK_STYLE = """
QWidget { background-color: #1e1e21; color: #f0f0f0; font-size: 13px; }
QTabWidget::pane { border: 1px solid #3a3a3d; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background: #2b2b2e; color: #b0b0b0; padding: 8px 18px;
    border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px;
}
QTabBar::tab:selected { background: #1e1e21; color: #f0f0f0; font-weight: 600; }
QLineEdit {
    background: #2b2b2e; border: 1px solid #444; border-radius: 8px;
    padding: 8px 10px; color: #f0f0f0;
}
QLineEdit:focus { border: 1px solid #5e9bff; }
QListWidget {
    background: #232326; border: 1px solid #3a3a3d; border-radius: 8px; padding: 4px;
}
QListWidget::item { padding: 8px 6px; border-radius: 6px; }
QListWidget::item:selected { background: #35406b; }
QPushButton {
    background: #33343a; border: none; border-radius: 8px; padding: 8px 14px; font-weight: 600;
}
QPushButton:hover { background: #40414a; }
#dialButton, #primaryAction { background: #2e7d32; }
#dialButton:hover, #primaryAction:hover { background: #388e3c; }
#deleteButton { background: #c62828; }
#deleteButton:hover { background: #d32f2f; }
#dialpadDisplay { font-size: 22px; font-weight: 600; padding: 10px; }
"""

_CALL_TYPE_ICON = {"Incoming": "\u2199", "Outgoing": "\u2197", "Missed": "\u2716"}


class _EditContactDialog(QDialog):
    """Replaces the old QInputDialog-per-field flow with one real form."""

    def __init__(self, title: str, name: str, number: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(_DARK_STYLE)
        self._name_field = QLineEdit(name)
        self._number_field = QLineEdit(number)

        form = QFormLayout()
        form.addRow("Name", self._name_field)
        form.addRow("Number", self._number_field)

        save_button = QPushButton("Save")
        save_button.setObjectName("primaryAction")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addWidget(cancel_button)
        button_row.addWidget(save_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(button_row)

    def values(self) -> tuple[str, str]:
        return self._name_field.text().strip(), self._number_field.text().strip()


class _DialerTab(QWidget):
    def __init__(self, on_dial: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_dial = on_dial

        self._display = QLineEdit()
        self._display.setObjectName("dialpadDisplay")
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display.setPlaceholderText("Enter a number\u2026")

        call_button = QPushButton("\u260E  Call")
        call_button.setObjectName("dialButton")
        call_button.clicked.connect(self._dial)
        self._display.returnPressed.connect(self._dial)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._display.clear)

        button_row = QHBoxLayout()
        button_row.addWidget(clear_button)
        button_row.addWidget(call_button)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self._display)
        layout.addLayout(button_row)
        layout.addStretch()

    def _dial(self) -> None:
        number = self._display.text().strip()
        if number:
            self._on_dial(number)
            self._display.clear()


class _ContactsTab(QWidget):
    def __init__(self, controller: ContactsController, on_dial: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._on_dial = on_dial
        self._contacts: list[Contact] = []

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search name or number\u2026")
        self._search_box.textChanged.connect(self._refresh_list)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.itemDoubleClicked.connect(lambda _item: self._dial_selected())

        dial_button = QPushButton("Dial")
        dial_button.setObjectName("dialButton")
        dial_button.clicked.connect(self._dial_selected)
        add_button = QPushButton("Add\u2026")
        add_button.clicked.connect(self._prompt_add)
        edit_button = QPushButton("Edit\u2026")
        edit_button.clicked.connect(self._prompt_edit_selected)
        delete_button = QPushButton("Delete")
        delete_button.setObjectName("deleteButton")
        delete_button.clicked.connect(self._delete_selected)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._controller.refresh)

        button_row = QHBoxLayout()
        for button in (dial_button, add_button, edit_button, delete_button, refresh_button):
            button_row.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search_box)
        layout.addWidget(self._list)
        layout.addLayout(button_row)

        self._controller.contacts_updated.connect(self._on_contacts_updated)
        self._controller.operation_failed.connect(self._on_operation_failed)

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
            label = f"{contact.name}   {contact.number}" if contact.name else contact.number
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, contact)
            self._list.addItem(item)

    def _selected_contact(self) -> Contact | None:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _dial_selected(self) -> None:
        contact = self._selected_contact()
        if contact is not None and contact.number:
            self._on_dial(contact.number)

    def _prompt_add(self) -> None:
        dialog = _EditContactDialog("Add Contact", "", "", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, number = dialog.values()
            if number:
                self._controller.add(name, number)

    def _prompt_edit_selected(self) -> None:
        contact = self._selected_contact()
        if contact is None:
            return
        dialog = _EditContactDialog("Edit Contact", contact.name, contact.number, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, number = dialog.values()
            self._controller.update(contact.contact_id, name, number)

    def _delete_selected(self) -> None:
        contact = self._selected_contact()
        if contact is None:
            return
        confirm = QMessageBox.question(self, "Delete Contact", f"Delete {contact.name or contact.number}?")
        if confirm == QMessageBox.StandardButton.Yes:
            self._controller.delete(contact.contact_id)


class _CallLogTab(QWidget):
    def __init__(self, controller: CallLogController, on_dial: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._on_dial = on_dial

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(lambda _item: self._dial_selected())

        dial_button = QPushButton("Call Back")
        dial_button.setObjectName("dialButton")
        dial_button.clicked.connect(self._dial_selected)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._controller.refresh)

        button_row = QHBoxLayout()
        button_row.addWidget(dial_button)
        button_row.addWidget(refresh_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(button_row)

        self._controller.call_log_updated.connect(self._on_call_log_updated)

    def _on_call_log_updated(self, entries: list[CallLogEntry]) -> None:
        self._list.clear()
        for entry in entries:
            icon = _CALL_TYPE_ICON.get(entry.call_type_label, "")
            label = f"{icon} {entry.display_name}   \u2014   {entry.call_type_label}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self._list.addItem(item)

    def _dial_selected(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        entry: CallLogEntry = item.data(Qt.ItemDataRole.UserRole)
        if entry.number:
            self._on_dial(entry.number)


class PhoneWindow(QWidget):
    """The app's main "phone & contacts" surface - Dialer / Contacts / Call Log."""

    def __init__(
        self,
        contacts_controller: ContactsController,
        call_log_controller: CallLogController,
        on_dial: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dash Phone Con")
        self.resize(440, 560)
        self.setStyleSheet(_DARK_STYLE)

        self._contacts_controller = contacts_controller
        self._call_log_controller = call_log_controller

        tabs = QTabWidget()
        tabs.addTab(_DialerTab(on_dial), "Dialer")
        tabs.addTab(_ContactsTab(contacts_controller, on_dial), "Contacts")
        tabs.addTab(_CallLogTab(call_log_controller, on_dial), "Call Log")
        self._tabs = tabs

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(tabs)

    def show_and_refresh(self) -> None:
        """Open the window and pull the latest contacts + call log from the
        phone, so it never shows stale data from a previous session."""
        self._contacts_controller.refresh()
        self._call_log_controller.refresh()
        self.show()
        self.raise_()
        self.activateWindow()
