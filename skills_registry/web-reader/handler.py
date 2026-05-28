"""Fetch and extract clean text from any webpage. Stdlib only."""

import urllib.request
import urllib.error
import urllib.parse
import re
from html.parser import HTMLParser


# Tags whose entire content (including children) should be skipped
_SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"}
# Tags that act as block separators
_BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td", "th"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0
        self._title: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in _BLOCK_TAGS and self._skip_depth == 0:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self._title.append(data)
            return
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._parts.append(text)

    def get_title(self) -> str:
        return "".join(self._title).strip()

    def get_text(self) -> str:
        raw = " ".join(self._parts)
        # Collapse multiple whitespace/newlines
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        raw = re.sub(r" {2,}", " ", raw)
        return raw.strip()


def _is_public_host(host: str) -> bool:
    """Reject internal/link-local/loopback addresses to prevent SSRF.

    Resolves the hostname and bails if any returned address is private. This
    blocks the obvious attacks: hitting `http://postgres:5432`,
    `http://169.254.169.254/` (AWS metadata), `http://localhost`, etc."""
    import ipaddress
    import socket
    host = host.split(":")[0].strip().lower()
    if not host or host in {"localhost"}:
        return False
    try:
        addrs = {ai[4][0] for ai in socket.getaddrinfo(host, None)}
    except Exception:
        return False
    if not addrs:
        return False
    for a in addrs:
        try:
            ip = ipaddress.ip_address(a)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_unspecified
            or ip.is_reserved
        ):
            return False
    return True


def handle(inputs: dict) -> dict:
    url = str(inputs.get("url", "")).strip()
    if not url:
        return {"error": "url is required"}
    if not url.startswith(("http://", "https://")):
        return {"error": "url must start with http:// or https://"}

    # SSRF guard: refuse internal/link-local/loopback targets up front.
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if not parsed.hostname or not _is_public_host(parsed.hostname):
        return {"error": "URL host is not a public address (SSRF blocked)", "url": url}

    max_chars = min(int(inputs.get("max_chars", 6000)), 20000)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return {"error": f"Unsupported content type: {content_type}", "url": url}
            raw_html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "url": url}
    except urllib.error.URLError as e:
        return {"error": f"Cannot reach URL: {e.reason}", "url": url}
    except Exception as e:
        return {"error": f"Fetch failed: {str(e)}", "url": url}

    parser = _TextExtractor()
    try:
        parser.feed(raw_html)
    except Exception:
        pass

    title = parser.get_title()
    content = parser.get_text()
    char_count = len(content)

    if char_count == 0:
        return {"error": "Could not extract text from page (may require JavaScript)", "url": url}

    truncated = content[:max_chars]
    if char_count > max_chars:
        truncated += f"\n\n[... truncated. Total: {char_count} chars. Use max_chars to read more.]"

    return {
        "url": url,
        "title": title,
        "content": truncated,
        "char_count": char_count,
    }
