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


class PerRequestFileHandler(logging.Handler):
    """
    Writes each request's pipeline log lines to its own file under `logs_dir`,
    named after the current request_id (see request_id_var) - instead of every
    request's logs piling up together into one shared file, which made debugging
    a single request painful.

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
        safe_name = _SAFE_NAME_RE.sub("_", rid)
        path = os.path.join(self.logs_dir, f"{safe_name}.log")
        try:
            msg = self.format(record)
            with self._lock:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
        except Exception:
            self.handleError(record)
