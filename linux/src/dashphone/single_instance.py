"""Stops a second copy of the app from starting (it would just fail to bind
port 8765 anyway, with a confusing crash).

Uses a Linux "abstract namespace" unix domain socket as the lock: binding
to an abstract address (a name starting with a NUL byte) never creates a
file on disk, and the kernel releases it automatically as soon as the
process exits - even if it crashes. There is nothing to clean up by hand.
"""

from __future__ import annotations

import socket

_ABSTRACT_LOCK_ADDRESS = "\0dash-phonecon.single-instance-lock"


class SingleInstanceLock:
    def __init__(self) -> None:
        self._socket: socket.socket | None = None

    def acquire(self) -> bool:
        """Returns True if this is the only running instance."""
        candidate = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            candidate.bind(_ABSTRACT_LOCK_ADDRESS)
        except OSError:
            candidate.close()
            return False
        self._socket = candidate
        return True
