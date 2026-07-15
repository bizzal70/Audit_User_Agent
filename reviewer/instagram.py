"""Read the Instagram insights the games pipeline publishes, as reviewable text.

The games repo collects reach/likes/saves per Reel into data/metrics/instagram.json
(bin/tools/collect_ig_metrics.py). Formatting it here lets the reviewer actually
score Instagram (caption quality + real engagement) instead of marking it
'deferred'. Key-free — just reads the public file.

Env: IG_METRICS_URL (optional override of the published-file location).
"""
from __future__ import annotations

import json
import os
import urllib.request

_URL = os.environ.get(
    "IG_METRICS_URL",
    "https://raw.githubusercontent.com/bizzal70/Bizzal-Games-YT-PUB/main/data/metrics/instagram.json",
)


def recent_posts() -> str | None:
    try:
        with urllib.request.urlopen(_URL, timeout=30) as r:
            data = json.loads(r.read())
    except Exception as e:  # noqa: BLE001 - degrade gracefully if not published yet
        print(f"[collect] ig metrics unavailable: {e}")
        return None
    posts = data.get("posts") or []
    if not posts:
        return None
    lines = [
        f"Recent Instagram Reels with real insights (collected {data.get('generated','')}):",
        "",
    ]
    for p in posts[:12]:
        lines.append(
            f"- {p.get('timestamp','')} | reach {p.get('reach') or 0}, views {p.get('views') or 0}, "
            f"likes {p.get('likes') or 0}, comments {p.get('comments') or 0}, saves {p.get('saved') or 0}"
        )
        cap = (p.get("caption") or "").strip().replace("\n", " ")
        if cap:
            lines.append(f"  caption: {cap}")
        if p.get("permalink"):
            lines.append(f"  {p['permalink']}")
    return "\n".join(lines)
