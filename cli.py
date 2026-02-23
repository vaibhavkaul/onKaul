"""CLI entry point for onKaul."""

from __future__ import annotations

import sys

from agent.core import agent


def _print_banner() -> None:
    print("onKaul CLI")
    print("Type your request and press Enter.")
    print("Type /exit or /quit to leave.\n")


def main() -> int:
    _print_banner()

    while True:
        try:
            user_input = input("> ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 0

        if not user_input:
            continue

        if user_input.lower() in {"/exit", "/quit"}:
            return 0

        try:
            response = agent.investigate(user_input, context="")
        except Exception as exc:
            print(f"Error: {exc}")
            return 1

        print("\n" + response + "\n")


if __name__ == "__main__":
    sys.exit(main())
