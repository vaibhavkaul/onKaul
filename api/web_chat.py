"""Web chat endpoints with SSE streaming and pluggable conversation sessions."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Cookie
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, StreamingResponse

from agent.core import agent
from api.conversation_store import SessionDetail, SessionSummary, new_user_id, store

router = APIRouter()

USER_COOKIE = "onkaul_user_id"
COOKIE_MAX_AGE = 86400  # 24 hours — matches Redis TTL; refreshed on every chat


# ─── Request / response models ────────────────────────────────────────────────


class WebChatRequest(BaseModel):
    """Web chat request payload."""

    message: str = Field(min_length=1, description="User message")
    session_id: str | None = Field(
        default=None,
        description="Session ID to continue; omit to start a new conversation",
    )


# ─── Helper ───────────────────────────────────────────────────────────────────


def _cookie_response(base: StreamingResponse | JSONResponse, user_id: str):
    """Attach the user_id cookie to a response."""
    base.set_cookie(
        USER_COOKIE,
        user_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,  # the UI never reads it; keep it away from scripts
        samesite="lax",
    )
    return base


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/web/sessions", response_model=list[SessionSummary])
async def list_sessions(
    user_id: str | None = Cookie(default=None, alias=USER_COOKIE),
):
    """Return all sessions for the current user, newest first."""
    if not user_id:
        return []
    return store.list_sessions(user_id)


@router.get("/web/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    user_id: str | None = Cookie(default=None, alias=USER_COOKIE),
):
    """Return the full message history for one of the current user's sessions."""
    session = store.get_session(session_id, user_id) if user_id else None
    if session is None:
        return JSONResponse(status_code=404, content={"detail": "Session not found"})
    return session


@router.delete("/web/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user_id: str | None = Cookie(default=None, alias=USER_COOKIE),
):
    """Delete a session and remove it from the user's session list."""
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    store.delete_session(session_id, user_id)


@router.post("/web/chat/stream")
async def web_chat_stream(
    payload: WebChatRequest,
    user_id: str | None = Cookie(default=None, alias=USER_COOKIE),
) -> StreamingResponse:
    """
    Stream a chat response as Server-Sent Events.

    Creates or refreshes a user_id cookie on first visit. SSE event types:

      data: {"type": "session",  "session_id": "<uuid>"}   — first event, always
      data: {"type": "text",     "content": "<chunk>"}      — streamed text chunk
      data: {"type": "done"}                                — stream complete
      data: {"type": "error",    "content": "<message>"}   — on failure
    """
    resolved_user_id = user_id or new_user_id()

    session_id = payload.session_id or str(uuid.uuid4())
    if payload.session_id:
        owner = store.session_owner(session_id)
        if owner is not None and owner != resolved_user_id:
            # Someone else's session: behave exactly as if it did not exist.
            return JSONResponse(status_code=404, content={"detail": "Session not found"})
    history = store.get_messages(session_id, resolved_user_id) if payload.session_id else []

    # Derive session title from the first user message in the session
    title = payload.message[:60].strip()
    if history:
        for msg in history:
            if msg.get("role") == "user":
                title = msg["content"][:60].strip()
                break

    with_question = history + [{"role": "user", "content": payload.message}]
    # Save the question before answering so a crash or disconnect never loses it.
    store.save(session_id, resolved_user_id, with_question, title, status="streaming")

    def generate() -> Iterator[str]:
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        collected: list[str] = []
        status = "error"
        error: str | None = None
        try:
            for chunk in agent.investigate_stream(
                payload.message,
                thread_history=history or None,
                event_context={"channel": "web", "session_id": session_id},
            ):
                if chunk:
                    collected.append(chunk)
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
            status = "done"
        except GeneratorExit:
            status = "interrupted"  # client went away mid-stream
            raise
        except Exception as e:
            error = str(e)
        finally:
            reply = "".join(collected)
            messages = with_question + ([{"role": "assistant", "content": reply}] if reply else [])
            store.save(session_id, resolved_user_id, messages, title, status=status)

        if error is not None:
            yield f"data: {json.dumps({'type': 'error', 'content': error})}\n\n"
            return
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    response = StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
    # Always (re)set the cookie so its expiry slides along with the session TTL.
    return _cookie_response(response, resolved_user_id)
