"""Pure call-state data. No Qt, no networking - just "what is the call doing right now".

Keeping this file free of Qt/Widget imports means it can be unit tested
without a display, and reused as-is if the UI toolkit ever changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto


class CallPhase(Enum):
    IDLE = auto()
    RINGING = auto()
    ACTIVE = auto()


@dataclass(frozen=True)
class CallState:
    phase: CallPhase
    number: str = ""
    name: str = ""
    start_time: datetime | None = field(default=None)

    @staticmethod
    def idle() -> "CallState":
        return CallState(CallPhase.IDLE)

    @staticmethod
    def ringing(number: str, name: str) -> "CallState":
        return CallState(CallPhase.RINGING, number=number, name=name)

    @staticmethod
    def active(start_time: datetime) -> "CallState":
        return CallState(CallPhase.ACTIVE, start_time=start_time)

    @property
    def display_name(self) -> str:
        return self.name if self.name else "Unknown"
