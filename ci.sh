#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but not installed or not on PATH."
  exit 1
fi

echo "Running: ruff format --check ."
uv run --with ruff ruff format --check .

echo "Running: ruff check ."
uv run --with ruff ruff check .

echo "Running: pytest -q"
uv run --with pytest pytest -q

echo "All CI checks passed."
