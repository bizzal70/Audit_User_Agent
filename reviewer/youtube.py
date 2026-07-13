"""Read a YouTube channel's recent uploads from its public RSS feed.

Free, no API key, no OAuth: https://www.youtube.com/feeds/videos.xml?channel_id=UC...
Returns a text digest of recent videos (title, date, link, description, stats)
for the judge, or None if the feed can't be read.
"""
from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET

_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
}
_UA = "Mozilla/5.0 (compatible; BizzalContentReviewer/1.0)"


def recent_videos(channel_id: str, limit: int = 10) -> str | None:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml = resp.read().decode("utf-8", "replace")
        root = ET.fromstring(xml)
    except Exception as e:  # noqa: BLE001
        print(f"[youtube] feed for {channel_id} failed: {e}")
        return None

    blocks = []
    for entry in root.findall("a:entry", _NS)[:limit]:
        title = entry.findtext("a:title", default="", namespaces=_NS)
        published = entry.findtext("a:published", default="", namespaces=_NS)
        link_el = entry.find("a:link", _NS)
        link = link_el.get("href") if link_el is not None else ""
        group = entry.find("media:group", _NS)
        desc = ""
        views = ""
        if group is not None:
            desc = (group.findtext("media:description", default="", namespaces=_NS) or "")[:400]
            community = group.find("media:community", _NS)
            if community is not None:
                stats = community.find("media:statistics", _NS)
                if stats is not None:
                    views = stats.get("views", "")
        blocks.append(
            f"- {published[:10]} | {title}\n"
            f"  {link}{('  ('+views+' views)') if views else ''}\n"
            f"  {desc.strip()}"
        )
    if not blocks:
        return None
    return "Recent uploads (newest first):\n" + "\n".join(blocks)
