"""Structured events: one JSON object per line, to stdout and logs/events.jsonl.

Every event carries the current run context (``run_id``, ``channel`` and
whatever the entry point set), so all LLM and tool calls made while answering
one question can be grouped by ``run_id``.
"""

from __future__ import annotations

import contextvars
import json
import sys
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from config import config

_context: ContextVar[dict[str, Any]] = ContextVar("onkaul_event_context", default={})


def _merged(fields: dict[str, Any]) -> dict[str, Any]:
    merged = {**_context.get(), **{k: v for k, v in fields.items() if v is not None}}
    merged.setdefault("run_id", uuid.uuid4().hex)
    return merged


@contextmanager
def run_context(**fields: Any) -> Iterator[dict[str, Any]]:
    """Attach fields (e.g. channel="slack", thread_ts=...) to events emitted inside.

    A ``run_id`` is created for the outermost context and inherited by nested ones.
    """
    merged = _merged(fields)
    token = _context.set(merged)
    try:
        yield merged
    finally:
        _context.reset(token)


def iterate_in_run_context(make_iter: Callable[[], Iterator], **fields: Any) -> Iterator:
    """Like ``run_context`` for a generator.

    Servers may advance a sync generator from different threads/contexts, so a
    ContextVar set inside it can vanish between chunks. Running every step in
    one copied context keeps the run fields stable for the whole stream.
    """
    ctx = contextvars.copy_context()

    def start() -> Iterator:
        _context.set(_merged(fields))
        return iter(make_iter())

    it = ctx.run(start)
    while True:
        try:
            item = ctx.run(next, it)
        except StopIteration:
            return
        yield item


def emit(event: str, **fields: Any) -> None:
    """Write one structured event. Never raises."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **_context.get(),
        **fields,
    }
    try:
        line = json.dumps(record, default=str)
        print(line, file=sys.stdout, flush=True)
        with config.EVENTS_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"⚠️  Failed to write event {event}: {e}", file=sys.stderr)
