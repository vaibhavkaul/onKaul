"""Web chat endpoint with SSE streaming and Redis-backed conversation sessions."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator

from fastapi import APIRouter
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from agent.core import agent
from bee.queue import get_redis_connection

router = APIRouter()

SESSION_TTL = 86400  # 24 hours
SESSION_KEY_PREFIX = "chat_session:"


def _session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def _load_history(session_id: str) -> list[dict]:
    """Load conversation history from Redis. Returns empty list on miss or error."""
    try:
        r = get_redis_connection()
        raw = r.get(_session_key(session_id))
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return []


def _save_history(session_id: str, history: list[dict]) -> None:
    """Persist conversation history to Redis with TTL. Silently ignores errors."""
    try:
        r = get_redis_connection()
        r.setex(_session_key(session_id), SESSION_TTL, json.dumps(history))
    except Exception:
        pass


class WebChatRequest(BaseModel):
    """Web chat request payload."""

    message: str = Field(min_length=1, description="User message")
    session_id: str | None = Field(default=None, description="Session ID to continue; omit to start a new conversation")


@router.post("/web/chat/stream")
async def web_chat_stream(payload: WebChatRequest) -> StreamingResponse:
    """
    Stream a chat response as Server-Sent Events.

    Creates a new Redis-backed session if session_id is omitted, or continues
    an existing one. The SSE stream emits typed JSON events:

      data: {"type": "session", "session_id": "<uuid>"}   — first event, always
      data: {"type": "text",    "content": "<chunk>"}      — streamed text
      data: {"type": "done"}                               — stream finished
      data: {"type": "error",   "content": "<message>"}   — on failure
    """
    session_id = payload.session_id or str(uuid.uuid4())
    history = _load_history(session_id) if payload.session_id else []

    def generate() -> Iterator[str]:
        # Always send session_id first so the client can persist it
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        collected: list[str] = []
        try:
            for chunk in agent.investigate_stream(
                payload.message,
                thread_history=history or None,
            ):
                if chunk:
                    collected.append(chunk)
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            return

        # Persist updated history (only clean text turns — no tool call objects)
        full_response = "".join(collected)
        updated_history = history + [
            {"role": "user", "content": payload.message},
            {"role": "assistant", "content": full_response},
        ]
        _save_history(session_id, updated_history)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Prevent nginx from buffering SSE
        },
    )
