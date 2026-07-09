#!/usr/bin/env python3
"""Build-time helper: renders the installed app icon (used by the .desktop
entry) using the exact same drawing code as the live tray icon, so the two
can never drift apart. Not installed - only used by build-deb.sh.
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QGuiApplication

from dashphone.ui.icons import save_app_icon_png


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} <output-png-path>")

    # QPixmap/QPainter need a Qt application instance to exist, even for a
    # one-off offscreen render with no window.
    app = QGuiApplication(sys.argv[:1])
    save_app_icon_png(sys.argv[1])
    del app


if __name__ == "__main__":
    main()
