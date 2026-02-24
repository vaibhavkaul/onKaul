#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is not installed. Install uv and retry." >&2
  exit 1
fi

uv run onkaul "$@"
