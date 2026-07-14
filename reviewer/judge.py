"""Score one property's content against its rubric using the Claude API.

Advisory only: the judge produces scores + suggestions, never edits anything.
Returns a dict with per-criterion scores, an overall score, and prose findings.

Env:
  ANTHROPIC_API_KEY   Claude API key.
  REVIEW_MODEL        Model id (default: claude-sonnet-5). Use claude-opus-4-8
                      for the sharpest critique if daily cost is acceptable.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic

_RUBRIC_DIR = Path(__file__).parent / "rubrics"
# Note: a blank env var (e.g. an unset Actions `vars.REVIEW_MODEL`) must fall
# back to the default, so use `or` rather than dict.get's default argument.
_MODEL = os.environ.get("REVIEW_MODEL") or "claude-sonnet-5"

_SYSTEM = (
    "You are the editor-in-chief for the Bizzal content network. You review "
    "published and queued content and return rigorous, specific, actionable "
    "critique. You are advisory only: never rewrite the whole piece, but you "
    "may quote a line and suggest a sharper version. Be honest — a 3 is "
    "average, reserve 5 for genuinely excellent work. Respond with JSON only."
)


def _build_prompt(collected: dict, rubric_text: str) -> str:
    parts = [
        "# Rubric\n",
        rubric_text,
        "\n\n# Content to review\n",
        f"Property: {collected['name']}\n",
    ]
    for label, item in collected["live"].items():
        if item["ok"]:
            parts.append(f"\n## LIVE — {label} ({item['url']})\n{item['content']}\n")
        else:
            reason = item.get("reason") or "unavailable"
            parts.append(f"\n## LIVE — {label}: NOT REVIEWED ({reason})\n")
    src = collected.get("source")
    if src:
        parts.append(f"\n## SOURCE — {src['path']}\n{src['text']}\n")
    else:
        parts.append("\n## SOURCE — none found\n")

    parts.append(
        "\n\n# Scoring rule\n"
        "Only score criteria you could ACTUALLY review from the content above. If a "
        "source is marked 'NOT REVIEWED', OMIT every criterion that depends on it from "
        "`scores` entirely and exclude it from `overall`. Never assign a low score "
        "merely because a source was unavailable.\n"
        "\n# Output format\n"
        "Return a JSON object with exactly these keys:\n"
        '  "scores": object mapping each REVIEWED criterion name to an integer 1-5,\n'
        '  "overall": number (average of the scored criteria only, one decimal),\n'
        '  "top_improvement": string (the single highest-leverage fix),\n'
        '  "findings": array of strings (each a specific, actionable note,\n'
        "             quoting the content where useful),\n"
        '  "flags": array of strings (off-brand / lane-drift / repetition; [] if none).\n'
    )
    return "".join(parts)


def judge(collected: dict) -> dict:
    # REVIEW_RUBRIC lets a manual run apply one alternate lens (e.g. blog_growth)
    # to every property instead of each property's default rubric.
    rubric_name = (os.environ.get("REVIEW_RUBRIC") or "").strip() or collected["rubric"]
    rubric_file = _RUBRIC_DIR / f"{rubric_name}.md"
    rubric_text = rubric_file.read_text(encoding="utf-8")
    prompt = _build_prompt(collected, rubric_text)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=_MODEL,
        max_tokens=3000,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    # Models may emit thinking blocks before the text block, so pick the text
    # block explicitly rather than assuming content[0] is it.
    raw = next(
        (b.text for b in resp.content if getattr(b, "type", None) == "text"),
        "",
    ).strip()
    # Tolerate accidental ```json fences.
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].lstrip("json").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "scores": {},
            "overall": None,
            "top_improvement": "(judge returned unparseable output)",
            "findings": [raw[:1000]],
            "flags": ["judge-parse-error"],
        }
    result["id"] = collected["id"]
    result["name"] = collected["name"]
    result["issue_repo"] = collected["issue_repo"]
    return result
