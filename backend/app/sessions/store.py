from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any
import redis

from app.sessions.models import SessionState, SessionStatus

logger = logging.getLogger(__name__)


class BaseSessionStore(ABC):
    @abstractmethod
    def get(self, session_id: str) -> SessionState:
        """Get existing session state or return a new IDLE session state."""
        raise NotImplementedError

    @abstractmethod
    def save(self, state: SessionState) -> None:
        """Persist session state."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, session_id: str) -> None:
        """Delete session state."""
        raise NotImplementedError


class RedisSessionStore(BaseSessionStore):
    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        password: str | None = None,
        ttl_seconds: int = 1800,
        key_prefix: str = "chat_session:",
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self.client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
            socket_timeout=5.0,
        )
        self._test_connection()

    def _test_connection(self) -> None:
        try:
            self.client.ping()
            logger.info("Connected successfully to Redis at %s:%s", self.client.connection_pool.connection_kwargs.get("host"), self.client.connection_pool.connection_kwargs.get("port"))
        except Exception as e:
            logger.warning("Could not ping Redis (will retry on operations): %s", e)

    def _format_key(self, session_id: str) -> str:
        return f"{self.key_prefix}{session_id}"

    def get(self, session_id: str) -> SessionState:
        key = self._format_key(session_id)
        try:
            raw_data = self.client.get(key)
            if raw_data:
                parsed = json.loads(raw_data)
                return SessionState(**parsed)
        except Exception as e:
            logger.error("Error reading session '%s' from Redis: %s", session_id, e)

        # Default new session state
        return SessionState(session_id=session_id, status=SessionStatus.IDLE)

    def save(self, state: SessionState) -> None:
        key = self._format_key(state.session_id)
        try:
            serialized = state.model_dump_json()
            self.client.set(key, serialized, ex=self.ttl_seconds)
        except Exception as e:
            logger.error("Error saving session '%s' to Redis: %s", state.session_id, e)

    def delete(self, session_id: str) -> None:
        key = self._format_key(session_id)
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error("Error deleting session '%s' from Redis: %s", session_id, e)


class InMemorySessionStore(BaseSessionStore):
    """Fallback in-memory store for local testing or standalone use."""

    def __init__(self) -> None:
        self._store: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        if session_id in self._store:
            return self._store[session_id]
        new_state = SessionState(session_id=session_id, status=SessionStatus.IDLE)
        self._store[session_id] = new_state
        return new_state

    def save(self, state: SessionState) -> None:
        self._store[state.session_id] = state

    def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)
