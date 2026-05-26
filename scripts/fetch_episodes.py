#!/usr/bin/env python3
"""
Fetch the AEW-some Pod episodes from the Simplecast RSS feed and write
them to data/episodes.json for the static site to render.

Runs in GitHub Actions (open internet), NOT in the chat sandbox.
"""
import json
import re
import sys
import html
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen

FEED_URL = "https://feeds.simplecast.com/nroyEyaj"
OUT = Path(__file__).resolve().parent.parent / "data" / "episodes.json"
UA = "Mozilla/5.0 (compatible; AEWsomePodSite/1.0; +https://github.com)"


def fetch(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def strip_html(text):
    """Turn show-note HTML into a clean plain-text blurb."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"</p>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)          # drop remaining tags
    text = re.sub(r"https?://\S+", "", text)      # drop bare links
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tag(block, name):
    """Pull the inner text of the first <name>...</name> in block."""
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, re.S | re.I)
    if not m:
        return ""
    val = m.group(1).strip()
    cd = re.match(r"<!\[CDATA\[(.*?)\]\]>", val, re.S)
    return cd.group(1).strip() if cd else val


def attr(block, name, key):
    m = re.search(rf"<{name}[^>]*\b{key}=\"([^\"]*)\"", block, re.S | re.I)
    return m.group(1) if m else ""


def fmt_duration(raw):
    """iTunes duration is seconds OR HH:MM:SS. Normalise to '1h 12m'."""
    if not raw:
        return ""
    raw = raw.strip()
    if ":" in raw:
        parts = [int(p) for p in raw.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0)
        h, m, s = parts[0], parts[1], parts[2]
    else:
        try:
            total = int(raw)
        except ValueError:
            return ""
        h, m = total // 3600, (total % 3600) // 60
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m"


def episode_number(title, idx_from_end):
    """Try to pull an explicit episode number from the title, else fall back."""
    m = re.search(r"\b(?:episode|ep\.?)\s*#?\s*(\d{1,4})\b", title, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"#\s*(\d{1,4})\b", title)
    if m:
        return int(m.group(1))
    return None  # unknown; site will hide the number rather than fake it


def main():
    try:
        xml = fetch(FEED_URL)
    except Exception as e:
        print(f"ERROR fetching feed: {e}", file=sys.stderr)
        sys.exit(1)

    items = re.findall(r"<item\b.*?</item>", xml, re.S | re.I)
    print(f"Found {len(items)} items in feed")

    episodes = []
    for i, block in enumerate(items):
        title = strip_html(tag(block, "title"))
        if not title:
            continue
        desc = tag(block, "description") or tag(block, "itunes:summary") \
            or tag(block, "content:encoded")
        blurb = strip_html(desc)
        if len(blurb) > 320:
            blurb = blurb[:317].rsplit(" ", 1)[0] + "..."

        pub_raw = tag(block, "pubDate")
        try:
            dt = parsedate_to_datetime(pub_raw)
            date_disp = dt.strftime("%b %d, %Y")
            date_iso = dt.astimezone(timezone.utc).isoformat()
        except Exception:
            date_disp, date_iso = "", ""

        audio = attr(block, "enclosure", "url")
        duration = fmt_duration(tag(block, "itunes:duration"))
        # link: do NOT strip_html (it deletes URLs). Pull raw text or href.
        link = ""
        lm = re.search(r"<link[^>]*>(.*?)</link>", block, re.S | re.I)
        if lm:
            raw = lm.group(1)
            cd = re.match(r"<!\[CDATA\[(.*?)\]\]>", raw, re.S)
            link = (cd.group(1) if cd else raw).strip()
        if not link or not link.startswith("http"):
            m = re.search(r'<link[^>]*href="([^"]+)"', block, re.I)
            if m:
                link = m.group(1).strip()
        link = html.unescape(link)
        guid = strip_html(tag(block, "guid"))
        num = episode_number(title, len(items) - i)

        episodes.append({
            "num": num,
            "title": title,
            "date": date_disp,
            "date_iso": date_iso,
            "len": duration,
            "blurb": blurb,
            "audio": audio,
            "link": link,
            "guid": guid,
        })

    # Newest first (feeds are usually already in this order, but be safe)
    episodes.sort(key=lambda e: e["date_iso"] or "", reverse=True)

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(episodes),
        "episodes": episodes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Wrote {len(episodes)} episodes to {OUT}")


if __name__ == "__main__":
    main()
