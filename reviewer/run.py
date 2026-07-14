"""Daily orchestrator: collect -> judge -> publish issues.

Run:  python -m reviewer.run
Optional: REVIEW_ONLY=itsalreadypriced  to audit a single property (debug).
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

import yaml

from . import collect, judge, report_issues

_TARGETS = Path(__file__).parent / "targets.yml"


def main() -> int:
    cfg = yaml.safe_load(_TARGETS.read_text(encoding="utf-8"))
    owner = (cfg.get("defaults") or {}).get("owner", "bizzal70")
    only = os.environ.get("REVIEW_ONLY")

    results = []
    for prop in cfg["properties"]:
        if only and prop["id"] != only:
            continue
        print(f"[run] reviewing {prop['id']}")
        try:
            collected = collect.collect(prop, owner)
            has_live = any(v["ok"] for v in collected["live"].values())
            if not has_live and not collected["source"]:
                # e.g. Instagram in the key-free config: only a deferred source
                # and no repo content. Don't fabricate scores for it.
                deferred = ", ".join(
                    v["label"] for v in collected["live"].values()
                ) or "all sources"
                print(f"[run] skipping {prop['id']} — nothing reviewable")
                results.append(
                    {
                        "id": prop["id"],
                        "name": prop["name"],
                        "issue_repo": prop["issue_repo"],
                        "overall": None,
                        "scores": {},
                        "top_improvement": (
                            f"deferred — no free source to review ({deferred}); "
                            "needs a paid scraper to enable"
                        ),
                        "findings": [],
                        "flags": ["deferred-no-content"],
                    }
                )
                continue
            results.append(judge.judge(collected))
        except Exception:  # noqa: BLE001 - one bad property must not kill the run
            print(f"[run] ERROR reviewing {prop['id']}:\n{traceback.format_exc()}")
            results.append(
                {
                    "id": prop["id"],
                    "name": prop["name"],
                    "issue_repo": prop["issue_repo"],
                    "overall": None,
                    "scores": {},
                    "top_improvement": "review failed — see workflow logs",
                    "findings": [],
                    "flags": ["run-error"],
                }
            )

    if not results:
        print("[run] nothing to review")
        return 0

    report_issues.publish(results)
    print(f"[run] done — {len(results)} properties reviewed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
