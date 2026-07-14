"""Collect public YouTube video stats via the Data API v3 (key-based, no OAuth).

Recent video IDs come from the channel's uploads playlist (the uploads playlist
id is just the channel id with the UC prefix swapped to UU), and per-video stats
(views/likes/comments) from the videos endpoint. All via the API key — no RSS
dependency (the public RSS feed is flaky). Watch-time / CTR / retention need the
YouTube Analytics API (OAuth) — a phase-2 add.

Env: BIZZAL_YT_DATA_API_KEY, optional YT_CHANNEL_ID (default @Bizzal_Games).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_CHANNEL = os.environ.get("YT_CHANNEL_ID", "UCn8fIswollQTSAJYkAshjyw")
_API = "https://www.googleapis.com/youtube/v3"


def _get(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"[measure] yt api -> {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    except Exception as e:  # noqa: BLE001
        print(f"[measure] yt api failed: {e}")
    return None


def _recent_video_ids(channel_id: str, key: str, limit: int = 12) -> list[str]:
    # Resolve the channel's uploads playlist authoritatively via the channels
    # endpoint (the UC->UU shortcut isn't always accepted).
    ch = _get(f"{_API}/channels?part=contentDetails&id={channel_id}&key={key}")
    items = (ch or {}).get("items", [])
    if not items:
        print(f"[measure] yt: channel {channel_id} returned no items")
        return []
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"[measure] yt uploads playlist: {uploads}")
    data = _get(
        f"{_API}/playlistItems?part=contentDetails&maxResults={limit}"
        f"&playlistId={uploads}&key={key}"
    )
    if not data:
        return []
    return [
        it["contentDetails"]["videoId"]
        for it in data.get("items", [])
        if it.get("contentDetails", {}).get("videoId")
    ]


def collect() -> dict | None:
    key = os.environ.get("BIZZAL_YT_DATA_API_KEY")
    if not key:
        print("[measure] no BIZZAL_YT_DATA_API_KEY; skipping YouTube")
        return None
    ids = _recent_video_ids(_CHANNEL, key)
    if not ids:
        return None
    data = _get(f"{_API}/videos?part=snippet,statistics&id={','.join(ids)}&key={key}")
    if not data:
        return None
    videos = []
    for it in data.get("items", []):
        s = it.get("statistics", {})
        sn = it.get("snippet", {})
        videos.append(
            {
                "id": it.get("id"),
                "title": sn.get("title", ""),
                "published": (sn.get("publishedAt", "") or "")[:10],
                "views": int(s.get("viewCount", 0) or 0),
                "likes": int(s.get("likeCount", 0) or 0),
                "comments": int(s.get("commentCount", 0) or 0),
            }
        )
    return {"videos": videos}
