"""CLI entry point for onKaul."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx


def _print_banner(base_url: str) -> None:
    print("onKaul shell")
    print(f"Connected target: {base_url}")
    print("Type your request and press Enter.")
    print("Commands: /help, /setup, /clear, /exit, /quit\n")


def _print_help() -> None:
    print("Commands:")
    print("  /help   Show this help")
    print("  /setup  Configure integrations in .env")
    print("  /clear  Clear terminal output")
    print("  /exit   Exit shell")
    print("  /quit   Exit shell\n")


def _clear_screen() -> None:
    print("\033[2J\033[H", end="")


def _ensure_env_file() -> Path:
    env_path = Path(".env")
    if env_path.exists():
        return env_path

    env_example_path = Path(".env.example")
    if env_example_path.exists():
        env_path.write_text(env_example_path.read_text(encoding="utf-8"), encoding="utf-8")
        print("Created .env from .env.example\n")
        return env_path

    env_path.write_text("", encoding="utf-8")
    print("Created empty .env\n")
    return env_path


def _load_env_map(env_path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def _upsert_env_value(env_path: Path, key: str, value: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            updated.append(f"{key}={value}")
            found = True
            continue
        updated.append(line)
    if not found:
        updated.append(f"{key}={value}")
    env_path.write_text("\n".join(updated).rstrip("\n") + "\n", encoding="utf-8")


def _prompt_env_value(env_path: Path, key: str, label: str) -> None:
    current = _load_env_map(env_path).get(key, "")
    if current:
        value = input(f"{label} [{current}]: ").strip()
        if not value:
            return
    else:
        value = input(f"{label}: ").strip()
        if not value:
            return
    _upsert_env_value(env_path, key, value)


def _run_setup_wizard() -> None:
    env_path = _ensure_env_file()

    while True:
        print("Setup wizard - choose integration:")
        print("  1) Anthropic")
        print("  2) GitHub")
        print("  3) Datadog")
        print("  4) Sentry")
        print("  5) Jira")
        print("  6) Confluence")
        print("  7) Brave Search")
        print("  8) Repo config paths")
        print("  9) Done")
        choice = input("Select 1-9: ").strip()

        if choice == "1":
            _prompt_env_value(env_path, "ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
        elif choice == "2":
            _prompt_env_value(env_path, "GITHUB_ORG", "GITHUB_ORG")
        elif choice == "3":
            _prompt_env_value(env_path, "DD_API_KEY", "DD_API_KEY")
            _prompt_env_value(env_path, "DD_APP_KEY", "DD_APP_KEY")
            _prompt_env_value(env_path, "DD_SITE", "DD_SITE")
        elif choice == "4":
            _prompt_env_value(env_path, "SENTRY_ORG", "SENTRY_ORG")
            _prompt_env_value(env_path, "SENTRY_TOKEN", "SENTRY_TOKEN")
        elif choice == "5":
            _prompt_env_value(env_path, "JIRA_BASE_URL", "JIRA_BASE_URL")
            _prompt_env_value(env_path, "JIRA_EMAIL", "JIRA_EMAIL")
            _prompt_env_value(env_path, "JIRA_API_TOKEN", "JIRA_API_TOKEN")
            _prompt_env_value(env_path, "JIRA_WEBHOOK_SECRET", "JIRA_WEBHOOK_SECRET")
            _prompt_env_value(
                env_path,
                "ENABLE_JIRA_WEBHOOK_VERIFICATION",
                "ENABLE_JIRA_WEBHOOK_VERIFICATION (true/false)",
            )
        elif choice == "6":
            _prompt_env_value(env_path, "CONFLUENCE_EMAIL", "CONFLUENCE_EMAIL")
            _prompt_env_value(env_path, "CONFLUENCE_API_TOKEN", "CONFLUENCE_API_TOKEN")
            _prompt_env_value(env_path, "CONFLUENCE_CLOUD_ID", "CONFLUENCE_CLOUD_ID")
            _prompt_env_value(env_path, "CONFLUENCE_WIKI_BASE_URL", "CONFLUENCE_WIKI_BASE_URL")
            _prompt_env_value(env_path, "CONFLUENCE_API_BASE_URL", "CONFLUENCE_API_BASE_URL")
        elif choice == "7":
            _prompt_env_value(env_path, "BRAVE_SEARCH_API_KEY", "BRAVE_SEARCH_API_KEY")
        elif choice == "8":
            _prompt_env_value(env_path, "REPO_CONFIG_PATH", "REPO_CONFIG_PATH")
            _prompt_env_value(env_path, "MONITORING_CONFIG_PATH", "MONITORING_CONFIG_PATH")
        elif choice == "9":
            print("\nSetup complete. Restart API/worker if they are already running.\n")
            return
        else:
            print("Invalid selection.\n")
            continue

        print("Saved.\n")


def _chat(base_url: str, user_input: str) -> str:
    endpoint = f"{base_url.rstrip('/')}/chat"
    with httpx.Client(timeout=1200.0) as client:
        try:
            resp = client.post(endpoint, json={"message": user_input})
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(
                "Could not connect to local server. Start Docker first with "
                "'docker compose up --build'."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Server returned {exc.response.status_code}: {exc.response.text}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Request to local server failed: {exc}") from exc

    data = resp.json()
    response = data.get("response")
    if not isinstance(response, str):
        raise RuntimeError("Invalid response payload from server.")
    return response


def run_shell(base_url: str) -> int:
    _print_banner(base_url)

    while True:
        try:
            user_input = input("onkaul> ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 0

        if not user_input:
            continue

        command = user_input.lower()
        if command in {"/exit", "/quit"}:
            return 0
        if command == "/help":
            _print_help()
            continue
        if command == "/setup":
            _run_setup_wizard()
            continue
        if command == "/clear":
            _clear_screen()
            _print_banner(base_url)
            continue

        try:
            response = _chat(base_url, user_input)
        except Exception as exc:
            print(f"Error: {exc}\n")
            continue

        print("\n" + response + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="onKaul local shell")
    parser.add_argument(
        "command",
        nargs="?",
        default="shell",
        choices=["shell"],
        help="Command to run (default: shell)",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("ONKAUL_BASE_URL", "http://localhost:8000"),
        help="Base URL for local onKaul API (default: http://localhost:8000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_shell(args.base_url)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
