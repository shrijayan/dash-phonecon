"""Unit tests for CallServer's bounded bind-retry helper.

No real socket or long-lived asyncio server is needed - `bind_with_retries`
is a plain free function that takes an arbitrary async no-arg callable, so
we can simulate the "port is briefly still in use, then frees up" race with
a fake bind function that raises OSError a fixed number of times.
"""

from __future__ import annotations

import asyncio
import unittest

from dashphone.network.call_server import bind_with_retries


class BindWithRetriesTests(unittest.TestCase):
    def test_succeeds_after_transient_failures(self) -> None:
        attempts_made = []

        async def flaky_bind():
            attempts_made.append(1)
            if len(attempts_made) < 3:
                raise OSError("Address already in use")
            return "server-object"

        result = asyncio.run(bind_with_retries(flaky_bind, attempts=3, delay=0))

        self.assertEqual(result, "server-object")
        self.assertEqual(len(attempts_made), 3)

    def test_succeeds_on_first_try_without_retrying(self) -> None:
        attempts_made = []

        async def always_ok_bind():
            attempts_made.append(1)
            return "server-object"

        result = asyncio.run(bind_with_retries(always_ok_bind, attempts=3, delay=0))

        self.assertEqual(result, "server-object")
        self.assertEqual(len(attempts_made), 1)

    def test_raises_after_exhausting_all_attempts(self) -> None:
        attempts_made = []

        async def always_failing_bind():
            attempts_made.append(1)
            raise OSError("Address already in use")

        with self.assertRaises(OSError):
            asyncio.run(bind_with_retries(always_failing_bind, attempts=3, delay=0))

        self.assertEqual(len(attempts_made), 3)


if __name__ == "__main__":
    unittest.main()
