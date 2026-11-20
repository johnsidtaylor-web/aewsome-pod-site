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
APPLE_LOOKUP = (
    "https://itunes.apple.com/lookup?id=1655190709"
    "&entity=podcastEpisode&limit=200"
)
SPOTIFY_SHOW_ID = "7wOoXA1zgghRv25SbOSu7h"
SPOTIFY_EMBED_PAGE = (
    f"https://open.spotify.com/embed/show/{SPOTIFY_SHOW_ID}"
)
# Hardcoded fallbacks for the current latest episode (EP 256, Sparkling Death).
# Used when a live lookup fails so the site never ships an empty player.
APPLE_FALLBACK = {
    "track_id": 1000802416423,
    "slug": "sparkling-death",
    "title": "Sparkling Death",
    "release": "2026-11-17T06:22:00Z",
}
SPOTIFY_FALLBACK = {
    "episode_id": "5FNPKvGgOUFDv9TVFf4NS7",
    "title": "Sparkling Death",
}
OUT = Path(__file__).resolve().parent.parent / "data" / "episodes.json"
UA = "Mozilla/5.0 (compatible; AEWsomePodSite/1.0; +https://github.com)"
UA_BROWSER = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def fetch(url, ua=None):
    req = Request(url, headers={"User-Agent": ua or UA})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def apple_slug_from_view_url(url):
    """Pull the episode slug from a podcasts.apple.com trackViewUrl."""
    m = re.search(r"/podcast/([^/]+)/id\d+", url or "")
    return m.group(1) if m else ""


def fetch_apple_episodes():
    """podcastEpisode rows from the iTunes Lookup API, newest first."""
    raw = fetch(APPLE_LOOKUP)
    data = json.loads(raw)
    eps = [
        r for r in data.get("results") or []
        if r.get("wrapperType") == "podcastEpisode"
    ]
    if not eps:
        raise RuntimeError("iTunes lookup returned no podcastEpisode rows")
    eps.sort(key=lambda r: r.get("releaseDate") or "", reverse=True)
    out = []
    for ep in eps:
        track_id = ep.get("trackId")
        if not track_id:
            continue
        slug = apple_slug_from_view_url(ep.get("trackViewUrl") or "")
        out.append({
            "track_id": int(track_id),
            "slug": slug,
            "title": ep.get("trackName") or "",
            "release": ep.get("releaseDate") or "",
        })
    if not out:
        raise RuntimeError("iTunes episode missing trackId")
    return out


def fetch_apple_latest():
    """Newest podcastEpisode from the iTunes Lookup API (no auth)."""
    eps = fetch_apple_episodes()
    ep = eps[0]
    return {
        "track_id": ep["track_id"],
        "slug": ep["slug"] or APPLE_FALLBACK["slug"],
        "title": ep["title"],
        "release": ep["release"],
    }


def norm_title(s):
    s = (s or "").casefold()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def slugify(title, preferred=None):
    if preferred and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", preferred):
        return preferred
    s = (title or "").casefold()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80] or "episode"


def uniquify_slugs(episodes):
    seen = {}
    for ep in episodes:
        base = slugify(ep.get("title"), ep.get("apple_slug") or ep.get("slug"))
        slug = base
        n = 2
        while slug in seen:
            slug = f"{base}-{n}"
            n += 1
        seen[slug] = True
        ep["slug"] = slug


def attach_apple_ids(episodes, apple_eps):
    by_title = {}
    by_day = {}
    for a in apple_eps:
        nt = norm_title(a["title"])
        if nt and nt not in by_title:
            by_title[nt] = a
        day = (a.get("release") or "")[:10]
        if day and day not in by_day:
            by_day[day] = a
    matched = 0
    for ep in episodes:
        a = by_title.get(norm_title(ep.get("title")))
        if not a:
            a = by_day.get((ep.get("date_iso") or "")[:10])
        if not a:
            continue
        ep["apple_track_id"] = a["track_id"]
        if a.get("slug"):
            ep["apple_slug"] = a["slug"]
        matched += 1
    return matched


def fetch_spotify_latest():
    """Latest episode id from the public Spotify show-embed page. No API key.

    open.spotify.com/oembed?url=<show> returns the latest title but still
    points the iframe at the *show* URL, so we parse the embed page's
    __NEXT_DATA__ (entity.uri = spotify:episode:<id>) instead.
    """
    raw = fetch(SPOTIFY_EMBED_PAGE, ua=UA_BROWSER)
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        raw, re.S,
    )
    episode_id = title = ""
    if m:
        data = json.loads(m.group(1))
        ent = (
            data.get("props", {})
                .get("pageProps", {})
                .get("state", {})
                .get("data", {})
                .get("entity") or {}
        )
        uri = str(ent.get("uri") or "")
        mid = re.search(r"episode:([A-Za-z0-9]{22})", uri)
        episode_id = (ent.get("id") if re.fullmatch(r"[A-Za-z0-9]{22}", str(ent.get("id") or "")) else None) or (mid.group(1) if mid else "")
        title = ent.get("title") or ent.get("name") or ""
    if not episode_id:
        mid = re.search(r"spotify:episode:([A-Za-z0-9]{22})", raw)
        if mid:
            episode_id = mid.group(1)
    if not episode_id:
        raise RuntimeError("could not parse a Spotify episode id from the embed page")
    return {"episode_id": episode_id, "title": title}


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


def episode_number(*texts):
    """Pull an explicit episode number from title, itunes tag, or show notes.

    Never invents a number; returns None when none is stated.
    """
    blob = " ".join(t for t in texts if t)
    m = re.search(r"\b(?:episode|ep\.? )\s*#?\s*(\d{1,4})\b", blob, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"#\s*(\d{1,4})\b", texts[0] if texts else "")
    if m:
        return int(m.group(1))
    return None  # unknown; site will hide the number rather than fake it


SIMPLECAST_FOOTER = re.compile(
    r"\s*Hosted by Simplecast, an AdsWizz company\..*$",
    re.I | re.S,
)


def clean_blurb(text):
    text = strip_html(text)
    text = SIMPLECAST_FOOTER.sub("", text).strip()
    text = re.sub(r"\s+", " ", text).strip()
    return text



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
        blurb_full = clean_blurb(desc)
        # short version for the compact episode-list rows
        if len(blurb_full) > 320:
            blurb_short = blurb_full[:317].rsplit(" ", 1)[0] + "..."
        else:
            blurb_short = blurb_full

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
        ep_tag = tag(block, "itunes:episode").strip()
        if ep_tag.isdigit():
            num = int(ep_tag)
        else:
            num = episode_number(title, blurb_full)
        image = attr(block, "itunes:image", "href") or attr(block, "media:content", "url") or ""
        sm = re.search(r"/episodes/([0-9a-f-]{36})/", audio, re.I)
        simplecast_id = sm.group(1) if sm else ""

        episodes.append({
            "num": num,
            "title": title,
            "date": date_disp,
            "date_iso": date_iso,
            "len": duration,
            "blurb": blurb_short,
            "blurb_full": blurb_full,
            "audio": audio,
            "link": link,
            "guid": guid,
            "image": image,
            "simplecast_id": simplecast_id,
        })

    # Newest first (feeds are usually already in this order, but be safe)
    episodes.sort(key=lambda e: e["date_iso"] or "", reverse=True)

    apple = dict(APPLE_FALLBACK)
    apple_eps = []
    try:
        apple_eps = fetch_apple_episodes()
        latest = apple_eps[0]
        apple = {
            "track_id": latest["track_id"],
            "slug": latest["slug"] or APPLE_FALLBACK["slug"],
            "title": latest["title"],
            "release": latest["release"],
        }
        print(f"Apple latest: {apple['title']} i={apple['track_id']} slug={apple['slug']} ({len(apple_eps)} episodes)")
    except Exception as e:
        print(f"WARN Apple lookup failed ({e}); using fallback i={apple['track_id']}", file=sys.stderr)

    spotify = dict(SPOTIFY_FALLBACK)
    try:
        spotify = fetch_spotify_latest()
        print(f"Spotify latest: {spotify['title']} id={spotify['episode_id']}")
    except Exception as e:
        print(f"WARN Spotify lookup failed ({e}); using fallback id={spotify['episode_id']}", file=sys.stderr)

    matched = attach_apple_ids(episodes, apple_eps)
    print(f"Matched Apple IDs onto {matched} RSS episodes")
    # Attach the Spotify episode id to the matching (usually latest) RSS row only.
    if episodes and spotify.get("episode_id"):
        target = None
        st = norm_title(spotify.get("title"))
        if st:
            for ep in episodes:
                if norm_title(ep.get("title")) == st:
                    target = ep
                    break
        if target is None:
            target = episodes[0]
        target["spotify_episode_id"] = spotify["episode_id"]

    uniquify_slugs(episodes)

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(episodes),
        "latest_embeds": {
            "apple_track_id": apple["track_id"],
            "apple_slug": apple["slug"],
            "apple_title": apple["title"],
            "apple_release": apple["release"],
            "spotify_episode_id": spotify["episode_id"],
            "spotify_title": spotify["title"],
        },
        "episodes": episodes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text())
            prev_cmp = {k: v for k, v in prev.items() if k != "updated"}
            new_cmp = {k: v for k, v in payload.items() if k != "updated"}
            if prev_cmp == new_cmp:
                payload["updated"] = prev.get("updated") or payload["updated"]
                text = json.dumps(payload, indent=2, ensure_ascii=False)
                print("Episode payload unchanged (besides timestamp); keeping previous updated stamp")
        except Exception:
            pass
    OUT.write_text(text)
    print(f"Wrote {len(episodes)} episodes to {OUT}")

    try:
        from generate_pages import generate
        generate(payload)
    except Exception as e:
        print(f"WARN page generation failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
