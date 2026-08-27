from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    IDLE = "IDLE"
    WAITING_CLARIFY = "WAITING_CLARIFY"


class SessionState(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.IDLE
    current_scenario: str | None = None
    clarify_guideline: str | None = None
    raw_answer_template: str | None = None
    collected_slots: dict[str, Any] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def reset_to_idle(self) -> None:
        self.status = SessionStatus.IDLE
        self.current_scenario = None
        self.clarify_guideline = None
        self.raw_answer_template = None
        self.collected_slots = {}
        self.missing_slots = []
        self.updated_at = datetime.now(timezone.utc).isoformat()
