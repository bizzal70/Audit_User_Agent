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

_URL = os.environ.get(
    "IG_METRICS_URL",
    "https://raw.githubusercontent.com/bizzal70/Bizzal-Games-YT-PUB/main/data/metrics/instagram.json",
)


def collect() -> dict | None:
    try:
        with urllib.request.urlopen(_URL, timeout=30) as r:
            data = json.loads(r.read())
    except Exception as e:  # noqa: BLE001 - degrade gracefully if not published yet
        print(f"[measure] IG metrics file unavailable: {e}")
        return None
    posts = data.get("posts")
    return {"posts": posts, "generated": data.get("generated")} if posts else None
