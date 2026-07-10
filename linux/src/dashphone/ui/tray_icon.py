"""System tray icon + dropdown menu.

Mirrors MenuBarView.swift + the icon logic in DashPhoneApp.swift: a status
line, an active-call timer with Hang Up when a call is live, and Quit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMenu, QSystemTrayIcon, QWidget

from dashphone.state import CallPhase, CallState
from dashphone.ui.icons import icon_for_connection_and_state

APP_DISPLAY_NAME = "Dash Phone Con"


def normalize_dial_number(raw: str) -> str:
    """Strip whitespace and drop anything but leading '+' and digits.

    Pure function (no Qt) so it's trivially unit-testable and reusable if
    another entry point for dialing gets added later. Users may paste a
    number with spaces/dashes/parens from a contacts list or webpage -
    normalize before it ever hits the wire.
    """
    raw = raw.strip()
    if not raw:
        return ""
    keep_leading_plus = raw.startswith("+")
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return ""
    return f"+{digits}" if keep_leading_plus else digits


class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        on_hangup: Callable[[], None],
        on_quit: Callable[[], None],
        device_label: str,
        on_open_log: Callable[[], None] | None = None,
        on_clear_log: Callable[[], None] | None = None,
        on_toggle_bluetooth_audio: Callable[[bool], None] | None = None,
        on_dial: Callable[[str], None] | None = None,
        on_open_contacts: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._is_connected = False
        self._state: CallState = CallState.idle()
        self._bind_error: str | None = None
        self._listening_port: int | None = None

        self._status_action = self._disabled_action("Not Connected")
        self._device_action = self._disabled_action(device_label)

        self._timer_action = self._disabled_action("00:00")
        self._timer_action.setVisible(False)

        self._hangup_action = QAction("Hang Up")
        self._hangup_action.setVisible(False)
        self._hangup_action.triggered.connect(lambda: on_hangup())

        self._dial_action = QAction("Dial\u2026")
        self._on_dial = on_dial
        self._dial_action.triggered.connect(self._prompt_and_dial)

        self._contacts_action = QAction("\u260E Phone \u0026 Contacts\u2026")
        self._on_open_contacts = on_open_contacts
        if on_open_contacts is not None:
            self._contacts_action.triggered.connect(lambda: on_open_contacts())

        self._open_log_action = QAction("Open Log File")
        if on_open_log is not None:
            self._open_log_action.triggered.connect(lambda: on_open_log())

        self._clear_log_action = QAction("Clear Log File")
        if on_clear_log is not None:
            self._clear_log_action.triggered.connect(lambda: on_clear_log())

        self._bluetooth_audio_action = QAction("Route Call Audio via Bluetooth")
        self._bluetooth_audio_action.setCheckable(True)
        self._bluetooth_audio_action.setChecked(True)
        if on_toggle_bluetooth_audio is not None:
            self._bluetooth_audio_action.toggled.connect(lambda checked: on_toggle_bluetooth_audio(checked))

        quit_action = QAction(f"Quit {APP_DISPLAY_NAME}")
        quit_action.triggered.connect(lambda: on_quit())

        menu = QMenu()
        menu.addAction(self._status_action)
        menu.addAction(self._device_action)
        menu.addSeparator()
        menu.addAction(self._timer_action)
        menu.addAction(self._hangup_action)
        menu.addAction(self._dial_action)
        menu.addAction(self._contacts_action)
        menu.addSeparator()
        menu.addAction(self._open_log_action)
        menu.addAction(self._clear_log_action)
        menu.addAction(self._bluetooth_audio_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_timer_text)

        self._refresh()

    def set_connected(self, connected: bool) -> None:
        self._is_connected = connected
        self._refresh()

    def set_listening(self, port: int) -> None:
        """Called once the WebSocket server has actually bound its port and
        started listening (see CallServer.listening). Before this signal
        existed, the tray showed the exact same "Not Connected" text whether
        the server hadn't finished starting up yet, was listening fine and
        just waiting for the phone, or had silently crashed - this gives the
        "waiting for the phone" state its own distinct, informative label."""
        self._listening_port = port
        self._refresh()

    def set_state(self, state: CallState) -> None:
        self._state = state
        if state.phase is CallPhase.ACTIVE:
            self._timer.start()
        else:
            self._timer.stop()
        self._refresh()

    def set_device_label(self, text: str) -> None:
        """Update the disabled \"This device: ip:port\" menu item.

        Without this, the label computed once at startup (see app.py's
        main()) goes stale forever if the network changes - e.g. a laptop
        that suspends/resumes on a different Wi-Fi network or plugs into
        Ethernet keeps showing the old, wrong IP until the whole app is
        restarted, silently breaking the "type this into the Android app"
        flow the label exists for."""
        self._device_action.setText(text)

    def set_bind_error(self, message: str) -> None:
        """Called when the WebSocket server couldn't bind its port (see
        CallServer.bind_failed). Today that failure was only logged - the
        tray kept showing the generic "Not Connected" status with no way
        for the user to know the app never actually started listening.
        This overrides the status line/tooltip with the real reason and
        also fires a native notification, in case the dropdown is never
        opened."""
        self._bind_error = message
        self._refresh()
        self.showMessage(APP_DISPLAY_NAME, message, QSystemTrayIcon.MessageIcon.Warning)

    def notify_missed_call(self, name: str, number: str) -> None:
        """Called when a call rang and ended without ever being answered
        (see CallStateController.call_missed). The popup that was showing
        the incoming call has already closed by the time CALL_ENDED
        arrives, so without this the user would have no record that a call
        happened at all unless they noticed it live."""
        who = name or number or "Unknown"
        self.showMessage(APP_DISPLAY_NAME, f"Missed call from {who}", QSystemTrayIcon.MessageIcon.Information)

    def _prompt_and_dial(self) -> None:
        """Ask for a number via a small input dialog, then hand it to on_dial.

        Blank/whitespace-only input is silently ignored (user hit Cancel or
        typed nothing) rather than sending an empty DIAL to the phone.
        """
        number, ok = QInputDialog.getText(None, "Dial", "Phone number:", QLineEdit.EchoMode.Normal, "")
        cleaned = normalize_dial_number(number)
        if ok and cleaned and self._on_dial is not None:
            self._on_dial(cleaned)

    @staticmethod
    def _disabled_action(text: str) -> QAction:
        action = QAction(text)
        action.setEnabled(False)
        return action

    def _refresh(self) -> None:
        self.setIcon(icon_for_connection_and_state(self._is_connected, self._state.phase))

        label = self._status_label()
        self._status_action.setText(label)
        self.setToolTip(f"{APP_DISPLAY_NAME} \u2014 {label}")

        is_active = self._state.phase is CallPhase.ACTIVE
        self._timer_action.setVisible(is_active)
        self._hangup_action.setVisible(is_active)
        if is_active:
            self._update_timer_text()

    def _status_label(self) -> str:
        if self._bind_error is not None:
            return self._bind_error
        if not self._is_connected:
            if self._listening_port is not None:
                return f"Waiting for phone on port {self._listening_port}"
            return "Not Connected"
        if self._state.phase is CallPhase.IDLE:
            return "Connected \u2014 No Active Call"
        if self._state.phase is CallPhase.RINGING:
            return f"Ringing: {self._state.display_name}"
        return "Call Active"

    def _update_timer_text(self) -> None:
        start_time = self._state.start_time
        if start_time is None:
            self._timer_action.setText("00:00")
            return
        elapsed = max(0, int((datetime.now() - start_time).total_seconds()))
        minutes, seconds = divmod(elapsed, 60)
        self._timer_action.setText(f"{minutes:02d}:{seconds:02d}")
