"""Publish the daily content-opportunities digest as a GitHub issue.

Mirrors the reviewer: one stable digest issue in Audit_User_Agent, authored by
github-actions[bot] (default GITHUB_TOKEN) so it emails the owner, with each day's
opportunities appended as a comment. The machine-readable per-channel JSON queues
are written to disk by run.py and committed by the workflow.
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
_TITLE = "🧭 Daily content opportunities"


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
        print(f"[scout] {method} {path} -> {e.code}: {e.read().decode()[:200]}")
    except Exception as e:  # noqa: BLE001
        print(f"[scout] {method} {path} failed: {e}")
    return None


def _find_open(title: str):
    issues = _api("GET", f"/repos/{_OWNER}/{_AUDIT_REPO}/issues?state=open&per_page=100")
    if isinstance(issues, list):
        for it in issues:
            if it.get("title") == title and "pull_request" not in it:
                return it
    return None


def render(per_channel: dict, cross: list[dict], channels: dict) -> str:
    date = dt.date.today().isoformat()
    lines = [f"### {date} — content opportunities", ""]

    if cross:
        lines.append("#### 🔗 Cross-channel plays")
        for p in cross:
            chans = ", ".join(p.get("channels") or [])
            lines.append(f"- **{p.get('story','')}** → _{chans}_")
            for cid, spin in (p.get("angles") or {}).items():
                lines.append(f"  - `{cid}`: {spin}")
            if p.get("source"):
                lines.append(f"  - source: {p['source']}")
        lines.append("")

    for cid, opps in per_channel.items():
        name = channels.get(cid, {}).get("name", cid)
        lines.append(f"#### {name}")
        if not opps:
            lines.append("- (no strong opportunities today)")
        for o in opps:
            lines.append(f"- **{o.get('title','')}** — {o.get('why_now','')}")
            extra = o.get("angle", "")
            src = o.get("source", "")
            if extra or src:
                lines.append(f"  - {extra}{('  ·  ' + src) if src else ''}")
        lines.append("")
    return "\n".join(lines)


def publish(body: str) -> str | None:
    issue = _find_open(_TITLE)
    if issue is None:
        created = _api(
            "POST", f"/repos/{_OWNER}/{_AUDIT_REPO}/issues",
            {"title": _TITLE, "body": body, "labels": ["content-sourcing"]},
        )
        return created.get("html_url") if created else None
    _api(
        "POST", f"/repos/{_OWNER}/{_AUDIT_REPO}/issues/{issue['number']}/comments",
        {"body": body},
    )
    return issue.get("html_url")
