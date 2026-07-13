"""Plain HTTP fetch for public pages (blogs). No third-party service, no auth.

Returns readable text (tags stripped) or None on failure so the caller can
report "unavailable" instead of crashing.
"""
from __future__ import annotations

import re
import urllib.request

_UA = "Mozilla/5.0 (compatible; BizzalContentReviewer/1.0)"
_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\n\s*\n\s*\n+")


def _raw(url: str, timeout: int = 30) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - collection must never hard-fail
        print(f"[fetch] {url} failed: {e}")
        return None


def get_text(url: str, limit: int = 15000) -> str | None:
    """Fetch a page and return visible text with HTML stripped."""
    html = _raw(url)
    if html is None:
        return None
    text = _SCRIPT_STYLE.sub(" ", html)
    text = _TAGS.sub(" ", text)
    text = _WS.sub("\n\n", re.sub(r"[ \t]+", " ", text)).strip()
    return text[:limit]
