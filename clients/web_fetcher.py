"""Fetch a public web page as text, refusing anything that points inside the network.

Guards against SSRF: only http(s), no credentials in the URL, and every address
the host resolves to must be publicly routable — checked again on each redirect
hop. Responses are size-capped and HTML is reduced to readable text.

Residual risk: DNS is resolved for the check and again by the HTTP client, so a
host that changes its answer between the two (DNS rebinding) is not caught.
"""

from __future__ import annotations

import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_CHARS = 20_000
USER_AGENT = "onKaul/0.1 (+https://github.com/vaibhavkaul/onKaul)"

_TEXT_TYPES = ("text/", "application/json", "application/xml", "application/xhtml+xml")


class FetchRefusedError(Exception):
    """The URL is not allowed to be fetched."""


def _check_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise FetchRefusedError(f"Only http(s) URLs can be fetched, not {parts.scheme or 'none'}")
    if parts.username or parts.password:
        raise FetchRefusedError("URLs with credentials are not allowed")
    host = parts.hostname
    if not host:
        raise FetchRefusedError("URL has no host")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise FetchRefusedError(f"Could not resolve {host}: {e}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            raise FetchRefusedError(f"{host} resolves to a non-public address ({ip})")


class _TextExtractor(HTMLParser):
    """Collect visible text and the <title> from an HTML document."""

    _SKIP = {"script", "style", "noscript", "template", "svg"}
    _BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag in self._BLOCK:
            self._parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        lines = (" ".join(line.split()) for line in "".join(self._parts).splitlines())
        return "\n".join(line for line in lines if line)


def html_to_text(html: str) -> tuple[str, str]:
    """Return (title, visible text) for an HTML document."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return " ".join(parser.title.split()), parser.text()


def _read_capped(response: httpx.Response) -> tuple[bytes, bool]:
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_bytes():
        chunks.append(chunk)
        size += len(chunk)
        if size > MAX_BYTES:
            return b"".join(chunks)[:MAX_BYTES], True
    return b"".join(chunks), False


def fetch_url(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> dict:
    """Fetch a public URL and return its text content."""
    max_chars = max(1, min(int(max_chars), 100_000))
    current = url
    try:
        with httpx.Client(
            timeout=TIMEOUT_SECONDS, follow_redirects=False, headers={"User-Agent": USER_AGENT}
        ) as client:
            for _ in range(MAX_REDIRECTS + 1):
                _check_url(current)
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        current = urljoin(current, response.headers.get("location", ""))
                        continue
                    content_type = response.headers.get("content-type", "").split(";")[0].strip()
                    if response.status_code >= 400:
                        return {"error": f"HTTP {response.status_code}", "url": current}
                    if content_type and not content_type.startswith(_TEXT_TYPES):
                        return {
                            "error": f"Unsupported content type: {content_type}",
                            "url": current,
                        }
                    body, byte_capped = _read_capped(response)
                    encoding = response.encoding or "utf-8"
                break
            else:
                return {"error": f"Too many redirects (>{MAX_REDIRECTS})", "url": current}
    except FetchRefusedError as e:
        return {"error": str(e), "url": current}
    except httpx.HTTPError as e:
        return {"error": f"Fetch failed: {e}", "url": current}

    text = body.decode(encoding, errors="replace")
    title = ""
    if "html" in content_type or text.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
        title, text = html_to_text(text)
    return {
        "url": url,
        "final_url": current,
        "content_type": content_type,
        "title": title,
        "content": text[:max_chars],
        "truncated": byte_capped or len(text) > max_chars,
    }
