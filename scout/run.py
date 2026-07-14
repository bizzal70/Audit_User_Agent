"""Unified content-sourcing scout: fetch feeds -> rank -> opportunities.

Run:  python -m scout.run
Writes machine-readable queues to scout/opportunities/<channel>.json (+ the
cross-channel file), and files a human digest issue that emails you.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import traceback
from pathlib import Path

import yaml

from . import fetch_feeds, rank, report

_HERE = Path(__file__).parent
_FEEDS = _HERE / "feeds.yml"
_OUT = _HERE / "opportunities"


def _write_json(name: str, payload) -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    cfg = yaml.safe_load(_FEEDS.read_text(encoding="utf-8"))
    channels = cfg["channels"]
    feeds = cfg["feeds"]
    days = int(os.environ.get("SCOUT_LOOKBACK_DAYS") or "3")

    items = fetch_feeds.fresh_items(feeds, days=days)
    print(f"[scout] {len(items)} fresh items across all feeds")

    by_topic: dict[str, list[dict]] = {}
    for it in items:
        for t in it["topics"]:
            by_topic.setdefault(t, []).append(it)

    client = rank._client()
    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    per_channel: dict[str, list[dict]] = {}
    for cid, meta in channels.items():
        wanted = set(meta.get("consumes") or [])
        pool = [it for it in items if wanted.intersection(it["topics"])]
        try:
            opps = rank.rank_channel(client, cid, meta, pool)
        except Exception:  # noqa: BLE001 - one channel must not kill the run
            print(f"[scout] rank error {cid}:\n{traceback.format_exc()}")
            opps = []
        per_channel[cid] = opps
        _write_json(f"{cid}.json", {"generated": generated, "opportunities": opps})
        print(f"[scout] {cid}: {len(opps)} opportunities from {len(pool)} items")

    try:
        cross = rank.rank_cross_channel(client, channels, by_topic)
    except Exception:  # noqa: BLE001
        print(f"[scout] cross-channel error:\n{traceback.format_exc()}")
        cross = []
    _write_json("_cross_channel.json", {"generated": generated, "plays": cross})
    print(f"[scout] {len(cross)} cross-channel plays")

    url = report.publish(report.render(per_channel, cross, channels))
    print(f"[scout] digest published: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
