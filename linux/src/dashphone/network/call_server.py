"""WebSocket server that talks to the Android phone.

This module only knows about bytes/JSON framing and connection lifecycle -
it has no idea what CALL_RINGING or ANSWER *mean*. That belongs to
CallStateController (see state/call_state_controller.py). Keeping the two
separate means either one can change without touching the other.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Optional

import websockets
from PySide6.QtCore import QObject, Signal
from websockets.asyncio.server import ServerConnection

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8765
DEFAULT_HOST = "0.0.0.0"  # listen on every interface - the phone connects over LAN/Tailscale

BIND_RETRY_ATTEMPTS = 3
BIND_RETRY_DELAY_SECONDS = 1.0


async def bind_with_retries(bind_fn, attempts: int = BIND_RETRY_ATTEMPTS, delay: float = BIND_RETRY_DELAY_SECONDS):
    """Call the async ``bind_fn`` (no args), retrying a bounded number of times on OSError.

    This exists to survive the brief window right after a restart where the
    previous process's WebSocket TCP socket is still lingering in TIME_WAIT
    even though `SingleInstanceLock`'s abstract-namespace socket has already
    been released - without a retry, that race causes an immediate,
    permanent `bind_failed`. Kept as a free function (not a method) so it's
    trivially unit-testable with a fake `bind_fn` and no real socket/asyncio
    server involved.

    Raises the last `OSError` if every attempt fails.
    """
    last_error: Optional[OSError] = None
    for attempt in range(1, attempts + 1):
        try:
            return await bind_fn()
        except OSError as error:
            last_error = error
            logger.warning("Bind attempt %s/%s failed: %s", attempt, attempts, error)
            if attempt < attempts:
                await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


class CallServer(QObject):
    """Owns the WebSocket listener.

    Runs its own asyncio event loop on a background thread so the Qt event
    loop on the main thread never blocks on network I/O. Signals are safe
    to connect to from the GUI thread: Qt automatically queues them across
    threads because the receivers live on the main thread's event loop.
    """

    connection_changed = Signal(bool)  # True once a phone connects, False when it disconnects
    message_received = Signal(dict)  # one decoded JSON message from the phone
    bind_failed = Signal(str)  # emitted if the port could not be bound (e.g. already running)
    listening = Signal(int)  # emitted with the port once the server has actually started listening

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._host = host
        self._port = port
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._current_connection: Optional[ServerConnection] = None

    @property
    def port(self) -> int:
        return self._port

    def start(self) -> None:
        """Start the server on a background thread. Call once from the GUI thread."""
        if self._thread is not None:
            logger.warning("CallServer.start() called twice - ignoring")
            return

        self._thread = threading.Thread(target=self._run_event_loop, name="dashphone-ws-server", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Ask the background thread to shut down and wait for it to finish."""
        if self._loop is None or self._stop_event is None:
            return
        self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def send(self, message: dict) -> None:
        """Send a JSON message to the currently connected phone, if any.

        Safe to call from the Qt/GUI thread - the actual send is handed off
        to the asyncio loop running on the background thread.
        """
        if self._loop is None:
            logger.warning("send() called before the server started - dropping message")
            return
        asyncio.run_coroutine_threadsafe(self._send_async(message), self._loop)

    # -- background thread entry point --

    def _run_event_loop(self) -> None:
        try:
            asyncio.run(self._serve())
        except OSError as error:
            logger.error("Could not listen on %s:%s - %s", self._host, self._port, error)
            self.bind_failed.emit(str(error))
        except Exception:
            logger.exception("WebSocket server crashed")

    async def _serve(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()

        async def _bind():
            return await websockets.serve(self._handle_client, self._host, self._port)

        server = await bind_with_retries(_bind)
        self.listening.emit(self._port)
        try:
            logger.info("Listening for the phone on %s:%s", self._host, self._port)
            await self._stop_event.wait()
        finally:
            server.close()
            await server.wait_closed()

        logger.info("WebSocket server stopped")

    # -- per-connection handling --

    async def _handle_client(self, connection: ServerConnection) -> None:
        await self._replace_current_connection(connection)
        logger.info("Phone connected from %s", connection.remote_address)
        self.connection_changed.emit(True)

        try:
            async for raw_message in connection:
                self._dispatch_message(raw_message)
        except websockets.ConnectionClosed:
            pass
        except Exception:
            logger.exception("Error while handling phone connection")
        finally:
            if self._current_connection is connection:
                self._current_connection = None
                self.connection_changed.emit(False)
                logger.info("Phone disconnected")

    async def _replace_current_connection(self, connection: ServerConnection) -> None:
        """Only one phone can be connected at a time - a new connection wins."""
        previous = self._current_connection
        self._current_connection = connection
        if previous is not None and previous is not connection:
            await previous.close()

    def _dispatch_message(self, raw_message: str | bytes) -> None:
        try:
            parsed = json.loads(raw_message)
        except (ValueError, TypeError):
            logger.warning("Ignoring non-JSON message from phone: %r", raw_message)
            return

        if not isinstance(parsed, dict):
            logger.warning("Ignoring non-object JSON message from phone: %r", parsed)
            return

        self.message_received.emit(parsed)

    async def _send_async(self, message: dict) -> None:
        connection = self._current_connection
        if connection is None:
            logger.warning("Attempted send while no phone is connected - dropping message")
            return
        try:
            await connection.send(json.dumps(message))
        except websockets.ConnectionClosed:
            logger.warning("Send failed - connection was already closed")
