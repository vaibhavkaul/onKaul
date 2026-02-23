# Contributing to onKaul

Thanks for your interest in contributing.

## Development Setup

### Requirements
- Python 3.12+
- uv (recommended) or pip

### Install (uv)
```bash
uv sync
```

### Install (pip)
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure
```bash
cp .env.example .env
```

## Code Quality

```bash
uv run ruff format .
uv run ruff check .
```

## Tests

```bash
uv run pytest
```

## Pull Requests

1. Create a feature branch.
2. Keep PRs focused and small.
3. Run formatting/linting and tests.
4. Provide a clear description of what changed and why.

## Reporting Issues

Use GitHub Issues and include:
- Steps to reproduce
- Expected vs actual behavior
- Logs or screenshots if helpful
