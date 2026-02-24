"""CLI entry point for onKaul."""

from __future__ import annotations

import argparse
import os
import sys

import httpx


def _print_banner(base_url: str) -> None:
    print("onKaul shell")
    print(f"Connected target: {base_url}")
    print("Type your request and press Enter.")
    print("Commands: /help, /clear, /exit, /quit\n")


def _print_help() -> None:
    print("Commands:")
    print("  /help   Show this help")
    print("  /clear  Clear terminal output")
    print("  /exit   Exit shell")
    print("  /quit   Exit shell\n")


def _clear_screen() -> None:
    print("\033[2J\033[H", end="")


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
