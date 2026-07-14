"""Collect public YouTube video stats via the Data API v3 (key-based, no OAuth).

Recent video IDs come from the free RSS feed; per-video stats (views/likes/
comments) come from the videos endpoint (1 quota unit each). Watch-time, CTR,
and retention need the YouTube Analytics API (OAuth) — a phase-2 add.

Env: BIZZAL_YT_DATA_API_KEY, optional YT_CHANNEL_ID (default @Bizzal_Games).
"""
from __future__ import annotations

import json
import os
import urllib.request
import xml.etree.ElementTree as ET

_CHANNEL = os.environ.get("YT_CHANNEL_ID", "UCn8fIswollQTSAJYkAshjyw")
_UA = "Mozilla/5.0 (compatible; BizzalMeasure/1.0)"
_NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def _recent_video_ids(channel_id: str, limit: int = 12) -> list[str]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            root = ET.fromstring(r.read())
    except Exception as e:  # noqa: BLE001
        print(f"[measure] yt feed failed: {e}")
        return []
    ids = []
    for entry in root.findall("a:entry", _NS)[:limit]:
        vid = entry.findtext("yt:videoId", default="", namespaces=_NS)
        if vid:
            ids.append(vid)
    return ids


def collect() -> dict | None:
    key = os.environ.get("BIZZAL_YT_DATA_API_KEY")
    if not key:
        print("[measure] no BIZZAL_YT_DATA_API_KEY; skipping YouTube")
        return None
    ids = _recent_video_ids(_CHANNEL)
    if not ids:
        return None
    url = (
        "https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics"
        f"&id={','.join(ids)}&key={key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        print(f"[measure] yt data api failed: {e}")
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
