#!/usr/bin/env python3
"""Generate per-episode pages, sitemap.xml, and the homepage episode JSON-LD block."""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://aewsomepod.com"
APPLE_SHOW = "https://podcasts.apple.com/us/podcast/the-aew-some-pod-w-johnny-taylor-diana-prince-gringo/id1655190709"
SPOTIFY_SHOW = "https://open.spotify.com/show/7wOoXA1zgghRv25SbOSu7h"
RSS = "https://feeds.simplecast.com/nroyEyaj"
IHEART = "https://www.iheart.com/podcast/269-the-aew-some-pod-w-johnny-104826268/"
PODBEAN = "https://www.podbean.com/podcast-detail/episode-list?pid=dir2688267"
APPLE_SHOW_ID = "1655190709"
# Show-level directory URLs used on PodcastSeries.sameAs and episode listen links.
SHOW_SAME_AS = [APPLE_SHOW, SPOTIFY_SHOW, IHEART, PODBEAN]

HEAD_ICONS = """
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#111111">
<link rel="alternate" type="application/rss+xml" title="The AEW-some Pod RSS feed" href="https://feeds.simplecast.com/nroyEyaj">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Oswald:wght@500;600;700&family=Barlow+Condensed:ital,wght@0,400;0,500;0,600;0,700;1,600;1,700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
""".strip()

FOOTER = """
<div class="torn torn-black" aria-hidden="true"></div>
<footer>
  <div class="listen-row" aria-label="Subscribe">
    <a href="https://podcasts.apple.com/us/podcast/the-aew-some-pod-w-johnny-taylor-diana-prince-gringo/id1655190709" target="_blank" rel="noopener">Apple Podcasts</a>
    <a href="https://open.spotify.com/show/7wOoXA1zgghRv25SbOSu7h" target="_blank" rel="noopener">Spotify</a>
    <a href="https://feeds.simplecast.com/nroyEyaj" rel="noopener">RSS feed</a>
    <a href="https://www.iheart.com/podcast/269-the-aew-some-pod-w-johnny-104826268/" target="_blank" rel="noopener">iHeart</a>
    <a href="https://www.podbean.com/podcast-detail/episode-list?pid=dir2688267" target="_blank" rel="noopener">Podbean</a>
  </div>
  <div class="presented-mini" aria-label="Presented by Kalshi">
    <span class="k">Presented by</span>
    <span class="n">Kalshi</span>
  </div>
  <div class="nets">
    <span style="color:var(--cream);font-size:11px;letter-spacing:.1em">BROUGHT TO YOU BY</span>
    <span class="net">Bleav</span>
    <span class="net">Creative Control Network</span>
  </div>
  THE AEW-SOME POD &copy; 2026 &middot; Diana Prince &middot; Gringo Fantastico &middot; Johnny Taylor<br>
  Not affiliated with AEW or Tony Khan <b>(yet)</b> &middot; News headlines &copy; their respective outlets
</footer>
""".strip()

NAV = """
<nav>
  <a href="/" class="nav-brand">
    <picture>
      <source type="image/webp" srcset="/assets/logo-nav.webp">
      <img src="/assets/logo-nav.png" width="44" height="44" alt="">
    </picture>
    <span>AEW-SOME <i>POD</i></span>
  </a>
  <ul class="navlinks">
    <li><a href="/#listen">Listen</a></li>
    <li><a href="/#episodes">Episodes</a></li>
    <li><a href="/#news">News</a></li>
    <li><a href="/#hosts">Crew</a></li>
  </ul>
</nav>
""".strip()


def esc(s):
    return html.escape(str(s or ""), quote=True)


def apple_url(ep):
    tid = ep.get("apple_track_id")
    if not tid:
        return APPLE_SHOW
    slug = ep.get("apple_slug") or ep.get("slug") or "episode"
    return f"https://podcasts.apple.com/us/podcast/{slug}/id{APPLE_SHOW_ID}?i={tid}"


def spotify_url(ep):
    sid = ep.get("spotify_episode_id")
    if sid:
        return f"https://open.spotify.com/episode/{sid}"
    return SPOTIFY_SHOW


def page_url(ep):
    return f"{SITE}/episodes/{ep['slug']}/"


def player_html(ep):
    title = esc(ep.get("title") or "Episode")
    bits = []
    tid = ep.get("apple_track_id")
    slug = ep.get("apple_slug") or ep.get("slug") or "episode"
    sid = ep.get("spotify_episode_id")
    sc = ep.get("simplecast_id")
    if tid:
        src = esc(f"https://embed.podcasts.apple.com/us/podcast/{slug}/id{APPLE_SHOW_ID}?i={tid}&theme=dark")
        bits.append(
            f'<iframe title="{title} on Apple Podcasts" allow="autoplay *; encrypted-media *; clipboard-write" '
            f'frameborder="0" height="175" style="width:100%;overflow:hidden;background:transparent" '
            f'sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-storage-access-by-user-activation allow-top-navigation-by-user-activation" '
            f'src="{src}"></iframe>'
        )
    elif sid:
        src = esc(f"https://open.spotify.com/embed/episode/{sid}?utm_source=generator&theme=0")
        bits.append(
            f'<iframe title="{title} on Spotify" src="{src}" width="100%" height="232" frameborder="0" '
            f'allowfullscreen allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>'
        )
    elif sc:
        src = esc(f"https://player.simplecast.com/{sc}")
        bits.append(
            f'<iframe title="{title} player" src="{src}" height="200" width="100%" frameborder="0" scrolling="no" loading="lazy"></iframe>'
        )
    elif ep.get("audio"):
        bits.append(f'<audio controls preload="none" src="{esc(ep["audio"])}">Your browser does not support audio. <a href="{esc(ep["audio"])}">Download the episode</a>.</audio>')
    if not bits:
        link = ep.get("link") or "/#listen"
        bits.append(f'<p><a class="btn red" href="{esc(link)}">Listen to this episode</a></p>')
    return "\n".join(bits)


def notes_html(ep):
    text = (ep.get("blurb_full") or ep.get("blurb") or "").strip()
    if not text:
        return "<p>Show notes for this episode were not included in the feed.</p>"
    # Real show notes only, as plain paragraphs (feed is already stripped to text).
    chunks = re.split(r"\n{2,}", text)
    return "\n".join(f"<p>{esc(chunk).replace(chr(10), '<br>')}</p>" for chunk in chunks if chunk.strip())


def episode_jsonld(ep, with_series=True):
    title = ep.get("title") or "Episode"
    desc = (ep.get("blurb_full") or ep.get("blurb") or title).strip()
    if len(desc) > 400:
        desc = desc[:397].rsplit(" ", 1)[0] + "..."
    data = {
        "@type": "PodcastEpisode",
        "name": title,
        "url": page_url(ep),
        "description": desc,
        "datePublished": ep.get("date_iso") or None,
        "partOfSeries": {
            "@type": "PodcastSeries",
            "name": "The AEW-some Pod",
            "url": SITE + "/",
            "sameAs": list(SHOW_SAME_AS),
        },
    }
    if ep.get("len"):
        # schema duration should be ISO 8601; we only have display lengths like '1h 04m'
        m = re.match(r"(?:(\d+)h\s*)?(\d+)m", str(ep["len"]).replace(" ", ""))
        if not m:
            m = re.match(r"(?:(\d+)h)?\s*(\d+)m", str(ep["len"]))
        if m:
            h = int(m.group(1) or 0)
            mins = int(m.group(2) or 0)
            data["duration"] = f"PT{h}H{mins}M" if h else f"PT{mins}M"
    if ep.get("num"):
        data["episodeNumber"] = int(ep["num"])
    if ep.get("image"):
        data["image"] = ep["image"]
    else:
        data["image"] = SITE + "/og-image.jpg"
    if ep.get("audio"):
        data["associatedMedia"] = {
            "@type": "MediaObject",
            "contentUrl": ep["audio"],
        }
    links = []
    if ep.get("apple_track_id"):
        links.append(apple_url(ep))
    if ep.get("spotify_episode_id"):
        links.append(spotify_url(ep))
    if ep.get("link"):
        links.append(ep["link"])
    for url in (IHEART, PODBEAN):
        if url not in links:
            links.append(url)
    if links:
        data["sameAs"] = links
    if not with_series:
        data.pop("partOfSeries", None)
    # drop Nones
    return {k: v for k, v in data.items() if v is not None}


def write_episode_page(ep, out_dir: Path):
    title = ep.get("title") or "Episode"
    num = ep.get("num")
    num_label = f"EP {num}" if num else "Latest episode"
    title_tag = f"{title}{f' ({num_label})' if num else ''} | The AEW-some Pod"
    desc = (ep.get("blurb_full") or ep.get("blurb") or "").strip()
    if not desc:
        desc = f"{title} — an episode of the AEW-some Pod, an All Elite Wrestling podcast hosted by Johnny Taylor, Diana Prince, and Gringo Fantastico."
    if len(desc) > 160:
        meta_desc = desc[:157].rsplit(" ", 1)[0] + "..."
    else:
        meta_desc = desc
    url = page_url(ep)
    img = SITE + "/og-image.jpg"
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Episodes", "item": SITE + "/#episodes"},
            {"@type": "ListItem", "position": 3, "name": title, "item": url},
        ],
    }
    ep_ld = {"@context": "https://schema.org", **episode_jsonld(ep)}
    listen_links = [
        f'<a class="btn red" href="{esc(apple_url(ep))}" target="_blank" rel="noopener">Apple Podcasts</a>',
        f'<a class="btn" href="{esc(spotify_url(ep))}" target="_blank" rel="noopener">Spotify</a>',
        f'<a class="btn" href="{esc(RSS)}" rel="noopener">RSS feed</a>',
        f'<a class="btn" href="{esc(IHEART)}" target="_blank" rel="noopener">iHeart</a>',
        f'<a class="btn" href="{esc(PODBEAN)}" target="_blank" rel="noopener">Podbean</a>',
    ]
    if ep.get("link"):
        listen_links.append(f'<a class="btn" href="{esc(ep["link"])}" target="_blank" rel="noopener">Show notes source</a>')

    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="google-site-verification" content="r4LDtyuGqt0kKYMNNoChUzqTSj-Rv2uqj12PwrfnfYI" />
<title>{esc(title_tag)}</title>
<meta name="description" content="{esc(meta_desc)}">
<link rel="canonical" href="{esc(url)}">
{HEAD_ICONS}
<meta property="og:type" content="article">
<meta property="og:site_name" content="The AEW-some Pod">
<meta property="og:title" content="{esc(title_tag)}">
<meta property="og:description" content="{esc(meta_desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="The AEW-some Pod logo — an All Elite Wrestling podcast">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title_tag)}">
<meta name="twitter:description" content="{esc(meta_desc)}">
<meta name="twitter:image" content="{img}">
<meta name="twitter:image:alt" content="The AEW-some Pod logo — an All Elite Wrestling podcast">
<script type="application/ld+json">
{json.dumps(ep_ld, indent=2, ensure_ascii=False)}
</script>
<script type="application/ld+json">
{json.dumps(crumbs, indent=2, ensure_ascii=False)}
</script>
</head>
<body class="page-episode">
<a class="skip" href="#notes">Skip to show notes</a>
{NAV}
<article class="ep-page">
  <nav class="crumbs" aria-label="Breadcrumb">
    <a href="/">Home</a>
    <span aria-hidden="true">/</span>
    <a href="/#episodes">Episodes</a>
    <span aria-hidden="true">/</span>
    <span>{esc(title)}</span>
  </nav>
  <p class="epnum">{esc(num_label)}</p>
  <h1>{esc(title)}</h1>
  <p class="meta">{esc("  ·  ".join(x for x in [ep.get("date"), ep.get("len")] if x).upper())}</p>
  <div class="embeds" id="player">
    {player_html(ep)}
  </div>
  <div class="links listen-ctas">
    {''.join(listen_links)}
  </div>
  <section id="notes" class="show-notes">
    <h2>Show notes</h2>
    {notes_html(ep)}
  </section>
  <p class="back"><a href="/#episodes">&larr; All episodes of the AEW-some Pod</a></p>
</article>
{FOOTER}
</body>
</html>
"""
    dest = out_dir / ep["slug"] / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html_page)
    return dest


def write_sitemap(episodes, dest: Path):
    urls = [
        (f"{SITE}/", "daily", "1.0", datetime.now(timezone.utc).date().isoformat()),
        (f"{SITE}/johnny", "monthly", "0.7", None),
        (f"{SITE}/diana", "monthly", "0.7", None),
        (f"{SITE}/gringo", "monthly", "0.7", None),
    ]
    for ep in episodes:
        last = (ep.get("date_iso") or "")[:10] or None
        urls.append((page_url(ep), "weekly", "0.8", last))
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, freq, pri, last in urls:
        parts.append("  <url>")
        parts.append(f"    <loc>{esc(loc)}</loc>")
        if last:
            parts.append(f"    <lastmod>{esc(last)}</lastmod>")
        parts.append(f"    <changefreq>{freq}</changefreq>")
        parts.append(f"    <priority>{pri}</priority>")
        parts.append("  </url>")
    parts.append("</urlset>")
    dest.write_text("\n".join(parts) + "\n")
    return len(urls)


def patch_home_episode_jsonld(episodes, index_path: Path, n=10):
    """Replace the marked JSON-LD block on the homepage with recent PodcastEpisode entries."""
    text = index_path.read_text()
    start = "<!-- EPISODE_JSONLD_START -->"
    end = "<!-- EPISODE_JSONLD_END -->"
    items = [episode_jsonld(ep) for ep in episodes[:n]]
    payload = {
        "@context": "https://schema.org",
        "@graph": items,
    }
    block = (
        f"{start}\n"
        f'<script type="application/ld+json">\n'
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n"
        f"</script>\n"
        f"{end}"
    )
    if start in text and end in text:
        text = re.sub(
            re.escape(start) + r".*?" + re.escape(end),
            lambda _: block,
            text,
            count=1,
            flags=re.S,
        )
    else:
        # insert before </head>
        text = text.replace("</head>", block + "\n</head>", 1)
    index_path.write_text(text)


def prune_episode_dirs(out_dir: Path, keep_slugs: set[str]):
    if not out_dir.exists():
        return
    for child in out_dir.iterdir():
        if child.is_dir() and child.name not in keep_slugs:
            html_file = child / "index.html"
            if html_file.exists():
                html_file.unlink()
            try:
                child.rmdir()
            except OSError:
                pass


def generate(payload: dict):
    episodes = payload.get("episodes") or []
    out_dir = ROOT / "episodes"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for ep in episodes:
        if not ep.get("slug"):
            continue
        write_episode_page(ep, out_dir)
        written += 1
    prune_episode_dirs(out_dir, {e["slug"] for e in episodes if e.get("slug")})
    count = write_sitemap(episodes, ROOT / "sitemap.xml")
    patch_home_episode_jsonld(episodes, ROOT / "index.html")
    print(f"Generated {written} episode pages and a sitemap with {count} URLs")
    return written, count


if __name__ == "__main__":
    data = json.loads((ROOT / "data" / "episodes.json").read_text())
    generate(data)
