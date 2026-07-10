"""Unit tests for CallServer._replace_current_connection()'s logging.

Uses plain fake connection objects exposing `.remote_address` and an
async `.close()`, mirroring the fake-object pattern already used in
test_call_server_bind_retry.py - no real websocket/socket needed.
"""

from __future__ import annotations

import asyncio
import unittest

from PySide6.QtCore import QCoreApplication

from dashphone.network.call_server import CallServer


class _FakeConnection:
    def __init__(self, remote_address):
        self.remote_address = remote_address
        self.closed = False

    async def close(self):
        self.closed = True


class ReplaceCurrentConnectionLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QCoreApplication.instance() or QCoreApplication([])
        self.server = CallServer(port=9124)

    def test_no_log_on_first_connection(self) -> None:
        first = _FakeConnection(("192.168.1.10", 5000))

        import logging

        logger = logging.getLogger("dashphone.network.call_server")
        handler = logging.Handler()
        records = []
        handler.emit = records.append  # type: ignore[method-assign]
        logger.addHandler(handler)
        try:
            asyncio.run(self.server._replace_current_connection(first))
        finally:
            logger.removeHandler(handler)

        self.assertFalse(any("Replacing existing" in r.getMessage() for r in records))

    def test_logs_replacement_on_second_connection(self) -> None:
        first = _FakeConnection(("192.168.1.10", 5000))
        second = _FakeConnection(("192.168.1.20", 6000))

        asyncio.run(self.server._replace_current_connection(first))

        with self.assertLogs("dashphone.network.call_server", level="INFO") as cm:
            asyncio.run(self.server._replace_current_connection(second))

        self.assertTrue(first.closed)
        self.assertFalse(second.closed)
        joined = "\n".join(cm.output)
        self.assertIn("Replacing existing phone connection", joined)
        self.assertIn("192.168.1.10", joined)
        self.assertIn("192.168.1.20", joined)


if __name__ == "__main__":
    unittest.main()
