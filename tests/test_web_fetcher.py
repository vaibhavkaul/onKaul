from __future__ import annotations

import socket

import httpx
import pytest

from clients import web_fetcher as wf

PUBLIC = {"example.com": "93.184.215.14", "docs.example.com": "93.184.215.15"}


@pytest.fixture
def dns(monkeypatch):
    """Resolve hosts from a table instead of real DNS."""
    table = dict(PUBLIC)

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if host not in table:
            raise socket.gaierror("not found")
        family = socket.AF_INET6 if ":" in table[host] else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (table[host], port))]

    monkeypatch.setattr(wf.socket, "getaddrinfo", fake_getaddrinfo)
    return table


@pytest.fixture
def web(monkeypatch):
    """Serve canned responses through httpx's MockTransport; records requested URLs."""
    routes: dict[str, httpx.Response] = {}
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return routes.get(str(request.url), httpx.Response(404))

    real_client = httpx.Client
    monkeypatch.setattr(
        wf.httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    return routes, requested


@pytest.mark.parametrize(
    ("ip", "label"),
    [
        ("127.0.0.1", "loopback"),
        ("10.0.0.5", "private"),
        ("192.168.1.1", "private"),
        ("169.254.169.254", "cloud metadata"),
        ("::1", "ipv6 loopback"),
        ("::ffff:127.0.0.1", "ipv4-mapped loopback"),
        ("fd00::1", "ipv6 unique local"),
        ("0.0.0.0", "unspecified"),
    ],
)
def test_refuses_hosts_resolving_to_non_public_addresses(dns, web, ip, label):
    dns["internal.example"] = ip

    result = wf.fetch_url("http://internal.example/admin")

    assert "non-public address" in result["error"], label
    assert web[1] == []


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "gopher://example.com",
        "http://user:pw@example.com/",
    ],
)
def test_refuses_bad_schemes_and_credentials(dns, web, url):
    assert "error" in wf.fetch_url(url)
    assert web[1] == []


def test_redirect_to_internal_address_is_refused(dns, web):
    routes, requested = web
    dns["metadata.internal"] = "169.254.169.254"
    routes["https://example.com/go"] = httpx.Response(
        302, headers={"location": "http://metadata.internal/latest/meta-data/"}
    )

    result = wf.fetch_url("https://example.com/go")

    assert "non-public address" in result["error"]
    assert requested == ["https://example.com/go"]


def test_follows_public_redirect_and_extracts_html_text(dns, web):
    routes, _ = web
    routes["https://example.com/old"] = httpx.Response(302, headers={"location": "/new"})
    routes["https://example.com/new"] = httpx.Response(
        200,
        headers={"content-type": "text/html; charset=utf-8"},
        text=(
            "<html><head><title> Release  notes </title><style>p{}</style></head>"
            "<body><script>evil()</script><h1>v2.0</h1><p>Fixed   the bug.</p></body></html>"
        ),
    )

    result = wf.fetch_url("https://example.com/old")

    assert result["final_url"] == "https://example.com/new"
    assert result["title"] == "Release notes"
    assert result["content"] == "v2.0\nFixed the bug."
    assert result["truncated"] is False


def test_too_many_redirects(dns, web):
    routes, _ = web
    routes["https://example.com/loop"] = httpx.Response(302, headers={"location": "/loop"})

    assert "Too many redirects" in wf.fetch_url("https://example.com/loop")["error"]


def test_rejects_binary_content(dns, web):
    web[0]["https://example.com/a.pdf"] = httpx.Response(
        200, headers={"content-type": "application/pdf"}, content=b"%PDF"
    )

    assert "Unsupported content type" in wf.fetch_url("https://example.com/a.pdf")["error"]


def test_caps_download_size_and_chars(dns, web, monkeypatch):
    monkeypatch.setattr(wf, "MAX_BYTES", 1000)
    web[0]["https://example.com/big.txt"] = httpx.Response(
        200, headers={"content-type": "text/plain"}, content=b"a" * 5000
    )

    result = wf.fetch_url("https://example.com/big.txt", max_chars=100)

    assert len(result["content"]) == 100
    assert result["truncated"] is True


def test_http_errors_are_reported(dns, web):
    assert wf.fetch_url("https://example.com/missing")["error"] == "HTTP 404"


def test_html_without_closing_head_keeps_body_text():
    title, text = wf.html_to_text("<html><head><title>T</title><body><p>visible</p>")

    assert (title, text) == ("T", "visible")
