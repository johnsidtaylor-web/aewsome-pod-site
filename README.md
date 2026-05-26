# The AEW-some Pod — Website

A self-maintaining static site for The AEW-some Pod. Episodes pull from your
Simplecast feed automatically. AEW news aggregates from 7 reputable sources,
filtered to AEW and deduped. A GitHub Actions cron refreshes both a few times
a day. No server, no database, no monthly bill.

## What's in here

```
index.html            Main page (loads data/*.json, falls back to samples)
johnny.html           Host page
diana.html            Host page
gringo.html           Host page
data/
  episodes.json       Auto-generated from your Simplecast feed
  news.json           Auto-generated AEW news wall
scripts/
  fetch_episodes.py   Parses the Simplecast RSS -> episodes.json
  fetch_news.py       Aggregates + filters + dedupes AEW news -> news.json
.github/workflows/
  refresh.yml         Cron that runs both scripts and commits the results
```

## One-time setup (about 5 minutes)

1. **Make a new GitHub repo** (public is fine, and required for free Pages).
   Name it whatever you want, e.g. `aewsome-pod-site`.

2. **Upload everything in this folder** to the repo. Either drag-and-drop in
   the GitHub web UI ("Add file" -> "Upload files"), or if you're comfy with
   git:
   ```
   git init
   git add .
   git commit -m "initial site"
   git branch -M main
   git remote add origin https://github.com/YOURNAME/aewsome-pod-site.git
   git push -u origin main
   ```

3. **Turn on GitHub Pages.** Repo -> Settings -> Pages -> under "Build and
   deployment", set Source to "Deploy from a branch", branch `main`, folder
   `/ (root)`. Save. After a minute your site is live at
   `https://YOURNAME.github.io/aewsome-pod-site/`.

4. **Let the cron run once.** Go to the Actions tab, click "Refresh feed
   data", then "Run workflow". This pulls your real episodes and the live AEW
   news for the first time. After that it runs on its own ~6x/day.

That's it. The site is live and self-updating.

## Hooking up your own domain (optional)

If you've got a domain (e.g. `aewsomepod.com`): Settings -> Pages -> Custom
domain, type it in, then add the DNS records GitHub shows you at your registrar.

## The news sources

The scraper pulls from: Fightful, Wrestling Observer (F4W), PWTorch, POST
Wrestling, PWInsider, Wrestling Inc, and ProWrestling.net — chosen for actual
reporting credibility, not rumor-mill traffic. It keeps headline + source +
link + a short blurb and **always links back to the original article**. It
never republishes full stories.

### If a news source stops showing up

Feeds occasionally change URLs. After the first run, open the Actions log — it
prints a status line per source (e.g. `Fightful: ok (8 AEW items)` or
`Fightful: FAILED`). If one says FAILED, the feed URL moved. Find the new RSS
URL (usually linked in the site's footer or at `/feed`, `/rss`) and update it
in `scripts/fetch_news.py` in the `SOURCES` list. The other sources keep
working in the meantime.

### Tuning the AEW filter

`scripts/fetch_news.py` has an `AEW_KEYWORDS` list (loose by default, catches
roster names + show names) and a `WWE_ONLY_HINTS` list that drops obvious
WWE-only stories. Add or remove keywords there to tighten or loosen the wall.

## Adding a blog/column post

Hand Johnny the text and he drops it into the posts array in `index.html`
(search for `const posts=[`). Each post is:
```js
{who:"Diana Prince", init:"DP", grad:"...", col:"...", date:"MAY 23, 2026",
 title:"Your headline", body:"The text..."}
```

## Updating a host's tour dates or socials

Host pages are plain HTML. Tour dates currently say "STAY TUNED" — search a
host file (e.g. `diana.html`) for `STAY TUNED` and replace with real dates.
Socials are already wired.

## Notes

- The featured player on `index.html` is currently a styled placeholder.
  To drop in real Apple/Spotify embeds, replace the contents of `#embApple`
  and `#embSpot` with the iframe embed code from each platform for your show.
- Episode numbers are pulled from episode titles. If a title has no number,
  the site just hides the number rather than guessing.
