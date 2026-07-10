"""Stops a second copy of the app from starting - but instead of just
failing with "already running", the second launch tells the first
instance to raise its Phone window. This is what makes clicking the
app icon in Ubuntu's app list behave like a normal single-window app
instead of erroring out.

Uses a Linux "abstract namespace" unix domain socket as both the lock
and the IPC channel: binding to an abstract address (a name starting
with a NUL byte) never creates a file on disk, and the kernel releases
it automatically as soon as the process exits - even if it crashes.
There is nothing to clean up by hand.
"""

from __future__ import annotations

import socket
from typing import Callable

from PySide6.QtCore import QSocketNotifier

_ABSTRACT_LOCK_ADDRESS = "\0dash-phonecon.single-instance-lock"
_SHOW_COMMAND = b"SHOW\n"


class SingleInstanceLock:
    def __init__(self) -> None:
        self._socket: socket.socket | None = None
        self._notifier: QSocketNotifier | None = None
        self.last_error: OSError | None = None

    def acquire(self, on_show_requested: Callable[[], None] | None = None) -> bool:
        """Returns True if this is the only running instance.

        If another instance is already running, this sends it a "show
        your window" request over the same socket instead of just
        failing silently, then returns False.

        On success, if ``on_show_requested`` is given, it will be called
        every time a later launch (e.g. clicking the app icon again)
        connects in - so the app can raise its main window instead of
        doing nothing.
        """
        candidate = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            candidate.bind(_ABSTRACT_LOCK_ADDRESS)
        except OSError as exc:
            candidate.close()
            self.last_error = exc
            self._request_show()
            return False

        candidate.listen(5)
        candidate.setblocking(False)
        self._socket = candidate
        self.last_error = None

        if on_show_requested is not None:
            self._notifier = QSocketNotifier(candidate.fileno(), QSocketNotifier.Type.Read)
            self._notifier.activated.connect(lambda _fd: self._accept_and_dispatch(on_show_requested))

        return True

    def _accept_and_dispatch(self, on_show_requested: Callable[[], None]) -> None:
        try:
            connection, _ = self._socket.accept()  # type: ignore[union-attr]
            connection.close()
        except OSError:
            return
        on_show_requested()

    def _request_show(self) -> None:
        """Best-effort: tell the already-running instance to raise its window."""
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(_ABSTRACT_LOCK_ADDRESS)
                client.sendall(_SHOW_COMMAND)
        except OSError:
            pass  # the other instance may be mid-shutdown; nothing more we can do
