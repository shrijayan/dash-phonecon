"""The main Phone window: a single tabbed surface (Contacts, with a merged
dial-any-number row, / Call Log) replacing the separate ad-hoc dialogs and
the old standalone Dialer tab. Styled to match the
CallPopupWindow's dark card aesthetic instead of looking like a raw,
unstyled Qt form - this is the app's actual "phone & contacts" UI, not
a debug utility.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QTimer
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

# Debounce delay for the contacts search box - typing re-filters and
# rebuilds the whole (potentially 1000+ item) list, so we wait for a
# short pause in typing instead of doing that on every keystroke.
_SEARCH_DEBOUNCE_MS = 200

_DARK_STYLE = """
QWidget { background-color: #1e1e21; color: #f0f0f0; font-size: 13px; }
#headerTitle { font-size: 16px; font-weight: 700; padding: 2px 0 8px 2px; }
QTabWidget::pane { border: 1px solid #3a3a3d; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background: #2b2b2e; color: #b0b0b0; padding: 9px 16px; font-size: 13px;
    border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px;
}
QTabBar::tab:selected { background: #1e1e21; color: #f0f0f0; font-weight: 600; }
QLineEdit {
    background: #2b2b2e; border: 1px solid #444; border-radius: 8px;
    padding: 9px 12px; color: #f0f0f0;
}
QLineEdit:focus { border: 1px solid #5e9bff; }
QListWidget {
    background: #232326; border: 1px solid #3a3a3d; border-radius: 8px; padding: 4px;
    outline: none;
}
QListWidget::item { border-radius: 6px; margin: 2px 0; }
QListWidget::item:selected { background: #35406b; }
QListWidget::item:hover { background: #2b2b30; }
QPushButton {
    background: #33343a; border: none; border-radius: 8px; padding: 9px 14px; font-weight: 600;
}
QPushButton:hover { background: #40414a; }
QPushButton:pressed { background: #2a2b30; }
#dialButton, #primaryAction { background: #2e7d32; }
#dialButton:hover, #primaryAction:hover { background: #388e3c; }
#deleteButton { background: #c62828; }
#deleteButton:hover { background: #d32f2f; }
#emptyState { color: #6f6f75; font-size: 13px; padding: 24px; }
#contactName { font-size: 13px; font-weight: 600; color: #f0f0f0; }
#contactNumber { font-size: 12px; color: #9a9a9e; }
#avatarLabel {
    background: #35406b; color: #dfe6ff; font-weight: 700; font-size: 14px;
    border-radius: 16px; min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px;
    qproperty-alignment: AlignCenter;
}
"""

_CALL_TYPE_ICON = {"Incoming": "\u2199", "Outgoing": "\u2197", "Missed": "\u2716"}
_CALL_TYPE_COLOR = {"Incoming": "#4caf50", "Outgoing": "#5e9bff", "Missed": "#e57373"}


def _initials(name: str, number: str) -> str:
    text = name.strip() or number.strip()
    parts = [p for p in text.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _empty_state_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("emptyState")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class _EditContactDialog(QDialog):
    """Replaces the old QInputDialog-per-field flow with one real form."""

    def __init__(self, title: str, name: str, number: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(_DARK_STYLE)
        self._name_field = QLineEdit(name)
        self._name_field.setPlaceholderText("e.g. Priya Sharma")
        self._number_field = QLineEdit(number)
        self._number_field.setPlaceholderText("e.g. +1 555 0100")

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


class _DialEntryRow(QWidget):
    """Compact manual-number dial row, merged into the Contacts tab so
    there's one "Phone" surface instead of a separate Dialer tab."""

    def __init__(self, on_dial: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_dial = on_dial

        self._entry = QLineEdit()
        self._entry.setPlaceholderText("Enter a number to dial\u2026")
        self._entry.returnPressed.connect(self._dial)

        call_button = QPushButton("\u260E Call")
        call_button.setObjectName("dialButton")
        call_button.clicked.connect(self._dial)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._entry)
        row.addWidget(call_button)

    def _dial(self) -> None:
        number = self._entry.text().strip()
        if number:
            self._on_dial(number)
            self._entry.clear()


def _contact_item_text(contact: Contact) -> str:
    """Plain two-line label text for a contact row.

    Building a full QWidget (QLabel avatar + 2 more QLabels + nested
    QHBoxLayout/QVBoxLayout) per contact and wiring it in via
    `QListWidget.setItemWidget` is the classic Qt perf trap for large
    lists: with ~1500 contacts that's ~6000 real widgets constructed on
    every refresh *and* on every keystroke while searching (since
    `_refresh_list` clears and rebuilds the whole list). A bare
    QListWidgetItem with multi-line text is drawn by the list's item
    delegate with no child widgets at all - dramatically cheaper, and
    is what actually fixes the multi-second search lag.
    """
    if contact.name:
        return f"{contact.name}\n{contact.number}"
    return contact.number


def _call_log_item_text(entry: CallLogEntry) -> str:
    icon = _CALL_TYPE_ICON.get(entry.call_type_label, "")
    return f"{icon} {entry.display_name}\n{entry.call_type_label}"


class _ContactsTab(QWidget):
    def __init__(self, controller: ContactsController, on_dial: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._on_dial = on_dial
        self._contacts: list[Contact] = []

        self._dial_entry = _DialEntryRow(on_dial)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\U0001f50d  Search name or number\u2026")
        self._search_box.textChanged.connect(self._on_search_text_changed)
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(_SEARCH_DEBOUNCE_MS)
        self._search_debounce.timeout.connect(self._refresh_list)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # No itemDoubleClicked -> dial here on purpose: a quick double-click
        # while just trying to select a contact (e.g. re-clicking to make
        # sure it's highlighted) used to place an unintended call. Dialing
        # now always requires an explicit tap on the Dial button.

        self._empty_label = _empty_state_label("No contacts yet \u2014 tap Add to create one.")

        dial_button = QPushButton("\u260E Dial")
        dial_button.setObjectName("dialButton")
        dial_button.clicked.connect(self._dial_selected)
        add_button = QPushButton("+ Add")
        add_button.clicked.connect(self._prompt_add)
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self._prompt_edit_selected)
        delete_button = QPushButton("Delete")
        delete_button.setObjectName("deleteButton")
        delete_button.clicked.connect(self._delete_selected)
        refresh_button = QPushButton("\u21bb")
        refresh_button.setToolTip("Refresh from phone")
        refresh_button.clicked.connect(self._controller.refresh)

        button_row = QHBoxLayout()
        for button in (dial_button, add_button, edit_button, delete_button, refresh_button):
            button_row.addWidget(button)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(self._dial_entry)
        layout.addWidget(self._search_box)
        layout.addWidget(self._list)
        layout.addWidget(self._empty_label)
        layout.addLayout(button_row)

        self._controller.contacts_updated.connect(self._on_contacts_updated)
        self._controller.operation_failed.connect(self._on_operation_failed)
        self._refresh_list()

    def _on_contacts_updated(self, contacts: list[Contact]) -> None:
        self._contacts = contacts
        self._refresh_list()

    def _on_operation_failed(self, error: str) -> None:
        QMessageBox.warning(self, "Contacts", f"That didn't work: {error}")

    def _on_search_text_changed(self) -> None:
        self._search_debounce.start()

    def _refresh_list(self) -> None:
        query = self._search_box.text()
        filtered = ContactsController.filter_contacts(self._contacts, query)
        self._list.clear()
        for contact in filtered:
            item = QListWidgetItem(_contact_item_text(contact), self._list)
            item.setData(Qt.ItemDataRole.UserRole, contact)
        self._list.setVisible(bool(filtered))
        self._empty_label.setVisible(not filtered)

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
        # No itemDoubleClicked -> dial here either, for the same reason as
        # the Contacts tab: dialing must be an explicit "Call Back" tap.
        self._empty_label = _empty_state_label("No recent calls.")

        dial_button = QPushButton("\u260E Call Back")
        dial_button.setObjectName("dialButton")
        dial_button.clicked.connect(self._dial_selected)
        refresh_button = QPushButton("\u21bb Refresh")
        refresh_button.clicked.connect(self._controller.refresh)

        button_row = QHBoxLayout()
        button_row.addWidget(dial_button)
        button_row.addWidget(refresh_button)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(self._list)
        layout.addWidget(self._empty_label)
        layout.addLayout(button_row)

        self._controller.call_log_updated.connect(self._on_call_log_updated)
        self._on_call_log_updated(controller.entries)

    def _on_call_log_updated(self, entries: list[CallLogEntry]) -> None:
        self._list.clear()
        for entry in entries:
            item = QListWidgetItem(_call_log_item_text(entry), self._list)
            item.setData(Qt.ItemDataRole.UserRole, entry)
        self._list.setVisible(bool(entries))
        self._empty_label.setVisible(not entries)

    def _dial_selected(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        entry: CallLogEntry = item.data(Qt.ItemDataRole.UserRole)
        if entry.number:
            self._on_dial(entry.number)


class PhoneWindow(QWidget):
    """The app's main "phone & contacts" surface - Contacts (dial + CRUD) / Call Log."""

    def __init__(
        self,
        contacts_controller: ContactsController,
        call_log_controller: CallLogController,
        on_dial: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dash Phone Con")
        self.resize(440, 620)
        self.setStyleSheet(_DARK_STYLE)

        self._contacts_controller = contacts_controller
        self._call_log_controller = call_log_controller

        header = QLabel("\u260E  Dash Phone Con")
        header.setObjectName("headerTitle")

        tabs = QTabWidget()
        tabs.addTab(_ContactsTab(contacts_controller, on_dial), "\U0001f465  Contacts")
        tabs.addTab(_CallLogTab(call_log_controller, on_dial), "\U0001f553  Call Log")
        self._tabs = tabs

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.addWidget(header)
        layout.addWidget(tabs)

    def show_and_refresh(self) -> None:
        """Open the window and pull the latest contacts + call log from the
        phone, so it never shows stale data from a previous session."""
        self._contacts_controller.refresh()
        self._call_log_controller.refresh()
        self.show()
        self.raise_()
        self.activateWindow()
