from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    IDLE = "IDLE"
    WAITING_CLARIFY = "WAITING_CLARIFY"


class ConversationTurn(BaseModel):
    """
    One completed exchange (question -> final answer), recorded server-side in
    Redis so follow-up turns get grounded context: the actual SQL/reasoning that
    was used, not just the rendered `<cite id="sql_X">` markdown shown to the
    user. Previously chat_history was whatever the client resent, which only
    ever contained that rendered text - so a later turn could see `sql_2` cited
    with no way to know what sql_2 actually was.
    """

    user_query: str
    extracted_entities: dict[str, Any] = Field(default_factory=dict)
    generated_sqls: list[dict[str, Any]] = Field(
        default_factory=list, description="Each item: {id, title, reasoning, sql} - the SQL(s) actually used to answer this turn"
    )
    bot_message: str = ""
    had_sql_errors: bool = Field(
        default=False,
        description="True if every generated SQL in this turn failed to execute (e.g. a bad slot value like "
        "campaign_id='5G' caused a type error). When true, the extracted_entities recorded for this turn are NOT "
        "confirmed facts - format_conversation_history() flags them so a later turn doesn't blindly trust and reuse "
        "a value that was never actually validated against the database.",
    )
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_CITE_TAG_RE = re.compile(r'<cite id="[^"]*">(.*?)</cite>', re.DOTALL)


def format_conversation_history(turns: list[ConversationTurn], max_turns: int = 3) -> str:
    """Renders the last `max_turns` server-recorded turns into prompt text -
    each with the user's question, the slots resolved, the SQL(s)/reasoning that
    were actually used, and the final answer (citation tags stripped down to
    their plain value, since `<cite id="sql_X">` is meaningless outside the
    original response and would otherwise dangle in the model's context)."""
    if not turns:
        return ""
    blocks: list[str] = []
    for turn in turns[-max_turns:]:
        lines = [f"user: {turn.user_query}"]
        if turn.extracted_entities:
            if turn.had_sql_errors:
                lines.append(
                    f"  (CẢNH BÁO: câu SQL sinh ra ở lượt này đều bị lỗi khi thực thi - các giá trị dưới đây CHƯA ĐƯỢC XÁC MINH "
                    f"với database, đừng coi là đúng/đủ nếu không chắc chắn, có thể cần hỏi lại người dùng: "
                    f"{json.dumps(turn.extracted_entities, ensure_ascii=False)})"
                )
            else:
                lines.append(f"  (thông tin đã xác định: {json.dumps(turn.extracted_entities, ensure_ascii=False)})")
        for sql in turn.generated_sqls:
            sql_id = sql.get("id", "")
            title = sql.get("title", "")
            reasoning = sql.get("reasoning", "")
            sql_text = sql.get("sql", "")
            reasoning_part = f" - {reasoning}" if reasoning else ""
            lines.append(f"  (đã dùng SQL [{sql_id}] {title}{reasoning_part}:\n  {sql_text})")
        clean_bot_msg = _CITE_TAG_RE.sub(r"\1", turn.bot_message or "")
        lines.append(f"bot: {clean_bot_msg}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


class SessionState(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.IDLE
    current_scenario: str | None = None
    clarify_guideline: str | None = None
    raw_answer_template: str | None = None
    collected_slots: dict[str, Any] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    conversation_history: list[ConversationTurn] = Field(
        default_factory=list, description="Server-managed turn history for this session - the source of truth for follow-up context, not the client-supplied chat_history."
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def reset_to_idle(self) -> None:
        """Resets the in-progress clarify/slot-filling state. Does NOT touch
        conversation_history - that's a separate, longer-lived record of the
        session and should survive across multiple resolved turns."""
        self.status = SessionStatus.IDLE
        self.current_scenario = None
        self.clarify_guideline = None
        self.raw_answer_template = None
        self.collected_slots = {}
        self.missing_slots = []
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def add_turn(self, turn: ConversationTurn, max_turns: int = 10) -> None:
        """Appends a completed turn, keeping only the most recent `max_turns`."""
        self.conversation_history.append(turn)
        if len(self.conversation_history) > max_turns:
            self.conversation_history = self.conversation_history[-max_turns:]
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def clear_history(self) -> None:
        self.conversation_history = []
