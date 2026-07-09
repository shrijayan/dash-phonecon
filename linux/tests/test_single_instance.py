import unittest
import uuid

from dashphone import single_instance
from dashphone.single_instance import SingleInstanceLock


class SingleInstanceLockTests(unittest.TestCase):
    """Uses a unique per-test abstract socket address (patched onto the
    module) so these tests don't collide with a real instance of the app
    that might already be running on this machine and holding the real
    lock address.
    """

    def setUp(self) -> None:
        self._original_address = single_instance._ABSTRACT_LOCK_ADDRESS
        single_instance._ABSTRACT_LOCK_ADDRESS = f"\0dash-phonecon.test-lock-{uuid.uuid4()}"

    def tearDown(self) -> None:
        single_instance._ABSTRACT_LOCK_ADDRESS = self._original_address

    def test_last_error_none_on_success(self) -> None:
        lock = SingleInstanceLock()
        try:
            self.assertTrue(lock.acquire())
            self.assertIsNone(lock.last_error)
        finally:
            if lock._socket is not None:
                lock._socket.close()

    def test_last_error_set_on_conflict(self) -> None:
        first = SingleInstanceLock()
        second = SingleInstanceLock()
        try:
            self.assertTrue(first.acquire())
            self.assertIsNone(first.last_error)

            self.assertFalse(second.acquire())
            self.assertIsInstance(second.last_error, OSError)
        finally:
            if first._socket is not None:
                first._socket.close()
            if second._socket is not None:
                second._socket.close()


if __name__ == "__main__":
    unittest.main()
