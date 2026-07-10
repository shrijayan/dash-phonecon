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
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from dashphone.state.call_log_controller import CallLogController, CallLogEntry
from dashphone.state.contacts_controller import Contact, ContactsController

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
#dialpadDisplay { font-size: 24px; font-weight: 600; padding: 12px; }
#keypadButton { font-size: 18px; font-weight: 700; min-height: 44px; background: #2b2b2e; }
#keypadButton:hover { background: #34353c; }
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
_KEYPAD_ROWS = (("1", "2", "3"), ("4", "5", "6"), ("7", "8", "9"), ("*", "0", "#"))


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


class _DialerTab(QWidget):
    def __init__(self, on_dial: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_dial = on_dial

        self._display = QLineEdit()
        self._display.setObjectName("dialpadDisplay")
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display.setPlaceholderText("Enter a number\u2026")
        self._display.returnPressed.connect(self._dial)

        keypad = QGridLayout()
        keypad.setSpacing(8)
        for row_index, row in enumerate(_KEYPAD_ROWS):
            for col_index, digit in enumerate(row):
                button = QPushButton(digit)
                button.setObjectName("keypadButton")
                button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                button.clicked.connect(lambda _checked=False, d=digit: self._append_digit(d))
                keypad.addWidget(button, row_index, col_index)

        call_button = QPushButton("\u260E  Call")
        call_button.setObjectName("dialButton")
        call_button.clicked.connect(self._dial)

        clear_button = QPushButton("\u232b  Clear")
        clear_button.clicked.connect(self._clear)

        button_row = QHBoxLayout()
        button_row.addWidget(clear_button)
        button_row.addWidget(call_button)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addWidget(self._display)
        layout.addLayout(keypad)
        layout.addLayout(button_row)
        layout.addStretch()

    def _append_digit(self, digit: str) -> None:
        self._display.setText(self._display.text() + digit)
        self._display.setFocus()

    def _clear(self) -> None:
        if self._display.text():
            self._display.setText(self._display.text()[:-1])
        self._display.setFocus()

    def _dial(self) -> None:
        number = self._display.text().strip()
        if number:
            self._on_dial(number)
            self._display.clear()


def _contact_row_widget(contact: Contact) -> QWidget:
    avatar = QLabel(_initials(contact.name, contact.number))
    avatar.setObjectName("avatarLabel")

    name_label = QLabel(contact.name or contact.number)
    name_label.setObjectName("contactName")
    number_label = QLabel(contact.number if contact.name else "")
    number_label.setObjectName("contactNumber")

    text_column = QVBoxLayout()
    text_column.setSpacing(1)
    text_column.addWidget(name_label)
    if contact.name:
        text_column.addWidget(number_label)

    row = QHBoxLayout()
    row.setContentsMargins(6, 6, 6, 6)
    row.addWidget(avatar)
    row.addSpacing(10)
    row.addLayout(text_column)
    row.addStretch()

    widget = QWidget()
    widget.setLayout(row)
    return widget


def _call_log_row_widget(entry: CallLogEntry) -> QWidget:
    icon = _CALL_TYPE_ICON.get(entry.call_type_label, "")
    color = _CALL_TYPE_COLOR.get(entry.call_type_label, "#9a9a9e")

    icon_label = QLabel(icon)
    icon_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: 700;")
    icon_label.setFixedWidth(20)

    name_label = QLabel(entry.display_name)
    name_label.setObjectName("contactName")
    type_label = QLabel(entry.call_type_label)
    type_label.setObjectName("contactNumber")
    type_label.setStyleSheet(f"color: {color};")

    text_column = QVBoxLayout()
    text_column.setSpacing(1)
    text_column.addWidget(name_label)
    text_column.addWidget(type_label)

    row = QHBoxLayout()
    row.setContentsMargins(6, 6, 6, 6)
    row.addWidget(icon_label)
    row.addSpacing(6)
    row.addLayout(text_column)
    row.addStretch()

    widget = QWidget()
    widget.setLayout(row)
    return widget


class _ContactsTab(QWidget):
    def __init__(self, controller: ContactsController, on_dial: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._on_dial = on_dial
        self._contacts: list[Contact] = []

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\U0001f50d  Search name or number\u2026")
        self._search_box.textChanged.connect(self._refresh_list)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.itemDoubleClicked.connect(lambda _item: self._dial_selected())

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

    def _refresh_list(self) -> None:
        query = self._search_box.text()
        filtered = ContactsController.filter_contacts(self._contacts, query)
        self._list.clear()
        for contact in filtered:
            item = QListWidgetItem(self._list)
            item.setData(Qt.ItemDataRole.UserRole, contact)
            item.setSizeHint(_contact_row_widget(contact).sizeHint())
            self._list.setItemWidget(item, _contact_row_widget(contact))
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
        self._list.itemDoubleClicked.connect(lambda _item: self._dial_selected())
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
            item = QListWidgetItem(self._list)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setSizeHint(_call_log_row_widget(entry).sizeHint())
            self._list.setItemWidget(item, _call_log_row_widget(entry))
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
        self.resize(440, 620)
        self.setStyleSheet(_DARK_STYLE)

        self._contacts_controller = contacts_controller
        self._call_log_controller = call_log_controller

        header = QLabel("\u260E  Dash Phone Con")
        header.setObjectName("headerTitle")

        tabs = QTabWidget()
        tabs.addTab(_DialerTab(on_dial), "\u2328  Dialer")
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
