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
    status: str  # "streaming" | "done" | "error" | "interrupted"


# ─── Abstract interface ────────────────────────────────────────────────────────


class ConversationStore(ABC):
    """Interface for conversation persistence.

    Every session belongs to the user who created it. Reads, writes and deletes
    take the caller's ``user_id`` and must act only on that user's sessions —
    a session owned by someone else behaves as if it did not exist.

    Implementations must be thread-safe (FastAPI may call these concurrently).
    All methods should silently swallow storage errors rather than raising, so
    a storage failure never crashes the chat endpoint.
    """

    @abstractmethod
    def session_owner(self, session_id: str) -> str | None:
        """Return the owning user_id, or None if the session does not exist."""

    @abstractmethod
    def get_messages(self, session_id: str, user_id: str) -> list[dict]:
        """Return the user's message history for a session, or [] if not theirs."""

    @abstractmethod
    def get_session(self, session_id: str, user_id: str) -> SessionDetail | None:
        """Return full session detail if the user owns it, else None."""

    @abstractmethod
    def save(
        self,
        session_id: str,
        user_id: str,
        messages: list[dict],
        title: str,
        status: str = "done",
    ) -> bool:
        """Persist messages and upsert the user's session index.

        Returns False (and writes nothing) if another user owns the session.
        """

    @abstractmethod
    def list_sessions(self, user_id: str) -> list[SessionSummary]:
        """Return all sessions for a user, newest-first."""

    @abstractmethod
    def delete_session(self, session_id: str, user_id: str) -> None:
        """Delete the user's session (no-op if they do not own it)."""


# ─── Redis implementation ─────────────────────────────────────────────────────


class RedisConversationStore(ConversationStore):
    """Conversation store backed by the existing Redis instance.

    Key layout:
      chat_session:<session_id>  →  JSON {user_id, title, messages, status, updated_at}  TTL 24h
      user_sessions:<user_id>    →  JSON [SessionSummary, ...]           TTL 24h
    """

    _SESSION_PREFIX = "chat_session:"
    _USER_PREFIX = "user_sessions:"

    def _sk(self, session_id: str) -> str:
        return f"{self._SESSION_PREFIX}{session_id}"

    def _uk(self, user_id: str) -> str:
        return f"{self._USER_PREFIX}{user_id}"

    def _load(self, session_id: str) -> dict | None:
        try:
            raw = get_redis_connection().get(self._sk(session_id))
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def _load_owned(self, session_id: str, user_id: str) -> dict | None:
        data = self._load(session_id)
        if data and user_id and data.get("user_id") == user_id:
            return data
        return None

    def session_owner(self, session_id: str) -> str | None:
        data = self._load(session_id)
        # Sessions saved before ownership was recorded have no owner and
        # cannot be claimed; they expire with the TTL.
        return (data.get("user_id") or "") if data is not None else None

    def get_messages(self, session_id: str, user_id: str) -> list[dict]:
        data = self._load_owned(session_id, user_id)
        return data.get("messages", []) if data else []

    def get_session(self, session_id: str, user_id: str) -> SessionDetail | None:
        data = self._load_owned(session_id, user_id)
        if not data:
            return None
        return SessionDetail(
            session_id=session_id,
            title=data.get("title", ""),
            messages=data.get("messages", []),
            updated_at=data.get("updated_at", ""),
            status=data.get("status", "done"),
        )

    def save(
        self,
        session_id: str,
        user_id: str,
        messages: list[dict],
        title: str,
        status: str = "done",
    ) -> bool:
        try:
            owner = self.session_owner(session_id)
            if owner is not None and owner != user_id:
                return False

            r = get_redis_connection()
            now = datetime.now(timezone.utc).isoformat()
            session_data = json.dumps(
                {
                    "user_id": user_id,
                    "title": title,
                    "messages": messages,
                    "status": status,
                    "updated_at": now,
                }
            )
            r.setex(self._sk(session_id), SESSION_TTL, session_data)

            # Upsert session into the user's index
            uk = self._uk(user_id)
            raw_index = r.get(uk)
            index: list[SessionSummary] = json.loads(raw_index) if raw_index else []
            index = [s for s in index if s["session_id"] != session_id]
            index.insert(0, SessionSummary(session_id=session_id, title=title, updated_at=now))
            r.setex(uk, SESSION_TTL, json.dumps(index))
            return True
        except Exception:
            return False

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
            if self._load_owned(session_id, user_id):
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
