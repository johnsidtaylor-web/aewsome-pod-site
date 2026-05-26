#!/usr/bin/env python3
"""
Aggregate AEW news headlines from a curated roster of reputable wrestling
news sources, filter to AEW (loose), dedupe near-identical scoops, and write
data/news.json for the static site.

Self-validating: any feed that fails (404, moved, malformed) is skipped and
logged, the rest still publish. Runs in GitHub Actions, not the chat sandbox.

CREDIT POLICY: we store headline + source + link + short blurb only, and the
site always links back to the original. We never republish full articles.
"""
import json
import re
import sys
import html
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

OUT = Path(__file__).resolve().parent.parent / "data" / "news.json"
UA = "Mozilla/5.0 (compatible; AEWsomePodSite/1.0; +https://github.com)"
MAX_ITEMS = 12          # cap the wall
MAX_AGE_HOURS = 72      # only show stories from the last 3 days
MAX_PER_SOURCE = 6      # keep one source from dominating

# Reputable roster. "aew_only" feeds are pre-filtered category feeds and skip
# keyword matching. General feeds get the loose AEW filter applied.
# NOTE: these URLs are best-known guesses; the first live run logs which
# resolve. Swap any that 404 with the corrected URL (see README).
SOURCES = [
    {"name": "Fightful",           "url": "https://www.fightful.com/rss",                       "aew_only": False},
    {"name": "Wrestling Observer", "url": "https://www.f4wonline.com/feed",                     "aew_only": False},
    {"name": "PWTorch",            "url": "https://pwtorch.com/site/feed",                      "aew_only": False},
    {"name": "POST Wrestling",     "url": "https://postwrestling.com/feed/",                    "aew_only": False},
    {"name": "PWInsider",          "url": "https://www.pwinsider.com/rss.php",                  "aew_only": False},
    {"name": "Wrestling Inc",      "url": "https://www.wrestlinginc.com/feed/",                 "aew_only": False},
    {"name": "ProWrestling.net",   "url": "https://www.prowrestling.net/site/feed",             "aew_only": False},
]

# Loose AEW keyword filter. Catches the obvious + roster/show names so we
# don't miss stories that bury "AEW" in the body.
AEW_KEYWORDS = [
    "aew", "all elite", "dynamite", "collision", "ring of honor", " roh ",
    "forbidden door", "double or nothing", "all out", "full gear",
    "revolution", "worlds end", "world's end", "blood and guts", "blood & guts",
    "grand slam", "tony khan", "continental classic", "casino", "owen hart",
    # current-ish roster names that strongly imply AEW context
    "moxley", "okada", "takeshita", "swerve strickland", "hangman", "mjf",
    "young bucks", "kenny omega", "toni storm", "orange cassidy", "ospreay",
    "mercedes mone", "mercedes moné", "don callis", "kazuchika okada",
]

# Strong WWE-only markers; if present AND no AEW marker, drop it (reduces the
# occasional WWE bleed-through that "loose" filtering allows).
WWE_ONLY_HINTS = ["wwe raw", "smackdown", "wrestlemania", "royal rumble",
                  "money in the bank", "nxt ", "summerslam"]


def fetch(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def strip_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tag(block, name):
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, re.S | re.I)
    if not m:
        return ""
    val = m.group(1).strip()
    cd = re.match(r"<!\[CDATA\[(.*?)\]\]>", val, re.S)
    return cd.group(1).strip() if cd else val


def is_aew(title, blurb):
    text = f"{title} {blurb}".lower()
    has_aew = any(k in text for k in AEW_KEYWORDS)
    if has_aew:
        return True
    return False


# Headlines that are clearly a WWE show piece get dropped outright, even if
# the blurb name-drops AEW in passing (e.g. a Raw review that mentions an AEW
# scrum note). The story's PRIMARY subject is what matters.
WWE_TITLE_KILL = ["wwe raw", "raw review", "raw results", "smackdown",
                  "wrestlemania", "royal rumble", "money in the bank",
                  "nxt ", "summerslam", "wwe nxt", " raw ", "raw rating"]


def looks_wwe_only(title, blurb):
    tl = title.lower()
    # Hard kill: the headline itself is a WWE show review/recap.
    if any(k in tl for k in WWE_TITLE_KILL):
        return True
    text = f"{title} {blurb}".lower()
    has_wwe = any(k in text for k in WWE_ONLY_HINTS)
    has_aew = any(k in text for k in AEW_KEYWORDS)
    return has_wwe and not has_aew


STOPWORDS = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
             "with", "at", "by", "from", "as", "is", "his", "her", "new",
             "after", "over", "aew", "wwe"}


def norm_key(title):
    """Normalise a headline for dedupe via a content-word signature.

    Strip punctuation + stopwords, keep the most distinctive words sorted,
    so 'Moxley signs new multi-year deal' and 'Moxley signs new multi-year
    deal with AEW' collapse to the same key.
    """
    words = re.sub(r"[^a-z0-9 ]", "", title.lower()).split()
    content = [w for w in words if w not in STOPWORDS and len(w) > 2]
    # take the 5 most distinctive (longest) content words, sorted for stability
    content = sorted(set(content), key=lambda w: (-len(w), w))[:5]
    return " ".join(sorted(content))


def rel_time(dt):
    if not dt:
        return ""
    delta = datetime.now(timezone.utc) - dt
    secs = delta.total_seconds()
    if secs < 3600:
        return f"{int(secs // 60)}m"
    if secs < 86400:
        return f"{int(secs // 3600)}h"
    return f"{int(secs // 86400)}d"


def main():
    all_items = []
    status = {}

    for src in SOURCES:
        try:
            xml = fetch(src["url"])
        except (URLError, HTTPError, Exception) as e:
            status[src["name"]] = f"FAILED ({e})"
            print(f"  ! {src['name']}: {e}", file=sys.stderr)
            continue

        blocks = re.findall(r"<item\b.*?</item>", xml, re.S | re.I)
        if not blocks:
            blocks = re.findall(r"<entry\b.*?</entry>", xml, re.S | re.I)  # Atom
        kept = 0
        for block in blocks[:40]:
            title = strip_html(tag(block, "title"))
            if not title:
                continue
            desc = tag(block, "description") or tag(block, "summary") \
                or tag(block, "content:encoded") or tag(block, "content")
            blurb = strip_html(desc)
            if len(blurb) > 200:
                blurb = blurb[:197].rsplit(" ", 1)[0] + "..."

            # link: rss <link>text</link> or atom <link href="">
            # NOTE: do NOT run strip_html here — it deletes URLs. Pull raw.
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
            # last resort: some feeds put the canonical URL in <guid>
            if not link or not link.startswith("http"):
                g = tag(block, "guid")
                g = g.strip()
                if g.startswith("http"):
                    link = g
            link = html.unescape(link)

            if not src["aew_only"]:
                if not is_aew(title, blurb):
                    continue
                if looks_wwe_only(title, blurb):
                    continue

            pub_raw = tag(block, "pubDate") or tag(block, "published") \
                or tag(block, "updated")
            try:
                dt = parsedate_to_datetime(pub_raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                try:
                    dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                except Exception:
                    dt = None

            all_items.append({
                "src": src["name"],
                "h": title,
                "p": blurb,
                "link": link,
                "dt": dt,
                "t": rel_time(dt),
                "key": norm_key(title),
            })
            kept += 1
            if kept >= MAX_PER_SOURCE:
                break
        status[src["name"]] = f"ok ({kept} AEW items)"
        print(f"  + {src['name']}: kept {kept}")

    # Dedupe: same normalised headline = same scoop. Keep the earliest (the
    # source that broke it), then by recency.
    all_items.sort(key=lambda x: x["dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    seen = {}
    deduped = []
    for it in all_items:
        if it["key"] in seen:
            continue
        seen[it["key"]] = True
        deduped.append(it)

    # Drop anything older than MAX_AGE_HOURS (keep items with no date as a
    # safety net so a malformed date doesn't silently nuke a real story).
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    deduped = [it for it in deduped if (it["dt"] is None or it["dt"] >= cutoff)]

    deduped = deduped[:MAX_ITEMS]

    out_items = [{
        "src": it["src"], "h": it["h"], "p": it["p"],
        "link": it["link"], "t": it["t"],
        "dt": it["dt"].isoformat() if it["dt"] else "",
    } for it in deduped]

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(out_items),
        "sources": status,
        "items": out_items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nWrote {len(out_items)} AEW stories to {OUT}")
    print("Source status:", json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
