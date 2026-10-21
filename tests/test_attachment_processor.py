from __future__ import annotations

import httpx

from utils import attachment_processor as mod


def _fake_get(responses: dict[str, httpx.Response], calls: list[dict]):
    """Serve canned responses, following redirects only when asked to."""

    def get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        response = responses[url]
        if response.is_redirect and kwargs.get("follow_redirects"):
            return responses[response.headers["location"]]
        return response

    return get


def _response(status: int, url: str, **kwargs) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("GET", url), **kwargs)


def test_slack_download_follows_redirect(monkeypatch):
    private = "https://files.slack.com/files-pri/T1-F1/log.txt"
    cdn = "https://files-cdn.slack.com/log.txt"
    calls: list[dict] = []
    monkeypatch.setattr(
        mod.httpx,
        "get",
        _fake_get(
            {
                private: _response(302, private, headers={"location": cdn}),
                cdn: _response(200, cdn, content=b"boom at line 3"),
            },
            calls,
        ),
    )

    result = mod.AttachmentProcessor().process_slack_file(
        {"url_private": private, "name": "log.txt", "filetype": "txt"}, "xoxb-test"
    )

    assert calls[0]["follow_redirects"] is True
    assert result["processed"] is True
    assert result["extracted_text"] == "boom at line 3"


def test_slack_download_reports_html_login_page(monkeypatch):
    url = "https://files.slack.com/files-pri/T1-F1/shot.png"
    monkeypatch.setattr(
        mod.httpx,
        "get",
        _fake_get(
            {url: _response(200, url, headers={"content-type": "text/html"}, content=b"<html>")},
            [],
        ),
    )

    result = mod.AttachmentProcessor().process_slack_file(
        {"url_private": url, "name": "shot.png", "filetype": "png"}, "xoxb-test"
    )

    assert "files:read" in result["error"]


def test_jira_download_follows_redirect(monkeypatch):
    calls: list[dict] = []
    url = "https://acme.atlassian.net/rest/api/3/attachment/content/1"
    monkeypatch.setattr(
        mod.httpx, "get", _fake_get({url: _response(200, url, content=b"hi")}, calls)
    )

    mod.AttachmentProcessor().process_jira_attachment(
        {"content": url, "filename": "a.txt"}, ("me@acme.dev", "token")
    )

    assert calls[0]["follow_redirects"] is True
