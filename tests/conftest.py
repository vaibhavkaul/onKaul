from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure tests can import top-level app packages in all environments.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _events_to_tmp(tmp_path, monkeypatch):
    """Keep structured events written during tests out of the real logs/ dir."""
    from config import config

    monkeypatch.setattr(config, "EVENTS_LOG_FILE", tmp_path / "events.jsonl")
    return tmp_path / "events.jsonl"
