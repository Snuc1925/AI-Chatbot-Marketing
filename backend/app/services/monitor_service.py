from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, AsyncGenerator
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]")


class RequestTrace(BaseModel):
    request_id: str
    session_id: str
    query: str
    client_ip: str = "unknown"
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
    In-memory execution monitor service that also persists each finished trace to
    disk, grouped by session - <traces_dir>/<session_id>/<request_id>.json - and
    reloads the most recent ones on startup - so the Monitor's chat/execution
    history survives a backend restart instead of being wiped every time.
    Maintains the list of recent query traces and broadcasts realtime events to admin subscribers.
    """

    def __init__(self, max_traces: int = 100, traces_dir: str | None = None) -> None:
        self.max_traces = max_traces
        self.traces_dir = traces_dir
        self._traces: dict[str, RequestTrace] = {}
        self._ordered_ids: list[str] = []
        self._subscribers: list[asyncio.Queue] = []
        if self.traces_dir:
            os.makedirs(self.traces_dir, exist_ok=True)
            self._load_persisted_traces()

    def _trace_file_path(self, session_id: str, request_id: str) -> str | None:
        if not self.traces_dir:
            return None
        safe_sid = _SAFE_NAME_RE.sub("_", session_id or "no-session")
        safe_rid = _SAFE_NAME_RE.sub("_", request_id)
        return os.path.join(self.traces_dir, safe_sid, f"{safe_rid}.json")

    def _load_persisted_traces(self) -> None:
        """Restores the most recent finished traces from disk on startup (walks
        the <traces_dir>/<session_id>/ subfolders)."""
        found: list[str] = []
        for root, _dirs, files in os.walk(self.traces_dir):
            for fname in files:
                if fname.endswith(".json"):
                    found.append(os.path.join(root, fname))

        # Newest first, by file mtime (a proxy for finish_trace() write time)
        found.sort(key=os.path.getmtime, reverse=True)

        loaded = 0
        for full_path in found[: self.max_traces]:
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                trace = RequestTrace(**data)
                self._traces[trace.request_id] = trace
                self._ordered_ids.append(trace.request_id)
                loaded += 1
            except Exception as e:
                logger.warning("Failed to load persisted trace %s: %s", full_path, e)

        if loaded:
            logger.info("Restored %d persisted trace(s) from %s", loaded, self.traces_dir)

    def _persist_trace(self, trace: RequestTrace) -> None:
        path = self._trace_file_path(trace.session_id, trace.request_id)
        if not path:
            return
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(trace.model_dump(), f, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning("Failed to persist trace %s: %s", trace.request_id, e)

    def start_trace(self, request_id: str, session_id: str, query: str, client_ip: str = "unknown") -> RequestTrace:
        trace = RequestTrace(
            request_id=request_id,
            session_id=session_id,
            query=query,
            client_ip=client_ip,
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
            "client_ip": client_ip,
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
            self._persist_trace(trace)
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
                    "client_ip": trace.client_ip,
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
