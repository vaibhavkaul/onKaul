"""Web chat turns that run independently of the HTTP connection.

A turn runs in its own thread: it drives the agent stream, collects the reply
and saves the session when it ends. The SSE response only relays chunks, so a
closed tab or dropped connection never cancels or loses a reply. Only an
explicit stop cancels a run, and it takes effect immediately: the partial reply
is saved and the session freed even if the model is mid-thought; the thread
exits quietly once the provider yields again.

The final save happens exactly once (``_finalize``) and keeps the session's
current title, so a rename made while the reply was streaming is not undone.

Runs are tracked in-process; onKaul serves web chat from a single API process.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone

from api.conversation_store import store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChatRun:
    session_id: str
    user_id: str
    title: str
    messages: list[dict]  # history including the new question
    chunks: list[str] = field(default_factory=list)
    status: str = "streaming"  # -> done | error | interrupted
    error: str | None = None
    finished: threading.Event = field(default_factory=threading.Event)
    cancel: threading.Event = field(default_factory=threading.Event)
    _finalize_lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def reply(self) -> str:
        return "".join(self.chunks)


_active: dict[str, ChatRun] = {}
_lock = threading.Lock()


class RunInProgressError(Exception):
    """The session already has a turn running."""


def active_run(session_id: str) -> ChatRun | None:
    with _lock:
        return _active.get(session_id)


def start_run(
    *,
    session_id: str,
    user_id: str,
    title: str,
    messages: list[dict],
    stream: Callable[[], Iterator[str]],
) -> ChatRun:
    """Save the question and start answering it in a background thread."""
    run = ChatRun(session_id=session_id, user_id=user_id, title=title, messages=messages)
    with _lock:
        if session_id in _active:
            raise RunInProgressError(session_id)
        _active[session_id] = run
    # Save the question first so a crash never loses it.
    store.save(session_id, user_id, messages, title, status="streaming")
    threading.Thread(
        target=_drive, args=(run, stream), name=f"chat-run-{session_id[:8]}", daemon=True
    ).start()
    return run


def stop_run(session_id: str, user_id: str) -> bool:
    """Ask the user's running turn to stop. Returns False if there is none."""
    run = active_run(session_id)
    if run is None or run.user_id != user_id:
        return False
    run.cancel.set()
    _finalize(run, "interrupted")
    return True


def _finalize(run: ChatRun, status: str, error: str | None = None) -> None:
    """Save the turn and release the session — once, whoever gets here first."""
    with run._finalize_lock:
        if run.finished.is_set():
            return
        run.status, run.error = status, error
        reply = run.reply
        messages = run.messages + (
            [{"role": "assistant", "content": reply, "ts": _now()}] if reply else []
        )
        current = store.get_session(run.session_id, run.user_id)
        title = current["title"] if current and current["title"] else run.title
        store.save(run.session_id, run.user_id, messages, title, status=status)
        with _lock:
            if _active.get(run.session_id) is run:
                del _active[run.session_id]
        run.finished.set()


def _drive(run: ChatRun, stream: Callable[[], Iterator[str]]) -> None:
    iterator: Iterator[str] | None = None
    status, error = "done", None
    try:
        iterator = stream()
        for chunk in iterator:
            if run.cancel.is_set():
                status = "interrupted"
                break
            if chunk and not run.finished.is_set():
                run.chunks.append(chunk)
    except Exception as e:
        status, error = "error", str(e)
    finally:
        # Closing the agent generator closes the provider's HTTP stream too.
        close = getattr(iterator, "close", None)
        if close:
            try:
                close()
            except Exception:
                pass
        _finalize(run, "interrupted" if run.cancel.is_set() else status, error)
