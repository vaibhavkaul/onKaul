"""Web chat endpoints with SSE streaming and pluggable conversation sessions."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, StreamingResponse

from agent.core import agent
from api.chat_runs import RunInProgressError, start_run, stop_run
from api.conversation_store import (
    SESSION_TTL,
    SessionDetail,
    SessionSummary,
    new_user_id,
    store,
)

router = APIRouter()

USER_COOKIE = "onkaul_user_id"
RELAY_POLL_SECONDS = 0.05
COOKIE_MAX_AGE = SESSION_TTL  # refreshed on every chat, like the session TTL


# ─── Request / response models ────────────────────────────────────────────────


class RenameRequest(BaseModel):
    """Rename payload."""

    title: str = Field(min_length=1, max_length=200)


class WebChatRequest(BaseModel):
    """Web chat request payload."""

    message: str = Field(min_length=1, description="User message")
    session_id: str | None = Field(
        default=None,
        description="Session ID to continue; omit to start a new conversation",
    )


# ─── Helper ───────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


@router.patch("/web/sessions/{session_id}", response_model=SessionSummary)
async def rename_session(
    session_id: str,
    payload: RenameRequest,
    user_id: str | None = Cookie(default=None, alias=USER_COOKIE),
):
    """Rename one of the current user's sessions."""
    title = " ".join(payload.title.split())[:200]
    if not title:
        return JSONResponse(status_code=422, content={"detail": "Title cannot be blank"})
    if not user_id or not store.rename_session(session_id, user_id, title):
        return JSONResponse(status_code=404, content={"detail": "Session not found"})
    session = store.get_session(session_id, user_id)
    return SessionSummary(session_id=session_id, title=title, updated_at=session["updated_at"])


@router.post("/web/sessions/{session_id}/stop", status_code=204)
async def stop_session_run(
    session_id: str,
    user_id: str | None = Cookie(default=None, alias=USER_COOKIE),
):
    """Stop the current user's running turn; the partial reply is saved as interrupted."""
    if not user_id or not stop_run(session_id, user_id):
        return JSONResponse(status_code=404, content={"detail": "No running reply"})


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
      data: {"type": "done", "status": "done|interrupted"}  — turn finished
      data: {"type": "error",    "content": "<message>"}   — on failure

    The turn runs independently of this connection (see api.chat_runs): closing
    it does not cancel the reply; POST /web/sessions/{id}/stop does. Returns
    409 while a previous turn in the same session is still running.
    """
    resolved_user_id = user_id or new_user_id()

    session_id = payload.session_id or str(uuid.uuid4())
    if payload.session_id:
        owner = store.session_owner(session_id)
        if owner is not None and owner != resolved_user_id:
            # Someone else's session: behave exactly as if it did not exist.
            return JSONResponse(status_code=404, content={"detail": "Session not found"})
    existing = store.get_session(session_id, resolved_user_id) if payload.session_id else None
    history = existing["messages"] if existing else []

    # New sessions are titled from the first message; existing ones keep their
    # title, which the user may have renamed.
    title = existing["title"] if existing and existing["title"] else payload.message[:60].strip()

    with_question = history + [{"role": "user", "content": payload.message, "ts": _now()}]
    try:
        run = start_run(
            session_id=session_id,
            user_id=resolved_user_id,
            title=title,
            messages=with_question,
            stream=lambda: agent.investigate_stream(
                payload.message,
                thread_history=history or None,
                event_context={"channel": "web", "session_id": session_id},
            ),
        )
    except RunInProgressError:
        return JSONResponse(
            status_code=409,
            content={"detail": "Still answering the previous message in this conversation"},
        )

    async def relay() -> AsyncIterator[str]:
        # Only relays the run's output; if the client goes away the run keeps
        # going and saves the reply itself.
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
        sent = 0
        while True:
            finished = run.finished.is_set()
            chunks = run.chunks[sent:]
            for chunk in chunks:
                yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
            sent += len(chunks)
            if finished and sent == len(run.chunks):
                break
            await asyncio.sleep(RELAY_POLL_SECONDS)
        if run.status == "error":
            yield f"data: {json.dumps({'type': 'error', 'content': run.error or 'error'})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'done', 'status': run.status})}\n\n"

    response = StreamingResponse(
        relay(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
    # Always (re)set the cookie so its expiry slides along with the session TTL.
    return _cookie_response(response, resolved_user_id)
