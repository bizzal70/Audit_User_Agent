"""Publish the daily metrics digest as a GitHub issue.

One stable digest issue in Audit_User_Agent, authored by github-actions[bot]
(default GITHUB_TOKEN) so it emails the owner; each day appended as a comment.
The machine-readable time-series lives in measure/metrics/<channel>.json.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request

_GH_API = "https://api.github.com"
_OWNER = os.environ.get("REVIEW_OWNER", "bizzal70")
_AUDIT_REPO = os.environ.get("REVIEW_AUDIT_REPO", "Audit_User_Agent")
_TITLE = "📊 Daily viewer metrics"


def _api(method: str, path: str, body: dict | None = None):
    token = os.environ.get("GITHUB_TOKEN", "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{_GH_API}{path}", data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[measure] {method} {path} -> {e.code}: {e.read().decode()[:200]}")
    except Exception as e:  # noqa: BLE001
        print(f"[measure] {method} {path} failed: {e}")
    return None


def _find_open(title: str):
    issues = _api("GET", f"/repos/{_OWNER}/{_AUDIT_REPO}/issues?state=open&per_page=100")
    if isinstance(issues, list):
        for it in issues:
            if it.get("title") == title and "pull_request" not in it:
                return it
    return None


def _top(items: list[dict], key: str, n: int = 5) -> list[dict]:
    return sorted(items, key=lambda x: (x.get(key) or 0), reverse=True)[:n]


def render(yt: dict | None, ig: dict | None) -> str:
    date = dt.date.today().isoformat()
    lines = [f"### {date} — viewer metrics", ""]

    lines.append("#### YouTube (@Bizzal_Games)")
    if yt and yt.get("videos"):
        vids = yt["videos"]
        total = sum(v["views"] for v in vids)
        lines.append(f"- {len(vids)} recent videos, {total:,} total views")
        for v in _top(vids, "views"):
            lines.append(
                f"  - {v['views']:,} views · {v['likes']:,}♥ · {v['comments']} 💬 — {v['title'][:60]}"
            )
    else:
        lines.append("- not collected (missing BIZZAL_YT_DATA_API_KEY or no data)")
    lines.append("")

    lines.append("#### Instagram (@bizzalgames70)")
    if ig and ig.get("posts"):
        posts = ig["posts"]
        lines.append(f"- {len(posts)} recent posts")
        for p in _top(posts, "reach"):
            reach = p.get("reach") or 0
            lines.append(
                f"  - reach {reach:,} · {p.get('likes') or 0}♥ · {p.get('saved') or 0} saves — {p['caption'][:50]}"
            )
    else:
        lines.append("- not collected (missing BIZZAL_IG_* creds or no data)")
    lines.append("")
    lines.append("_Blogs (GoatCounter) and YouTube retention/CTR land in phase 2._")
    return "\n".join(lines)


def publish(body: str) -> str | None:
    issue = _find_open(_TITLE)
    if issue is None:
        created = _api(
            "POST", f"/repos/{_OWNER}/{_AUDIT_REPO}/issues",
            {"title": _TITLE, "body": body, "labels": ["metrics"]},
        )
        return created.get("html_url") if created else None
    _api(
        "POST", f"/repos/{_OWNER}/{_AUDIT_REPO}/issues/{issue['number']}/comments",
        {"body": body},
    )
    return issue.get("html_url")
