from __future__ import annotations

import contextvars
import logging
import os
import re
import threading
import time
import uuid

# Holds the current request's ID for the duration of one /api/chat or
# /api/chat/stream call. Set once at the top of the endpoint (see endpoints.py)
# so every log line emitted anywhere in the pipeline for that request - endpoint,
# chat_service, stream_service, llm_client - can be routed to the same file,
# instead of everything piling up into one shared chat_pipeline.log.
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

# Holds the current request's session ID, resolved once up-front in
# endpoints.py (generating a new one if the client didn't send one) - so
# per-request logs/traces can be grouped by session: logs/requests/<session_id>/<request_id>.log
session_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("session_id", default=None)

# Holds the current request's client IP (set alongside request_id in
# endpoints.py) so it can be logged into the per-request log file and attached
# to the Monitor trace, without threading it through every function signature.
client_ip_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("client_ip", default=None)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]")


def new_request_id() -> str:
    return f"req-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"


def get_or_create_request_id() -> str:
    """Returns the request_id set for the current context, creating one if none exists yet."""
    rid = request_id_var.get()
    if not rid:
        rid = new_request_id()
        request_id_var.set(rid)
    return rid


def get_or_create_session_id(explicit: str | None = None) -> str:
    """
    Resolves the session_id for the current request context: uses `explicit` if
    given (e.g. the client sent one), otherwise reuses whatever is already set
    in this context, otherwise creates a new one. Idempotent - safe to call from
    both the endpoint (first) and chat_service/stream_service (which reuse the
    same value the endpoint already resolved).
    """
    if explicit:
        session_id_var.set(explicit)
        return explicit
    sid = session_id_var.get()
    if not sid:
        sid = str(uuid.uuid4())
        session_id_var.set(sid)
    return sid


def get_client_ip() -> str:
    """Returns the client IP set for the current request context, or 'unknown' if none was set."""
    return client_ip_var.get() or "unknown"


class PerRequestFileHandler(logging.Handler):
    """
    Writes each request's pipeline log lines to its own file, grouped by
    session, under `logs_dir`: <logs_dir>/<session_id>/<request_id>.log -
    instead of every request's logs piling up together into one shared file
    (or previously, a flat file per request with no session grouping), which
    made following one conversation across multiple turns painful.

    Log records emitted outside of a request context (no request_id set) are
    dropped by this handler; they still go to stdout via the root logger as usual.
    """

    def __init__(self, logs_dir: str, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self.logs_dir = logs_dir
        os.makedirs(logs_dir, exist_ok=True)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        rid = request_id_var.get()
        if not rid:
            return
        safe_rid = _SAFE_NAME_RE.sub("_", rid)
        safe_sid = _SAFE_NAME_RE.sub("_", session_id_var.get() or "no-session")
        dir_path = os.path.join(self.logs_dir, safe_sid)
        path = os.path.join(dir_path, f"{safe_rid}.log")
        try:
            msg = self.format(record)
            with self._lock:
                os.makedirs(dir_path, exist_ok=True)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
        except Exception:
            self.handleError(record)
