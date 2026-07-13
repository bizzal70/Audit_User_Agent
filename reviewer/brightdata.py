"""Thin Bright Data Web Unlocker client.

Fetches a public URL through Bright Data so JS-heavy, bot-protected pages
(YouTube, Instagram, X) come back as usable content. Degrades gracefully:
on any failure it returns None so the caller can report "unavailable today"
instead of crashing the whole run.

Env:
  BRIGHTDATA_API_KEY   Bright Data API token.
  BRIGHTDATA_ZONE      Web Unlocker zone name (default: "web_unlocker").
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_ENDPOINT = "https://api.brightdata.com/request"


def fetch(url: str, timeout: int = 90) -> str | None:
    api_key = os.environ.get("BRIGHTDATA_API_KEY")
    if not api_key:
        print(f"[brightdata] no BRIGHTDATA_API_KEY set; skipping {url}")
        return None
    zone = os.environ.get("BRIGHTDATA_ZONE", "web_unlocker")
    payload = json.dumps(
        {"zone": zone, "url": url, "format": "raw", "data_format": "markdown"}
    ).encode()
    req = urllib.request.Request(
        _ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
        # Keep the prompt lean; the judge only needs the visible content.
        return body[:20000]
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"[brightdata] fetch failed for {url}: {e}")
        return None
