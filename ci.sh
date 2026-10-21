#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but not installed or not on PATH."
  exit 1
fi

echo "Running: uv lock --check"
uv lock --check

echo "Running: ruff format --check ."
uv run --locked ruff format --check .

echo "Running: ruff check ."
uv run --locked ruff check .

echo "Running: pytest -q"
uv run --locked pytest -q

echo "All CI checks passed."
