"""Tee stdout/stderr to a log file."""

import sys
from datetime import datetime
from pathlib import Path

from config import config


class _TeeStream:
    def __init__(self, original, log_file: Path):
        self._original = original
        self._log_file = log_file

    def write(self, data):
        if not data:
            return 0
        self._original.write(data)
        self._original.flush()
        try:
            with open(self._log_file, "a") as f:
                f.write(data)
        except Exception:
            pass
        return len(data)

    def flush(self):
        self._original.flush()


_def_log_path = config.LOGS_DIR / "bee.log"


def enable_tee_logging(log_path: Path | None = None):
    """Enable tee logging for stdout and stderr."""
    path = log_path or _def_log_path
    path.parent.mkdir(parents=True, exist_ok=True)

    header = f"\n===== Bee log started {datetime.utcnow().isoformat()}Z =====\n"
    try:
        with open(path, "a") as f:
            f.write(header)
    except Exception:
        pass

    sys.stdout = _TeeStream(sys.stdout, path)
    sys.stderr = _TeeStream(sys.stderr, path)
