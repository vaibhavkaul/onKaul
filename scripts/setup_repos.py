#!/usr/bin/env python3
"""
setup_repos.py — Add/update repos in repository_config/repo_config.json.

Accepts repos as:
  positional args   python scripts/setup_repos.py taptapsend/tts-business vaibhavkaul/onkaul.cloud
  comma-separated   python scripts/setup_repos.py "taptapsend/foo, taptapsend/bar"
  newline stdin     echo -e "taptapsend/foo\ntaptapsend/bar" | python scripts/setup_repos.py
  file              python scripts/setup_repos.py --file repos.txt

Repos can be given as  org/name  or just  name  (uses GITHUB_ORG from .env as fallback org).
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "repository_config" / "repo_config.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

TECH_INDICATORS: dict[str, list[str]] = {
    "React": ["react", "@types/react"],
    "Next.js": ["next"],
    "Vue": ["vue"],
    "TypeScript": ["typescript", "ts-node"],
    "Vite": ["vite"],
    "React Router": ["react-router", "react-router-dom"],
    "MUI": ["@mui/material"],
    "Tailwind CSS": ["tailwindcss"],
    "Vitest": ["vitest"],
    "Playwright": ["@playwright/test"],
    "Storybook": ["@storybook/react"],
    "React Hook Form": ["react-hook-form"],
    "Zod": ["zod"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "SQLAlchemy": ["sqlalchemy"],
    "SQLModel": ["sqlmodel"],
    "Alembic": ["alembic"],
    "Pydantic": ["pydantic"],
    "React Native": ["react-native"],
    "Redux": ["redux", "@reduxjs/toolkit"],
    "GraphQL": ["graphql", "@apollo/client"],
}

CONTEXT_FILE_CANDIDATES = [
    "CLAUDE.md",
    "README.md",
    "backend/README.md",
    "frontend/README.md",
]

AI_DOCS_PATH = "ai/docs"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=check)


def gh(*args: str, check: bool = True) -> dict | list | str | None:
    """Run a gh api call and return parsed JSON, or None on error."""
    result = run(["gh", "api", *args], check=False)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip() or None


# ── Step 1: Check gh ──────────────────────────────────────────────────────────


def check_gh() -> None:
    try:
        result = run(["gh", "auth", "status"], check=False)
        if result.returncode != 0:
            print("✗ gh is not authenticated. Run: gh auth login")
            sys.exit(1)
        print("✓ gh is installed and authenticated")
    except FileNotFoundError:
        print("✗ gh CLI not found. Install from https://cli.github.com/")
        sys.exit(1)


# ── Step 2: Parse repo list ───────────────────────────────────────────────────


def _load_default_org() -> str:
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            m = re.match(r"^\s*GITHUB_ORG\s*=\s*(.+)", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return ""


def parse_repos(raw: list[str], default_org: str) -> list[tuple[str, str]]:
    """Return list of (org, name) tuples."""
    # Flatten: split on commas, whitespace, newlines
    tokens: list[str] = []
    for item in raw:
        tokens.extend(re.split(r"[\s,]+", item))

    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    for token in tokens:
        token = token.strip().strip("/")
        if not token:
            continue
        if "/" in token:
            org, name = token.split("/", 1)
        elif default_org:
            org, name = default_org, token
        else:
            print(f"  ⚠  Cannot resolve org for '{token}' — provide as org/name or set GITHUB_ORG in .env")
            continue
        key = f"{org}/{name}"
        if key not in seen:
            seen.add(key)
            results.append((org, name))
    return results


# ── Step 3: Inspect repo via gh api ──────────────────────────────────────────


def _fetch_file_decoded(owner: str, repo: str, path: str) -> str | None:
    data = gh(f"repos/{owner}/{repo}/contents/{path}")
    if not isinstance(data, dict):
        return None
    content = data.get("content", "")
    encoding = data.get("encoding", "")
    if encoding == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception:
            return None
    return content or None


def _root_filenames(owner: str, repo: str) -> set[str]:
    data = gh(f"repos/{owner}/{repo}/contents/")
    if not isinstance(data, list):
        return set()
    return {item["name"] for item in data if isinstance(item, dict)}


def _list_dir(owner: str, repo: str, path: str) -> list[str]:
    data = gh(f"repos/{owner}/{repo}/contents/{path}")
    if not isinstance(data, list):
        return []
    return [item["name"] for item in data if isinstance(item, dict)]


def detect_tech_stack(owner: str, repo: str, root_files: set[str], primary_language: str) -> list[str]:
    stack: list[str] = []

    # Parse package.json
    if "package.json" in root_files:
        raw = _fetch_file_decoded(owner, repo, "package.json")
        if raw:
            try:
                pkg = json.loads(raw)
                deps = {
                    *pkg.get("dependencies", {}).keys(),
                    *pkg.get("devDependencies", {}).keys(),
                }
                for label, indicators in TECH_INDICATORS.items():
                    if any(ind in deps for ind in indicators):
                        stack.append(label)
            except json.JSONDecodeError:
                pass

    # Parse pyproject.toml / requirements.txt
    py_deps: set[str] = set()
    if "pyproject.toml" in root_files:
        raw = _fetch_file_decoded(owner, repo, "pyproject.toml")
        if raw:
            py_deps.update(re.findall(r'["\s]([\w-]+)\s*[><=!;"\n]', raw.lower()))
    if "requirements.txt" in root_files:
        raw = _fetch_file_decoded(owner, repo, "requirements.txt")
        if raw:
            py_deps.update(line.split("=")[0].split(">")[0].split("<")[0].strip().lower()
                           for line in raw.splitlines() if line.strip() and not line.startswith("#"))
    if py_deps:
        for label, indicators in TECH_INDICATORS.items():
            if any(ind.lower() in py_deps for ind in indicators):
                stack.append(label)

    # Monorepo hints
    if "backend" in root_files and "frontend" in root_files:
        # Check backend too
        be_files = set(_list_dir(owner, repo, "backend"))
        if "pyproject.toml" in be_files or "requirements.txt" in be_files:
            for fname in ["pyproject.toml", "requirements.txt"]:
                if fname in be_files:
                    raw = _fetch_file_decoded(owner, repo, f"backend/{fname}")
                    if raw:
                        for label, indicators in TECH_INDICATORS.items():
                            if any(ind.lower() in raw.lower() for ind in indicators):
                                if label not in stack:
                                    stack.append(label)

        fe_files = set(_list_dir(owner, repo, "frontend"))
        if "package.json" in fe_files:
            raw = _fetch_file_decoded(owner, repo, "frontend/package.json")
            if raw:
                try:
                    pkg = json.loads(raw)
                    deps = {
                        *pkg.get("dependencies", {}).keys(),
                        *pkg.get("devDependencies", {}).keys(),
                    }
                    for label, indicators in TECH_INDICATORS.items():
                        if any(ind in deps for ind in indicators) and label not in stack:
                            stack.append(label)
                except json.JSONDecodeError:
                    pass

    # Fallback: primary language from GitHub
    if primary_language and not stack:
        stack.append(primary_language)

    # Docker
    if any(f in root_files for f in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml")):
        stack.append("Docker")

    return stack


def find_context_files(owner: str, repo: str, root_files: set[str]) -> list[str]:
    found: list[str] = []
    for candidate in CONTEXT_FILE_CANDIDATES:
        top = candidate.split("/")[0]
        if top in root_files:
            # Verify sub-path exists for nested candidates
            if "/" in candidate:
                data = gh(f"repos/{owner}/{repo}/contents/{candidate}", check=False)
                if isinstance(data, dict) and data.get("type") == "file":
                    found.append(candidate)
            else:
                found.append(candidate)

    # Check ai/docs/
    if "ai" in root_files:
        ai_docs = _list_dir(owner, repo, AI_DOCS_PATH)
        for fname in sorted(ai_docs):
            found.append(f"{AI_DOCS_PATH}/{fname}")

    return found


# ── Step 4: Clone if needed ───────────────────────────────────────────────────


def clone_if_needed(org: str, name: str) -> None:
    workspace = REPO_ROOT / "workplace" / name
    if workspace.exists():
        print(f"  ✓ Already cloned at workplace/{name}")
        return
    workspace.parent.mkdir(parents=True, exist_ok=True)
    print(f"  ⬇  Cloning {org}/{name} into workplace/{name}...")
    result = run(["gh", "repo", "clone", f"{org}/{name}", str(workspace)], check=False)
    if result.returncode == 0:
        print(f"  ✓ Cloned successfully")
    else:
        print(f"  ⚠  Clone failed: {result.stderr.strip()}")


# ── Step 5: Update repo_config.json ──────────────────────────────────────────


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {"repositories": {}, "investigation_strategy": {}, "additional_context": {}}


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def build_repo_entry(owner: str, name: str, description: str, tech_stack: list[str], context_files: list[str]) -> dict:
    return {
        "name": name,
        "org": owner,
        "description": description,
        "tech_stack": tech_stack,
        "key_systems": [],
        "handles": [],
        "context_files": context_files,
    }


def upsert_repo(config: dict, owner: str, name: str, entry: dict) -> str:
    existing = config["repositories"].get(name)
    if existing:
        # Preserve manually set fields; update auto-detected ones
        entry["key_systems"] = existing.get("key_systems", [])
        entry["handles"] = existing.get("handles", [])
        config["repositories"][name] = entry
        return "updated"
    else:
        config["repositories"][name] = entry
        return "added"


# ── Main ──────────────────────────────────────────────────────────────────────


def process_repo(owner: str, name: str) -> None:
    slug = f"{owner}/{name}"
    print(f"\n→ {slug}")

    # Fetch GitHub metadata
    meta = gh(f"repos/{owner}/{name}")
    if not isinstance(meta, dict):
        print(f"  ✗ Could not fetch repo info (check org/name and gh auth)")
        return

    description: str = meta.get("description") or f"{name} repository"
    primary_language: str = meta.get("language") or ""

    print(f"  desc: {description}")
    print(f"  lang: {primary_language or '(unknown)'}")

    root_files = _root_filenames(owner, name)
    print(f"  root files: {len(root_files)} found")

    tech_stack = detect_tech_stack(owner, name, root_files, primary_language)
    print(f"  stack: {', '.join(tech_stack) or '(none detected)'}")

    context_files = find_context_files(owner, name, root_files)
    print(f"  context files: {context_files or '(none)'}")

    clone_if_needed(owner, name)

    config = load_config()
    entry = build_repo_entry(owner, name, description, tech_stack, context_files)
    action = upsert_repo(config, owner, name, entry)
    save_config(config)

    print(f"  ✓ {action} in {CONFIG_PATH.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repos", nargs="*", help="Repos to add (org/name or name)")
    parser.add_argument("--file", "-f", help="File with one repo per line")
    args = parser.parse_args()

    check_gh()

    raw: list[str] = list(args.repos)

    if args.file:
        raw.extend(Path(args.file).read_text().splitlines())

    # Read stdin if no args and stdin is piped
    if not raw and not sys.stdin.isatty():
        raw.extend(sys.stdin.read().splitlines())

    if not raw:
        parser.print_help()
        sys.exit(0)

    default_org = _load_default_org()
    repos = parse_repos(raw, default_org)

    if not repos:
        print("No valid repos found.")
        sys.exit(1)

    print(f"\nProcessing {len(repos)} repo(s)...\n")
    for org, name in repos:
        process_repo(org, name)

    print("\nDone.")


if __name__ == "__main__":
    main()
