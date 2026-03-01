"""
Pluggable conversation storage backend.

To add a new backend (e.g. PostgreSQL, DynamoDB), subclass ConversationStore,
implement all abstract methods, and replace the `store` singleton at the bottom
of this module:

    store: ConversationStore = MyDatabaseStore()
"""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TypedDict

from bee.queue import get_redis_connection

SESSION_TTL = 86400  # 24 hours


# ─── Data types ───────────────────────────────────────────────────────────────


class SessionSummary(TypedDict):
    session_id: str
    title: str
    updated_at: str  # ISO 8601


class SessionDetail(TypedDict):
    session_id: str
    title: str
    messages: list[dict]
    updated_at: str


# ─── Abstract interface ────────────────────────────────────────────────────────


class ConversationStore(ABC):
    """Interface for conversation persistence.

    Implementations must be thread-safe (FastAPI may call these concurrently).
    All methods should silently swallow storage errors rather than raising, so
    a storage failure never crashes the chat endpoint.
    """

    @abstractmethod
    def get_messages(self, session_id: str) -> list[dict]:
        """Return the message history for a session, or [] if not found."""

    @abstractmethod
    def get_session(self, session_id: str) -> SessionDetail | None:
        """Return full session detail (including messages), or None if not found."""

    @abstractmethod
    def save(
        self,
        session_id: str,
        user_id: str,
        messages: list[dict],
        title: str,
    ) -> None:
        """Persist messages and upsert the session in the user's session index."""

    @abstractmethod
    def list_sessions(self, user_id: str) -> list[SessionSummary]:
        """Return all sessions for a user, newest-first."""

    @abstractmethod
    def delete_session(self, session_id: str, user_id: str) -> None:
        """Delete a session and remove it from the user's index."""


# ─── Redis implementation ─────────────────────────────────────────────────────


class RedisConversationStore(ConversationStore):
    """Conversation store backed by the existing Redis instance.

    Key layout:
      chat_session:<session_id>  →  JSON {title, messages, updated_at}  TTL 24h
      user_sessions:<user_id>    →  JSON [SessionSummary, ...]           TTL 24h
    """

    _SESSION_PREFIX = "chat_session:"
    _USER_PREFIX = "user_sessions:"

    def _sk(self, session_id: str) -> str:
        return f"{self._SESSION_PREFIX}{session_id}"

    def _uk(self, user_id: str) -> str:
        return f"{self._USER_PREFIX}{user_id}"

    def get_messages(self, session_id: str) -> list[dict]:
        try:
            r = get_redis_connection()
            raw = r.get(self._sk(session_id))
            if raw:
                return json.loads(raw).get("messages", [])
        except Exception:
            pass
        return []

    def get_session(self, session_id: str) -> SessionDetail | None:
        try:
            r = get_redis_connection()
            raw = r.get(self._sk(session_id))
            if raw:
                data = json.loads(raw)
                return SessionDetail(
                    session_id=session_id,
                    title=data.get("title", ""),
                    messages=data.get("messages", []),
                    updated_at=data.get("updated_at", ""),
                )
        except Exception:
            pass
        return None

    def save(
        self,
        session_id: str,
        user_id: str,
        messages: list[dict],
        title: str,
    ) -> None:
        try:
            r = get_redis_connection()
            now = datetime.now(timezone.utc).isoformat()

            session_data = json.dumps({"title": title, "messages": messages, "updated_at": now})
            r.setex(self._sk(session_id), SESSION_TTL, session_data)

            # Upsert session into the user's index
            uk = self._uk(user_id)
            raw_index = r.get(uk)
            index: list[SessionSummary] = json.loads(raw_index) if raw_index else []
            index = [s for s in index if s["session_id"] != session_id]
            index.insert(0, SessionSummary(session_id=session_id, title=title, updated_at=now))
            r.setex(uk, SESSION_TTL, json.dumps(index))
        except Exception:
            pass

    def list_sessions(self, user_id: str) -> list[SessionSummary]:
        try:
            r = get_redis_connection()
            raw = r.get(self._uk(user_id))
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return []

    def delete_session(self, session_id: str, user_id: str) -> None:
        try:
            r = get_redis_connection()
            r.delete(self._sk(session_id))
            uk = self._uk(user_id)
            raw_index = r.get(uk)
            if raw_index:
                index = [s for s in json.loads(raw_index) if s["session_id"] != session_id]
                r.setex(uk, SESSION_TTL, json.dumps(index))
        except Exception:
            pass


# ─── Singleton ────────────────────────────────────────────────────────────────
# Swap this out to use a different backend, e.g.:
#   store: ConversationStore = PostgresConversationStore()

store: ConversationStore = RedisConversationStore()


def new_user_id() -> str:
    return str(uuid.uuid4())
