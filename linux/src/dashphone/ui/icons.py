"""Tray/app icons, drawn in code instead of shipped as image files.

Why draw instead of ship .svg/.png assets? One function is the single
source of truth for "what does the DashPhoneCon icon look like", so the
tray icon and the installed app icon (used for the .desktop entry, see
packaging/) can never drift out of sync, and there is nothing to keep
track of on disk.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from dashphone.state import CallPhase

_GLYPH = "\u260E"  # ☎

_COLOR_DISCONNECTED = QColor("#9e9e9e")  # grey - not connected to any phone
_COLOR_IDLE = QColor("#1976d2")  # blue - connected, no call
_COLOR_RINGING = QColor("#f57c00")  # amber - incoming call
_COLOR_ACTIVE = QColor("#2e7d32")  # green - call in progress


def render_icon(background: QColor, size: int = 64) -> QIcon:
    """Draw a filled circle with a phone glyph on it and return it as a QIcon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(background)
    painter.setPen(Qt.PenStyle.NoPen)
    margin = max(2, size // 16)
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)

    painter.setPen(QColor("white"))
    font = painter.font()
    font.setPointSize(int(size * 0.42))
    painter.setFont(font)
    painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, _GLYPH)

    painter.end()
    return QIcon(pixmap)


def icon_for_connection_and_state(is_connected: bool, phase: CallPhase) -> QIcon:
    """Mirrors MenuBarIconView.iconName from the macOS app: disconnected always
    wins, otherwise the icon reflects idle/ringing/active."""
    if not is_connected:
        return render_icon(_COLOR_DISCONNECTED)

    return render_icon(
        {
            CallPhase.IDLE: _COLOR_IDLE,
            CallPhase.RINGING: _COLOR_RINGING,
            CallPhase.ACTIVE: _COLOR_ACTIVE,
        }[phase]
    )


def save_app_icon_png(path: str, size: int = 256) -> None:
    """Used once at packaging time to produce the .desktop icon file (see
    build-deb.sh) so the app-menu entry uses the exact same artwork as the
    tray icon."""
    render_icon(_COLOR_IDLE, size=size).pixmap(size, size).save(path, "PNG")
