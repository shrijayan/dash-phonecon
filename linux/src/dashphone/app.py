"""Composition root: creates every component and wires them together.

This is the only file that knows about all the pieces at once. Everything
else only depends on the small interface it actually needs (a CallState, a
"send this JSON" callable, and so on) - which is what keeps each piece
testable and replaceable on its own. See linux/README.md for a walkthrough
of how a message flows through these pieces.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMessageBox

from dashphone.bluetooth import HfpManager
from dashphone.logging_setup import clear_log_file, log_file_path, setup_logging
from dashphone.media_ducker import MediaDucker
from dashphone.network import CallServer, device_label
from dashphone.protocol import MessageType
from dashphone.single_instance import SingleInstanceLock
from dashphone.state import CallPhase, CallState, CallStateController
from dashphone.state.contacts_controller import ContactsController
from dashphone.ui import CallPopupWindow, ContactsWindow, TrayIcon

APP_NAME = "Dash Phone Con"

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)  # closing the popup must not quit the tray app

    lock = SingleInstanceLock()
    if not lock.acquire():
        logger.warning("Another instance of %s is already running - exiting", APP_NAME)
        QMessageBox.warning(None, APP_NAME, f"{APP_NAME} is already running.")
        return 1

    server = CallServer()
    controller = CallStateController(send_json=server.send)
    contacts_controller = ContactsController(send_json=server.send)
    hfp_manager = HfpManager()
    media_ducker = MediaDucker()

    popup = CallPopupWindow(
        on_answer=lambda: controller.send_command(MessageType.ANSWER),
        on_decline=lambda: controller.send_command(MessageType.REJECT),
    )
    bluetooth_audio_enabled = True

    contacts_window = ContactsWindow(contacts_controller, on_dial=controller.dial)

    def on_toggle_bluetooth_audio(enabled: bool) -> None:
        nonlocal bluetooth_audio_enabled
        bluetooth_audio_enabled = enabled

    tray = TrayIcon(
        on_hangup=lambda: controller.send_command(MessageType.HANGUP),
        on_quit=app.quit,
        device_label=device_label(),
        on_open_log=lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_file_path()))),
        on_clear_log=clear_log_file,
        on_toggle_bluetooth_audio=on_toggle_bluetooth_audio,
        on_dial=controller.dial,
        on_open_contacts=contacts_window.show_and_refresh,
    )

    def on_state_changed(state: CallState) -> None:
        tray.set_state(state)

        if state.phase is CallPhase.RINGING:
            popup.show_call(number=state.number, name=state.name)
        else:
            popup.close()

        if state.phase is CallPhase.ACTIVE:
            hfp_manager.open_audio()
            media_ducker.duck_others()
        elif state.phase is CallPhase.IDLE:
            hfp_manager.close_audio()
            media_ducker.restore_others()

    server.message_received.connect(controller.handle_event)
    server.message_received.connect(contacts_controller.handle_event)
    server.connection_changed.connect(tray.set_connected)
    controller.state_changed.connect(on_state_changed)

    server.start()
    hfp_manager.start()
    tray.show()

    logger.info("%s is running", APP_NAME)
    exit_code = app.exec()

    server.stop()
    return exit_code
