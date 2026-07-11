"""The incoming-call popup: a small always-on-top card in the corner of the
screen with the caller's name/number and Answer/Decline buttons.

Mirrors CallPopupWindow.swift + CallPopupView.swift from the macOS app:
same corner placement, same Enter=Answer / Escape=Decline shortcuts.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

_CARD_STYLE = """
#card {
    background-color: #2b2b2e;
    border: 1px solid #444;
    border-radius: 14px;
}
QLabel {
    color: #f0f0f0;
}
#callerName {
    font-size: 15px;
    font-weight: 600;
}
#callerNumber {
    font-size: 12px;
    color: #b0b0b0;
}
#heading {
    font-size: 13px;
    font-weight: 600;
    color: #f0f0f0;
}
QPushButton {
    border: none;
    border-radius: 8px;
    padding: 8px 0;
    font-weight: 600;
    color: white;
}
#answerButton { background-color: #2e7d32; }
#answerButton:hover { background-color: #388e3c; }
#declineButton { background-color: #c62828; }
#declineButton:hover { background-color: #d32f2f; }
"""

_SCREEN_MARGIN_PX = 16


class CallPopupWindow(QWidget):
    def __init__(
        self,
        on_answer: Callable[[], None],
        on_decline: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_answer = on_answer
        self._on_decline = on_decline

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(300)
        self._drag_offset: QPoint | None = None

        self._caller_name_label = QLabel()
        self._caller_name_label.setObjectName("callerName")
        self._caller_number_label = QLabel()
        self._caller_number_label.setObjectName("callerNumber")

        self._build_layout()
        self.setStyleSheet(_CARD_STYLE)

    def show_call(self, number: str, name: str) -> None:
        self._caller_name_label.setText(name if name else "Unknown")
        self._caller_number_label.setText(number)
        self.adjustSize()
        self._move_to_top_right()
        self.show()
        self.raise_()
        self.activateWindow()

    # -- drag to reposition anywhere on screen --

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    # -- layout --

    def _build_layout(self) -> None:
        heading = QLabel(f"\u260E Incoming Call")
        heading.setObjectName("heading")

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #444;")

        self._caller_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._caller_number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        answer_button = QPushButton("Answer")
        answer_button.setObjectName("answerButton")
        answer_button.clicked.connect(self._answer)

        decline_button = QPushButton("Decline")
        decline_button.setObjectName("declineButton")
        decline_button.clicked.connect(self._decline)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)
        button_row.addWidget(answer_button)
        button_row.addWidget(decline_button)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 20)
        card_layout.setSpacing(10)
        card_layout.addWidget(heading, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(divider)
        card_layout.addWidget(self._caller_name_label)
        card_layout.addWidget(self._caller_number_label)
        card_layout.addSpacing(4)
        card_layout.addLayout(button_row)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(card)

    def _move_to_top_right(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        x = available.right() - self.width() - _SCREEN_MARGIN_PX
        y = available.top() + _SCREEN_MARGIN_PX
        self.move(x, y)

    # -- keyboard shortcuts: Enter = Answer, Escape = Decline --

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._answer()
        elif event.key() == Qt.Key.Key_Escape:
            self._decline()
        else:
            super().keyPressEvent(event)

    # -- button/shortcut actions --

    def _answer(self) -> None:
        self._on_answer()
        self.close()

    def _decline(self) -> None:
        self._on_decline()
        self.close()


_BAR_STYLE = """
#bar {
    background-color: #2b2b2e;
    border: 1px solid #444;
    border-radius: 14px;
}
QLabel { color: #f0f0f0; }
#callerName { font-size: 14px; font-weight: 600; }
#callTimer { font-size: 12px; color: #b0b0b0; }
QPushButton {
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
    color: white;
    background-color: #444;
}
QPushButton:hover { background-color: #505050; }
#muteButton:checked { background-color: #5e9bff; }
#muteButton:checked:hover { background-color: #6ea6ff; }
#hangupButton { background-color: #c62828; }
#hangupButton:hover { background-color: #d32f2f; }
"""


class InCallBar(QWidget):
    """Persistent floating bar shown for the whole life of an active call -
    caller name, a live MM:SS timer, Mute, and Hang Up. Same frameless
    always-on-top top-right card treatment as CallPopupWindow so it reads
    as one consistent "phone" surface instead of two different widget
    styles, since Ubuntu/GNOME has no equivalent of macOS's live Continuity
    call bar built into the system notification center to hook into.
    """

    def __init__(
        self,
        on_toggle_mute: Callable[[], None],
        on_hangup: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_toggle_mute = on_toggle_mute
        self._on_hangup = on_hangup

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(300)
        self._drag_offset: QPoint | None = None

        self._name_label = QLabel()
        self._name_label.setObjectName("callerName")
        self._timer_label = QLabel("00:00")
        self._timer_label.setObjectName("callTimer")

        self._mute_button = QPushButton("\U0001f507 Mute")
        self._mute_button.setObjectName("muteButton")
        self._mute_button.setCheckable(True)
        self._mute_button.clicked.connect(self._on_toggle_mute)

        hangup_button = QPushButton("\u260E Hang Up")
        hangup_button.setObjectName("hangupButton")
        hangup_button.clicked.connect(self._on_hangup)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addWidget(self._mute_button)
        button_row.addWidget(hangup_button)

        bar = QFrame()
        bar.setObjectName("bar")
        bar_layout = QVBoxLayout(bar)
        bar_layout.setContentsMargins(18, 14, 18, 16)
        bar_layout.setSpacing(8)
        bar_layout.addWidget(self._name_label, alignment=Qt.AlignmentFlag.AlignCenter)
        bar_layout.addWidget(self._timer_label, alignment=Qt.AlignmentFlag.AlignCenter)
        bar_layout.addLayout(button_row)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(bar)

        self.setStyleSheet(_BAR_STYLE)

    def show_call(self, name: str, number: str) -> None:
        self._name_label.setText(name or number or "Unknown")
        self._mute_button.setChecked(False)
        self.adjustSize()
        self._move_to_top_right()
        self.show()
        self.raise_()

    def set_muted(self, muted: bool) -> None:
        self._mute_button.setChecked(muted)

    def set_elapsed_text(self, text: str) -> None:
        self._timer_label.setText(text)

    # -- drag to reposition anywhere on screen --

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def _move_to_top_right(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        x = available.right() - self.width() - _SCREEN_MARGIN_PX
        y = available.top() + _SCREEN_MARGIN_PX
        self.move(x, y)
