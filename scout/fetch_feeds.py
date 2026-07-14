"""Fetch + parse every feed in feeds.yml once, keep only fresh items.

Key-free: plain RSS/Atom over HTTP, same philosophy as the reviewer. Shared
feeds are fetched a single time and their items carry every topic tag, so the
router can hand one story to multiple channels. Never hard-fails on a bad feed.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import urllib.request
import xml.etree.ElementTree as ET

_UA = "Mozilla/5.0 (compatible; BizzalContentScout/1.0)"
_ATOM = "{http://www.w3.org/2005/Atom}"


def _fetch(url: str, timeout: int = 20) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:  # noqa: BLE001 - one dead feed must not kill the run
        print(f"[scout] feed failed {url}: {e}")
        return None


def _parse_date(raw: str) -> dt.datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    # RFC 822 (RSS pubDate)
    try:
        d = email.utils.parsedate_to_datetime(raw)
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except Exception:
        pass
    # ISO 8601 (Atom published/updated)
    try:
        d = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


def _items_from_xml(raw: bytes) -> list[dict]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"[scout] xml parse error: {e}")
        return []
    out = []
    # RSS <item>
    for it in root.iter("item"):
        out.append(
            {
                "title": (it.findtext("title") or "").strip(),
                "link": (it.findtext("link") or "").strip(),
                "date": _parse_date(it.findtext("pubDate") or ""),
            }
        )
    # Atom <entry>
    for e in root.iter(f"{_ATOM}entry"):
        link_el = e.find(f"{_ATOM}link")
        out.append(
            {
                "title": (e.findtext(f"{_ATOM}title") or "").strip(),
                "link": (link_el.get("href") if link_el is not None else "") or "",
                "date": _parse_date(
                    e.findtext(f"{_ATOM}published") or e.findtext(f"{_ATOM}updated") or ""
                ),
            }
        )
    return [i for i in out if i["title"]]


def fresh_items(feeds: list[dict], days: int = 3, per_feed_cap: int = 12) -> list[dict]:
    """Return fresh items across all feeds, each tagged with its feed's topics."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    seen_urls: set[str] = set()
    results: list[dict] = []
    for feed in feeds:
        url = feed["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        raw = _fetch(url)
        if not raw:
            continue
        kept = 0
        for item in _items_from_xml(raw):
            # Keep undated items (some feeds omit dates) but prefer fresh ones.
            if item["date"] is not None and item["date"] < cutoff:
                continue
            results.append(
                {
                    "title": item["title"],
                    "link": item["link"],
                    "date": item["date"].date().isoformat() if item["date"] else "",
                    "source": feed["name"],
                    "topics": feed.get("topics") or [],
                    "category": feed.get("category") or "",
                }
            )
            kept += 1
            if kept >= per_feed_cap:
                break
        print(f"[scout] {feed['name']}: {kept} fresh")
    return results
