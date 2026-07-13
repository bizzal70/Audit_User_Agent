"""Collect both LIVE (public) and SOURCE (repo) content for each property.

LIVE  = the audience-facing sources in targets.yml, fetched for free:
          http        -> plain GET (public blogs)
          youtube_rss -> YouTube RSS feed (no key)
          deferred    -> not fetched (needs a paid scraper); reported as such.
SOURCE = the most recent generated content in the property's GitHub repo,
         read through the GitHub API (cloud-only; no local clone).
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request

from . import fetch, youtube

_GH_API = "https://api.github.com"

# Where each source repo keeps its freshly generated content. The collector
# reads the newest file under the first directory that exists. Bizzal Games
# generates into Supabase (not committed files), so it has no file source.
_SOURCE_PATHS = {
    "Bizzal-Games-YT-PUB": [],
    "itsalreadywritten": ["_posts"],
    "itsalreadypriced": ["_posts", "_field_notes"],
    "itsalreadywhen": ["_posts", "_field_notes"],
}


def _gh(path: str) -> object | None:
    token = os.environ.get("GITHUB_TOKEN", "")
    req = urllib.request.Request(f"{_GH_API}{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:  # noqa: BLE001 - collection must never hard-fail
        print(f"[collect] GitHub API {path} failed: {e}")
        return None


def latest_source(owner: str, repo: str) -> dict | None:
    """Return {'path','text'} for the most recently modified content file."""
    for directory in _SOURCE_PATHS.get(repo, []):
        listing = _gh(f"/repos/{owner}/{repo}/contents/{directory}")
        if not isinstance(listing, list) or not listing:
            continue
        # Filenames in these repos are date-prefixed, so name sort == recency.
        newest = sorted(
            (f for f in listing if f.get("type") == "file"),
            key=lambda f: f["name"],
        )[-1]
        blob = _gh(f"/repos/{owner}/{repo}/contents/{newest['path']}")
        if isinstance(blob, dict) and blob.get("content"):
            text = base64.b64decode(blob["content"]).decode("utf-8", "replace")
            return {"path": newest["path"], "text": text[:20000]}
    return None


def _fetch_live(src: dict) -> dict:
    method = src.get("method", "http")
    label, url = src["label"], src.get("url", "")
    if method == "http":
        content = fetch.get_text(url)
    elif method == "youtube_rss":
        content = youtube.recent_videos(src["channel_id"])
    elif method == "deferred":
        return {"label": label, "url": url, "content": None, "ok": False,
                "reason": "deferred — free reading not available for this channel"}
    else:
        return {"label": label, "url": url, "content": None, "ok": False,
                "reason": f"unknown method '{method}'"}
    return {"label": label, "url": url, "content": content, "ok": content is not None,
            "reason": None if content is not None else "fetch failed today"}


def collect(prop: dict, owner: str) -> dict:
    live = {}
    for src in prop.get("live") or []:
        result = _fetch_live(src)
        live[result["label"]] = result

    source = latest_source(owner, prop["source"])
    return {
        "id": prop["id"],
        "name": prop["name"],
        "rubric": prop["rubric"],
        "issue_repo": prop["issue_repo"],
        "live": live,
        "source": source,
    }
