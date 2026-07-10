"""Rotating file logger, so a call that misbehaves after you've logged out
and back in can still be diagnosed later - the same idea as the crash-log
viewer on the Android side.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_MAX_BYTES = 1_000_000
_BACKUP_COUNT = 3
_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def log_file_path() -> Path:
    state_home = Path(os.environ.get("XDG_STATE_HOME", "~/.local/state")).expanduser()
    directory = state_home / "dash-phonecon"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "dashphone.log"


def setup_logging(verbose: bool = False) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT)

    file_handler = RotatingFileHandler(log_file_path(), maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.getLogger(__name__).info("Dash Phone Con starting - logging to %s", log_file_path())


def clear_log_file() -> None:
    """Truncate the current log file in place (keeps rotated backups)."""
    log_file_path().write_text("")
