"""System tray icon + dropdown menu.

Mirrors MenuBarView.swift + the icon logic in DashPhoneApp.swift: a status
line, an active-call timer with Hang Up when a call is live, and Quit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from dashphone.state import CallPhase, CallState
from dashphone.ui.icons import icon_for_connection_and_state

APP_DISPLAY_NAME = "Dash Phone Con"


class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        on_hangup: Callable[[], None],
        on_quit: Callable[[], None],
        device_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._is_connected = False
        self._state: CallState = CallState.idle()

        self._status_action = self._disabled_action("Not Connected")
        self._device_action = self._disabled_action(device_label)

        self._timer_action = self._disabled_action("00:00")
        self._timer_action.setVisible(False)

        self._hangup_action = QAction("Hang Up")
        self._hangup_action.setVisible(False)
        self._hangup_action.triggered.connect(lambda: on_hangup())

        quit_action = QAction(f"Quit {APP_DISPLAY_NAME}")
        quit_action.triggered.connect(lambda: on_quit())

        menu = QMenu()
        menu.addAction(self._status_action)
        menu.addAction(self._device_action)
        menu.addSeparator()
        menu.addAction(self._timer_action)
        menu.addAction(self._hangup_action)
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

    def set_state(self, state: CallState) -> None:
        self._state = state
        if state.phase is CallPhase.ACTIVE:
            self._timer.start()
        else:
            self._timer.stop()
        self._refresh()

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
        if not self._is_connected:
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
