"""The incoming-call popup: a small always-on-top card in the corner of the
screen with the caller's name/number and Answer/Decline buttons.

Mirrors CallPopupWindow.swift + CallPopupView.swift from the macOS app:
same corner placement, same Enter=Answer / Escape=Decline shortcuts.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent
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
