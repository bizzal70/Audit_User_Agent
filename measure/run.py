"""Daily viewer-metrics collector: YouTube + Instagram -> time-series + digest.

Run: python -m measure.run
Appends today's snapshot to measure/metrics/<channel>.json (committed by the
workflow) and files a metrics digest issue that emails you. Phase 1 of the
measure arc; blogs (GoatCounter) and YouTube retention/CTR are phase 2.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from . import collect_instagram, collect_youtube, report

_OUT = Path(__file__).parent / "metrics"


def _append_snapshot(name: str, snapshot: dict) -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    path = _OUT / name
    series = []
    if path.exists():
        try:
            series = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            series = []
    series.append(snapshot)
    series = series[-180:]  # keep ~6 months of daily points
    path.write_text(json.dumps(series, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    date = dt.date.today().isoformat()
    yt = collect_youtube.collect()
    ig = collect_instagram.collect()

    if yt:
        _append_snapshot("youtube.json", {"date": date, **yt})
        print(f"[measure] youtube: {len(yt.get('videos', []))} videos")
    if ig:
        _append_snapshot("instagram.json", {"date": date, **ig})
        print(f"[measure] instagram: {len(ig.get('posts', []))} posts")
    if not yt and not ig:
        print("[measure] nothing collected (check secrets)")

    url = report.publish(report.render(yt, ig))
    print(f"[measure] digest: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
