from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RequestTrace(BaseModel):
    request_id: str
    session_id: str
    query: str
    timestamp: float = Field(default_factory=time.time)
    status: str = "running"  # "running", "completed", "error"
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    steps: list[dict[str, Any]] = Field(default_factory=list)
    llm_traces: list[dict[str, Any]] = Field(default_factory=list)
    sql_queries: list[dict[str, Any]] = Field(default_factory=list)
    final_response: dict[str, Any] | None = None
    error: str | None = None


class MonitorService:
    """
    In-memory and Redis backed execution monitor service.
    Maintains the list of recent query traces and broadcasts realtime events to admin subscribers.
    """

    def __init__(self, max_traces: int = 100) -> None:
        self.max_traces = max_traces
        self._traces: dict[str, RequestTrace] = {}
        self._ordered_ids: list[str] = []
        self._subscribers: list[asyncio.Queue] = []

    def start_trace(self, request_id: str, session_id: str, query: str) -> RequestTrace:
        trace = RequestTrace(
            request_id=request_id,
            session_id=session_id,
            query=query,
            timestamp=time.time(),
            status="running",
        )
        self._traces[request_id] = trace
        self._ordered_ids.insert(0, request_id)
        if len(self._ordered_ids) > self.max_traces:
            oldest = self._ordered_ids.pop()
            self._traces.pop(oldest, None)

        self._broadcast({
            "event": "trace_started",
            "request_id": request_id,
            "session_id": session_id,
            "query": query,
            "timestamp": trace.timestamp,
        })
        return trace

    def record_step(self, request_id: str, step_data: dict[str, Any]) -> None:
        trace = self._traces.get(request_id)
        if trace:
            trace.steps.append(step_data)
            self._broadcast({
                "event": "step_update",
                "request_id": request_id,
                "step": step_data,
            })

    def record_llm_trace(self, request_id: str, llm_trace: dict[str, Any]) -> None:
        trace = self._traces.get(request_id)
        if trace:
            trace.llm_traces.append(llm_trace)
            trace.prompt_tokens += llm_trace.get("prompt_tokens", 0)
            trace.completion_tokens += llm_trace.get("completion_tokens", 0)
            trace.total_tokens += llm_trace.get("total_tokens", 0)
            self._broadcast({
                "event": "llm_update",
                "request_id": request_id,
                "llm_trace": llm_trace,
                "total_tokens": trace.total_tokens,
            })

    def record_sql(self, request_id: str, sql_item: dict[str, Any]) -> None:
        trace = self._traces.get(request_id)
        if trace:
            trace.sql_queries.append(sql_item)
            self._broadcast({
                "event": "sql_update",
                "request_id": request_id,
                "sql_query": sql_item,
            })

    def finish_trace(
        self,
        request_id: str,
        final_response: dict[str, Any] | None = None,
        total_latency_ms: float = 0.0,
        error: str | None = None,
    ) -> None:
        trace = self._traces.get(request_id)
        if trace:
            trace.status = "error" if error else "completed"
            trace.total_latency_ms = total_latency_ms
            trace.final_response = final_response
            trace.error = error
            self._broadcast({
                "event": "trace_finished",
                "request_id": request_id,
                "status": trace.status,
                "total_latency_ms": total_latency_ms,
                "total_tokens": trace.total_tokens,
                "final_response": final_response,
                "error": error,
            })

    def list_traces(self) -> list[dict[str, Any]]:
        """Returns summary list of recent traces (latest first)."""
        summaries = []
        for req_id in self._ordered_ids:
            trace = self._traces.get(req_id)
            if trace:
                summaries.append({
                    "request_id": trace.request_id,
                    "session_id": trace.session_id,
                    "query": trace.query,
                    "timestamp": trace.timestamp,
                    "status": trace.status,
                    "total_latency_ms": trace.total_latency_ms,
                    "total_tokens": trace.total_tokens,
                    "prompt_tokens": trace.prompt_tokens,
                    "completion_tokens": trace.completion_tokens,
                    "sql_count": len(trace.sql_queries),
                    "steps_count": len(trace.steps),
                })
        return summaries

    def get_trace_detail(self, request_id: str) -> dict[str, Any] | None:
        trace = self._traces.get(request_id)
        return trace.model_dump() if trace else None

    def _broadcast(self, message: dict[str, Any]) -> None:
        dead_queues = []
        for q in self._subscribers:
            try:
                q.put_nowait(message)
            except Exception:
                dead_queues.append(q)
        for q in dead_queues:
            if q in self._subscribers:
                self._subscribers.remove(q)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """SSE generator for Admin Monitor subscriber."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.append(queue)
        try:
            # Send initial ping & connection greeting
            init_payload = json.dumps({"event": "connected", "traces_count": len(self._traces)}, ensure_ascii=False)
            yield f"event: monitor_connected\ndata: {init_payload}\n\n"

            while True:
                data = await queue.get()
                json_str = json.dumps(data, ensure_ascii=False, default=str)
                yield f"event: monitor_event\ndata: {json_str}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in self._subscribers:
                self._subscribers.remove(queue)
