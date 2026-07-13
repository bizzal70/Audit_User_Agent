"""Publish findings as GitHub issues.

Two delivery legs (see project design):
  * PER-PROPERTY detail issue in each source repo, authored via BIZZAL_REVIEW_PAT
    (needs cross-repo `issues:write`). One stable issue per property; each day's
    review is appended as a comment.
  * DIGEST issue in this repo (Audit_User_Agent), authored via GITHUB_TOKEN so the
    author is github-actions[bot] — that is what actually emails the repo owner
    (GitHub never notifies you of your own PAT-authored actions). The digest links
    to every per-property issue.
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

_DETAIL_TITLE = "🔎 Daily content review"
_DIGEST_TITLE = "🗞️ Daily content review digest"


def _api(method: str, path: str, token: str, body: dict | None = None) -> dict | None:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{_GH_API}{path}", data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[issues] {method} {path} -> {e.code}: {e.read().decode()[:300]}")
    except Exception as e:  # noqa: BLE001
        print(f"[issues] {method} {path} failed: {e}")
    return None


def _find_open_issue(owner: str, repo: str, title: str, token: str) -> dict | None:
    issues = _api("GET", f"/repos/{owner}/{repo}/issues?state=open&per_page=100", token)
    if isinstance(issues, list):
        for it in issues:
            if it.get("title") == title and "pull_request" not in it:
                return it
    return None


def _upsert(owner: str, repo: str, title: str, comment: str, token: str) -> str | None:
    """Ensure a stable issue exists; append today's review as a comment. Returns URL."""
    issue = _find_open_issue(owner, repo, title, token)
    if issue is None:
        issue = _api(
            "POST",
            f"/repos/{owner}/{repo}/issues",
            token,
            {"title": title, "body": comment, "labels": ["content-review"]},
        )
        return issue.get("html_url") if issue else None
    _api(
        "POST",
        f"/repos/{owner}/{repo}/issues/{issue['number']}/comments",
        token,
        {"body": comment},
    )
    return issue.get("html_url")


def _render_detail(r: dict, date: str) -> str:
    lines = [f"### {date} — {r['name']}", ""]
    if r.get("overall") is not None:
        lines.append(f"**Overall: {r['overall']}/5**")
    scores = r.get("scores") or {}
    if scores:
        lines.append("")
        for k, v in scores.items():
            lines.append(f"- {k}: **{v}/5**")
    if r.get("top_improvement"):
        lines += ["", f"**⭐ Top improvement:** {r['top_improvement']}"]
    if r.get("findings"):
        lines += ["", "**Findings:**"] + [f"- {f}" for f in r["findings"]]
    if r.get("flags"):
        lines += ["", "**⚠️ Flags:**"] + [f"- {f}" for f in r["flags"]]
    return "\n".join(lines)


def publish(results: list[dict]) -> None:
    date = dt.date.today().isoformat()
    pat = os.environ.get("BIZZAL_REVIEW_PAT")
    gh_token = os.environ.get("GITHUB_TOKEN", "")

    digest_rows = []
    for r in results:
        repo = r["issue_repo"]
        title = f"{_DETAIL_TITLE} — {r['name']}"
        url = None
        if pat:
            url = _upsert(_OWNER, repo, title, _render_detail(r, date), pat)
        else:
            print("[issues] BIZZAL_REVIEW_PAT unset; skipping per-repo detail issues")
        overall = r.get("overall")
        link = f"[details]({url})" if url else "(detail issue skipped)"
        digest_rows.append(
            f"| {r['name']} | {overall if overall is not None else '—'}/5 | "
            f"{(r.get('top_improvement') or '').replace('|', '/')} | {link} |"
        )

    digest = "\n".join(
        [
            f"### {date} — content review digest",
            "",
            "| Property | Overall | Top improvement | |",
            "| --- | --- | --- | --- |",
            *digest_rows,
        ]
    )
    _upsert(_OWNER, _AUDIT_REPO, _DIGEST_TITLE, digest, gh_token or pat or "")
    print(f"[issues] digest published for {date}")
