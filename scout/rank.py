"""Rank fresh feed items into content opportunities using the Claude API.

Two passes:
  * per-channel  — top opportunities for each channel's beat (title idea, why-now,
    suggested angle/format, source link).
  * cross-channel — stories that fit 2+ channels (the whole point of unifying),
    with the per-channel spin for each.

Advisory only: produces suggestions, never publishes. Same model plumbing as the
reviewer's judge.
"""
from __future__ import annotations

import json
import os

import anthropic

_MODEL = (os.environ.get("REVIEW_MODEL") or "").strip() or "claude-sonnet-5"
_SYSTEM = (
    "You are the content strategist for the Bizzal network. You read fresh news/"
    "social items and turn them into specific, timely content opportunities that "
    "will earn clicks and match each channel's beat and voice. You are advisory "
    "only. Be concrete: propose an actual title/hook, not a vague theme. Respond "
    "with JSON only."
)


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _text(resp) -> str:
    return next(
        (b.text for b in resp.content if getattr(b, "type", None) == "text"), ""
    ).strip()


def _parse_json(raw: str):
    if not raw:
        print("[scout] rank returned empty text")
        return None
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].lstrip("json").strip()
    # Tolerate prose wrapped around the object: parse the outermost {...}.
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        raw = raw[start : end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[scout] JSON parse failed ({e}); head={raw[:120]!r}")
        return None


def _items_block(items: list[dict], cap: int = 45) -> str:
    lines = []
    for i in items[:cap]:
        d = f"[{i['date']}] " if i["date"] else ""
        lines.append(f"- {d}{i['title']} — {i['source']} ({i['category']}) {i['link']}")
    return "\n".join(lines)


def rank_channel(client, channel_id: str, meta: dict, items: list[dict]) -> list[dict]:
    if not items:
        return []
    prompt = (
        f"Channel: {meta['name']}\nBeat/voice: {meta['beat']}\n\n"
        f"Fresh items from the last few days:\n{_items_block(items)}\n\n"
        "Pick the 5 strongest content opportunities for THIS channel. Prefer timely,"
        " specific, high-click angles that fit the beat and voice. Return JSON: "
        '{"opportunities":[{"title":"proposed hook/headline","why_now":"1 sentence",'
        '"angle":"suggested format/angle","source":"url"}]}'
    )
    resp = client.messages.create(
        model=_MODEL, max_tokens=3500, system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    data = _parse_json(_text(resp)) or {}
    return data.get("opportunities") or []


def rank_cross_channel(client, channels: dict, by_topic: dict) -> list[dict]:
    # Compress: show each topic's items so the model can spot spanning stories.
    blocks = []
    for topic, items in by_topic.items():
        blocks.append(f"### topic: {topic}\n{_items_block(items, cap=30)}")
    consume_map = {
        cid: meta["consumes"] for cid, meta in channels.items()
    }
    prompt = (
        "Channels and the topics each consumes:\n"
        + json.dumps(consume_map)
        + "\n\nFresh items grouped by topic:\n"
        + "\n\n".join(blocks)
        + "\n\nFind up to 4 stories/themes that could feed 2+ channels at once "
        "(e.g. a supply-chain attack for both crypto-security and cyber). For each, "
        "give the per-channel spin. Return JSON: "
        '{"plays":[{"story":"the shared story","channels":["id",...],'
        '"angles":{"channel_id":"the spin for that channel"},"source":"url"}]}'
    )
    resp = client.messages.create(
        model=_MODEL, max_tokens=4000, system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    data = _parse_json(_text(resp)) or {}
    return data.get("plays") or []
