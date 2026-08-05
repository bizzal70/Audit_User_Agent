"""Read Instagram metrics published by the Bizzal-Games-YT-PUB repo.

The IG token already lives (and posts daily) in Bizzal-Games-YT-PUB, and on a
personal GitHub account secrets don't cross repos. So rather than duplicating the
token here, IG insights are collected there (bin/tools/collect_ig_metrics.py) and
committed to data/metrics/instagram.json; this module just reads that public
file. No IG secrets needed in Audit_User_Agent.

Env: IG_METRICS_URL (optional override of the published-file location).
"""
from __future__ import annotations

import json
import os
import urllib.request

# Read via the GitHub contents API, NOT raw.githubusercontent -- the raw CDN
# caches for minutes and can serve stale data (same fix already applied in
# reviewer/instagram.py after it caused phantom stale-caption defects there).
_URL = os.environ.get(
    "IG_METRICS_URL",
    "https://api.github.com/repos/bizzal70/Bizzal-Games-YT-PUB/contents/data/metrics/instagram.json",
)


def collect() -> dict | None:
    try:
        req = urllib.request.Request(_URL)
        req.add_header("Accept", "application/vnd.github.raw")
        req.add_header("Cache-Control", "no-cache")
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except Exception as e:  # noqa: BLE001 - degrade gracefully if not published yet
        print(f"[measure] IG metrics file unavailable: {e}")
        return None
    posts = data.get("posts")
    return {"posts": posts, "generated": data.get("generated")} if posts else None
