"""Unit tests for logging_setup.log_file_path()'s XDG_STATE_HOME handling.

Run with:  QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m unittest discover -s tests -t . -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dashphone import logging_setup


class LogFilePathTests(unittest.TestCase):
    def test_honors_xdg_state_home_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir, unittest.mock.patch.dict(
            os.environ, {"XDG_STATE_HOME": tmp_dir}
        ):
            path = logging_setup.log_file_path()
            self.assertEqual(path, Path(tmp_dir) / "dash-phonecon" / "dashphone.log")

    def test_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir, unittest.mock.patch.dict(
            os.environ, {"XDG_STATE_HOME": tmp_dir}
        ):
            path = logging_setup.log_file_path()
            self.assertTrue(path.parent.is_dir())

    def test_falls_back_to_local_state_without_override(self) -> None:
        env_without_override = dict(os.environ)
        env_without_override.pop("XDG_STATE_HOME", None)
        with unittest.mock.patch.dict(os.environ, env_without_override, clear=True):
            path = logging_setup.log_file_path()
            self.assertTrue(str(path).endswith(".local/state/dash-phonecon/dashphone.log"))


if __name__ == "__main__":
    unittest.main()
