from __future__ import annotations

import signal

import pytest

from utils.slack_formatter import format_for_slack


@pytest.fixture(autouse=True)
def _fail_instead_of_hanging():
    """The formatter used to loop forever on unmatched **; fail fast if that regresses."""

    def _timeout(*_args):
        raise TimeoutError("format_for_slack hung")

    previous = signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(2)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("plain **bold** text", "plain *bold* text"),
        ("**a** and **b**", "*a* and *b*"),
        ("***both***", "*both*"),
        ("## Summary", "*Summary*"),
        ("## 🔍 **Summary**", "*🔍 Summary*"),
        ("see [docs](https://x.dev)", "see <https://x.dev|docs>"),
        ("**https://x.dev/a**", "https://x.dev/a"),
    ],
)
def test_format_for_slack(text, expected):
    assert format_for_slack(text) == expected


@pytest.mark.parametrize("text", ["a ** b", "x **y", "2 ** 8 = 256"])
def test_unmatched_double_asterisks_are_left_alone(text):
    assert format_for_slack(text) == text


def test_code_is_not_rewritten():
    text = "Call `f(**kwargs)`:\n```python\ndef f(**kwargs):\n    return 2 ** 3\n```\n**done**"

    assert format_for_slack(text) == (
        "Call `f(**kwargs)`:\n```python\ndef f(**kwargs):\n    return 2 ** 3\n```\n*done*"
    )
