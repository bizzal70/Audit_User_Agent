"""Collect Instagram Reel/post insights via the Graph API (Instagram Login).

Mirrors the publishing pipeline's auth (graph.instagram.com + the same two
secrets). This is also the source that finally lets the reviewer SEE Instagram
instead of marking it 'deferred'.

Env: BIZZAL_IG_ACCESS_TOKEN, BIZZAL_IG_USER_ID.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

_BASE = "https://graph.instagram.com/v20.0"


def _get(path: str, params: dict) -> dict | None:
    url = f"{_BASE}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001 - collection must never hard-fail
        print(f"[measure] ig {path} failed: {e}")
        return None


def collect(limit: int = 12) -> dict | None:
    token = os.environ.get("BIZZAL_IG_ACCESS_TOKEN")
    uid = os.environ.get("BIZZAL_IG_USER_ID")
    if not token or not uid:
        print("[measure] no BIZZAL_IG_* creds; skipping Instagram")
        return None
    media = _get(
        f"{uid}/media",
        {
            "fields": "id,caption,media_type,permalink,timestamp",
            "limit": limit,
            "access_token": token,
        },
    )
    if not media or "data" not in media:
        return None
    posts = []
    for m in media["data"]:
        mid = m.get("id")
        is_video = m.get("media_type") == "VIDEO"
        # Metric names differ by media type / API version; request a sensible
        # set and tolerate any the account/type doesn't expose.
        metric = (
            "reach,likes,comments,saved,shares,views"
            if is_video
            else "reach,likes,comments,saved"
        )
        ins = _get(f"{mid}/insights", {"metric": metric, "access_token": token}) or {}
        vals = {
            d.get("name"): (d.get("values", [{}]) or [{}])[0].get("value")
            for d in ins.get("data", [])
        }
        posts.append(
            {
                "id": mid,
                "permalink": m.get("permalink", ""),
                "timestamp": (m.get("timestamp", "") or "")[:10],
                "caption": (m.get("caption", "") or "")[:80],
                "media_type": m.get("media_type", ""),
                "reach": vals.get("reach"),
                "likes": vals.get("likes"),
                "comments": vals.get("comments"),
                "saved": vals.get("saved"),
                "shares": vals.get("shares"),
                "views": vals.get("views"),
            }
        )
    return {"posts": posts}
