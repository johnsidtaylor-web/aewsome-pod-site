(() => {
  const APPLE_SHOW = "https://podcasts.apple.com/us/podcast/the-aew-some-pod-w-johnny-taylor-diana-prince-gringo/id1655190709";
  const SPOTIFY_SHOW = "https://open.spotify.com/show/7wOoXA1zgghRv25SbOSu7h";
  const COVER_FALLBACK = "assets/cover-art-176.jpg";
  const APPLE_SHOW_ID = "1655190709";
  const ITUNES_LOOKUP = "https://itunes.apple.com/lookup?id=" + APPLE_SHOW_ID + "&entity=podcastEpisode&limit=5";
  const APPLE_EMBED_FALLBACK = {
    trackId: 1000802416423,
    slug: "sparkling-death",
    title: "Sparkling Death",
    release: "2026-11-17T06:22:00Z"
  };
  const SPOTIFY_EMBED_FALLBACK = {
    episodeId: "5FNPKvGgOUFDv9TVFf4NS7",
    title: "Sparkling Death"
  };

  const FALLBACK_NEWS = [
    {src:"Fightful",t:"2h",h:"Backstage notes on AEW's Forbidden Door build",p:"Sources indicate creative has mapped the next three weeks of Dynamite around the interpromotional card, with one title match already locked."},
    {src:"Wrestling Observer",t:"4h",h:"Meltzer: Multiple NJPW names cleared for Collision",p:"At least four New Japan talents are expected for the upcoming west-coast taping cycle according to the latest Observer Radio."},
    {src:"PWTorch",t:"6h",h:"Keller's Dynamite report: three segments that overdelivered",p:"This week's show leaned hard on long-form promo work, and two of the three main feuds advanced cleanly heading into the PPV."},
    {src:"POST Wrestling",t:"9h",h:"Pollock & Thurston on AEW's media rights timeline",p:"The business implications of the WBD situation and what a Paramount pivot could mean for All Elite's TV future."},
    {src:"PWInsider",t:"11h",h:"Live event attendance trending up for spring loop",p:"House show numbers from the last two weeks show a notable uptick in the southeast markets."},
    {src:"Wrestling Inc",t:"14h",h:"Former champion teases return in cryptic post",p:"A social post from a name off TV since last fall has fans speculating about a surprise return."},
    {src:"ProWrestling.net",t:"18h",h:"Full results: AEW Collision spoilers from taping",p:"Complete match-by-match results behind a spoiler tag, including a title change fans didn't see coming."},
    {src:"Fightful",t:"21h",h:"Signing update: AEW finalizes multi-year deal",p:"A talent whose contract was reportedly expiring has put pen to paper on a new long-term agreement."},
    {src:"Wrestling Observer",t:"1d",h:"Ratings: Dynamite holds steady in key demo",p:"Week-over-week the show retained its core audience despite tough sports counterprogramming."}
  ];
  const FALLBACK_EPISODES = [
    {n:256,title:"Sparkling Death",date:"Nov 17, 2026",len:"1h 04m"},
    {n:223,title:"Okada vs. Takeshita & The Callis Family Powder Keg",date:"May 22, 2026",len:"1h 12m"},
    {n:222,title:"Sacramento Goes Home: Swerve Hangs Omega",date:"May 19, 2026",len:"1h 18m"},
    {n:221,title:"Sisters of Sin & The Tag Title Tournament Heats Up",date:"May 15, 2026",len:"1h 04m"},
    {n:220,title:"Blood & Guts Build Begins (We Are Not Okay)",date:"May 12, 2026",len:"58m"},
    {n:219,title:"The One Where We Argue About Star Ratings",date:"May 8, 2026",len:"1h 02m"},
    {n:218,title:"FTR's Honorable Loss & Moxley's Briefcase of Doom",date:"May 5, 2026",len:"1h 11m"},
    {n:217,title:"Double Or Nothing Fallout + Mailbag Chaos",date:"May 1, 2026",len:"1h 28m"}
  ];
  const posts = [];

  function esc(s){
    return String(s ?? "").replace(/[&<>"']/g, c => ({
      "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"
    }[c]));
  }

  function epNum(e){
    if (e && (e.num !== undefined && e.num !== null && e.num !== "")) return e.num;
    if (e && (e.n !== undefined && e.n !== null && e.n !== "")) return e.n;
    const blob = ((e && e.title) || "") + " " + ((e && (e.blurb_full || e.blurb)) || "");
    const m = blob.match(/\b(?:episode|ep\.?)\s*#?\s*(\d{1,4})\b/i);
    return m ? m[1] : null;
  }

  function epArt(e){
    return (e && e.image) ? e.image : COVER_FALLBACK;
  }

  function cleanTitle(title){
    return String(title || "").replace(/^Episode\s*\d+:?\s*/i, "");
  }

  function appleEmbedUrl(slug, trackId){
    const s = encodeURIComponent(slug || APPLE_EMBED_FALLBACK.slug);
    return "https://embed.podcasts.apple.com/us/podcast/" + s + "/id" + APPLE_SHOW_ID + "?i=" + encodeURIComponent(String(trackId)) + "&theme=dark";
  }

  function spotifyEmbedUrl(episodeId){
    return "https://open.spotify.com/embed/episode/" + encodeURIComponent(episodeId) + "?utm_source=generator&theme=0";
  }

  function setNowPlaying(title){
    const np = document.getElementById("nowPlaying");
    const name = cleanTitle(title);
    if (np) np.textContent = name ? ("Now Playing: " + name) : "Now Playing";
  }

  function setAppleEmbed(info){
    const frame = document.getElementById("appleFrame");
    if (!frame || !info || !info.trackId) return;
    const slug = info.slug || APPLE_EMBED_FALLBACK.slug;
    const url = appleEmbedUrl(slug, info.trackId);
    if (frame.getAttribute("src") !== url) frame.setAttribute("src", url);
    frame.dataset.trackId = String(info.trackId);
    frame.dataset.slug = slug;
    if (info.release) frame.dataset.release = info.release;
    const label = cleanTitle(info.title) || "Latest episode";
    frame.setAttribute("title", label + " on Apple Podcasts");
  }

  function setSpotifyEmbed(info){
    const frame = document.getElementById("spotifyFrame");
    if (!frame || !info || !info.episodeId) return;
    const url = spotifyEmbedUrl(info.episodeId);
    if (frame.getAttribute("src") !== url) frame.setAttribute("src", url);
    frame.dataset.episodeId = info.episodeId;
    const label = cleanTitle(info.title) || "Latest episode";
    frame.setAttribute("title", label + " on Spotify");
  }

  function applyBakedEmbeds(embeds){
    if (!embeds) return;
    const appleId = embeds.apple_track_id;
    if (appleId){
      setAppleEmbed({
        trackId: appleId,
        slug: embeds.apple_slug,
        title: embeds.apple_title,
        release: embeds.apple_release
      });
      if (embeds.apple_title) setNowPlaying(embeds.apple_title);
    }
    if (embeds.spotify_episode_id){
      setSpotifyEmbed({
        episodeId: embeds.spotify_episode_id,
        title: embeds.spotify_title
      });
    }
  }

  function isNewerRelease(nextIso, currentIso){
    const next = Date.parse(nextIso || "");
    if (isNaN(next)) return false;
    const cur = Date.parse(currentIso || "");
    if (isNaN(cur)) return true;
    return next > cur;
  }

  function pickLatestAppleEpisode(data){
    const rows = (data && data.results) || [];
    const eps = rows.filter(r => r && r.wrapperType === "podcastEpisode");
    eps.sort((a, b) => String(b.releaseDate || "").localeCompare(String(a.releaseDate || "")));
    return eps[0] || null;
  }

  function slugFromAppleViewUrl(url){
    const m = String(url || "").match(/\/podcast\/([^/]+)\/id\d+/);
    return m ? m[1] : "";
  }

  function itunesJsonp(url){
    return new Promise((resolve, reject) => {
      const cb = "itunesCb" + Date.now() + Math.floor(Math.random() * 1000);
      const script = document.createElement("script");
      let done = false;
      const finish = (fn, val) => {
        if (done) return;
        done = true;
        try { delete window[cb]; } catch (e) { window[cb] = undefined; }
        if (script.parentNode) script.parentNode.removeChild(script);
        fn(val);
      };
      window[cb] = data => finish(resolve, data);
      script.onerror = () => finish(reject, new Error("iTunes JSONP failed"));
      script.src = url + (url.indexOf("?") >= 0 ? "&" : "?") + "callback=" + cb;
      document.head.appendChild(script);
      setTimeout(() => finish(reject, new Error("iTunes JSONP timeout")), 8000);
    });
  }

  async function fetchItunesLookup(){
    try {
      const res = await fetch(ITUNES_LOOKUP, { mode: "cors" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      return await res.json();
    } catch (err) {
      return itunesJsonp(ITUNES_LOOKUP);
    }
  }

  async function refreshAppleEmbed(){
    const frame = document.getElementById("appleFrame");
    const currentId = frame && frame.dataset.trackId ? frame.dataset.trackId : String(APPLE_EMBED_FALLBACK.trackId);
    const currentRelease = (frame && frame.dataset.release) || APPLE_EMBED_FALLBACK.release;
    try {
      const data = await fetchItunesLookup();
      const ep = pickLatestAppleEpisode(data);
      if (!ep || !ep.trackId) return;
      const nextId = String(ep.trackId);
      if (nextId === currentId) return;
      if (!isNewerRelease(ep.releaseDate, currentRelease)) return;
      const title = ep.trackName || "";
      setAppleEmbed({
        trackId: nextId,
        slug: slugFromAppleViewUrl(ep.trackViewUrl) || APPLE_EMBED_FALLBACK.slug,
        title,
        release: ep.releaseDate
      });
      if (title){
        setNowPlaying(title);
        const titleEl = document.querySelector(".feat .ftxt h3");
        if (titleEl) titleEl.textContent = cleanTitle(title);
        const artEl = document.getElementById("featArt");
        if (artEl) artEl.alt = cleanTitle(title) + " cover art";
      }
    } catch (err) {
      // Keep the baked / hardcoded episode embed.
    }
  }

  function relTime(iso){
    if (!iso) return "";
    const then = new Date(iso); if (isNaN(then)) return "";
    const secs = (Date.now() - then.getTime()) / 1000;
    if (secs < 60) return "just now";
    if (secs < 3600) return Math.floor(secs / 60) + "m ago";
    if (secs < 86400) return Math.floor(secs / 3600) + "h ago";
    return Math.floor(secs / 86400) + "d ago";
  }

  let activeSrc = "ALL";
  let news = FALLBACK_NEWS;
  let episodes = FALLBACK_EPISODES;
  let epsExpanded = false;
  const EP_LIMIT = 6;

  function renderNews(){
    const search = document.getElementById("search");
    const wall = document.getElementById("wall");
    if (!wall) return;
    const q = (search ? search.value : "").toLowerCase();
    wall.innerHTML = "";
    const f = news.filter(n => (activeSrc === "ALL" || n.src === activeSrc) && (!q || (n.h + " " + n.p).toLowerCase().includes(q)));
    const count = document.getElementById("newscount");
    if (count) count.textContent = f.length + " STORIES";
    if (!f.length){ wall.innerHTML = "<p class='empty'>No stories match that search.</p>"; return; }
    f.forEach(n => {
      const d = document.createElement("div");
      d.className = "clip";
      const url = n.link || "#";
      const tt = relTime(n.dt) || (n.t ? (n.t + " ago") : "");
      d.innerHTML = "<div class='src'><span>" + esc(n.src) + "</span><span class='time'>" + esc(tt) + "</span></div><h3>" + esc(n.h) + "</h3><p>" + esc(n.p) + "</p><a class='read' target='_blank' rel='noopener' href='" + esc(url) + "'>Read at " + esc(n.src) + "</a>";
      wall.appendChild(d);
    });
  }

  function renderEps(){
    const box = document.getElementById("eps");
    const search = document.getElementById("epsearch");
    if (!box) return;
    const q = (search ? search.value : "").toLowerCase();
    box.innerHTML = "";
    const all = episodes.filter(e => !q || (e.title + " " + (e.blurb || "")).toLowerCase().includes(q));
    const count = document.getElementById("epcount");
    if (count) count.textContent = all.length + " EPISODES";
    const f = (q || epsExpanded) ? all : all.slice(0, EP_LIMIT);
    f.forEach(e => {
      const d = document.createElement("article");
      d.className = "epcard";
      const num = epNum(e);
      const title = cleanTitle(e.title);
      const art = epArt(e);
      const meta = [e.date, e.len].filter(Boolean).join(" · ");
      const page = e.slug ? ("/episodes/" + encodeURIComponent(e.slug) + "/") : (e.link || "#listen");
      const appleHref = e.apple_track_id
        ? ("https://podcasts.apple.com/us/podcast/" + encodeURIComponent(e.apple_slug || e.slug || "episode") + "/id1655190709?i=" + encodeURIComponent(e.apple_track_id))
        : APPLE_SHOW;
      const spotHref = e.spotify_episode_id
        ? ("https://open.spotify.com/episode/" + encodeURIComponent(e.spotify_episode_id))
        : SPOTIFY_SHOW;
      d.innerHTML =
        "<img src='" + esc(art) + "' alt='" + esc(title) + " cover art' width='72' height='72' loading='lazy'>" +
        "<div><span class='epn'>" + (num ? ("EP " + esc(num)) : "") + "</span><h3><a href='" + esc(page) + "'>" + esc(title) + "</a></h3><div class='epmeta'>" + esc(meta) + "</div></div>" +
        "<div class='eplinks'>" +
          "<a href='" + esc(appleHref) + "' target='_blank' rel='noopener' title='Listen on Apple Podcasts'>APPLE</a>" +
          "<a class='sp' href='" + esc(spotHref) + "' target='_blank' rel='noopener' title='Listen on Spotify'>SPOTIFY</a>" +
        "</div>";
      box.appendChild(d);
    });
    if (!q && all.length > EP_LIMIT){
      const btn = document.createElement("button");
      btn.className = "btn more-btn";
      btn.type = "button";
      btn.textContent = epsExpanded ? "↑ Show Less" : ("View All " + all.length + " Episodes ↓");
      btn.addEventListener("click", () => {
        epsExpanded = !epsExpanded;
        renderEps();
        if (!epsExpanded) document.getElementById("episodes").scrollIntoView({behavior:"smooth"});
      });
      box.appendChild(btn);
    }
  }

  function renderRecent(){
    const rec = document.getElementById("recent");
    if (!rec) return;
    rec.innerHTML = "";
    episodes.slice(1, 4).forEach(e => {
      const a = document.createElement("a");
      a.className = "rcard";
      a.href = e.slug ? ("/episodes/" + encodeURIComponent(e.slug) + "/") : (e.link || "#listen");
      if (!e.slug && e.link){ a.target = "_blank"; a.rel = "noopener"; }
      const num = epNum(e);
      a.innerHTML =
        "<img src='" + esc(epArt(e)) + "' alt='" + esc(cleanTitle(e.title)) + " cover art' width='56' height='56' loading='lazy'>" +
        "<div>" + (num ? "<div class='n'>" + esc(num) + "</div>" : "") +
        "<h4>" + esc(cleanTitle(e.title)) + "</h4>" +
        "<div class='d'>" + esc([e.date, e.len].filter(Boolean).join(" · ")) + "</div></div>";
      rec.appendChild(a);
    });
  }

  function renderTicker(){
    const tk = document.getElementById("tk");
    if (!tk) return;
    const bits = ["THE AEW-SOME POD", "PRESENTED BY KALSHI", "DYNAMITE · COLLISION · EVERY PPV", "JOHNNY · DIANA · GRINGO"];
    news.slice(0, 8).forEach(n => {
      if (n && n.h) bits.push((n.src ? n.src + ": " : "") + n.h);
    });
    const unit = bits.map((b, i) => {
      const klass = /kalshi/i.test(b) ? "k" : "";
      return (i ? "<span class='dot'>●</span>" : "") + "<b class='" + klass + "'>" + esc(b) + "</b>";
    }).join("");
    tk.innerHTML = unit + unit;
  }

  function rebuildChips(){
    const chipWrap = document.getElementById("chips");
    if (!chipWrap) return;
    const sources = [...new Set(news.map(n => n.src))];
    chipWrap.innerHTML = "";
    ["ALL", ...sources].forEach(s => {
      const c = document.createElement("button");
      c.type = "button";
      c.className = "chip" + (s === activeSrc ? " on" : "");
      c.textContent = s;
      c.setAttribute("aria-pressed", s === activeSrc ? "true" : "false");
      c.addEventListener("click", () => {
        activeSrc = s;
        document.querySelectorAll(".chip").forEach(x => {
          x.classList.remove("on");
          x.setAttribute("aria-pressed", "false");
        });
        c.classList.add("on");
        c.setAttribute("aria-pressed", "true");
        renderNews();
      });
      chipWrap.appendChild(c);
    });
  }

  function updateFeatured(ep){
    if (!ep) return;
    const numEl = document.querySelector(".feat .epnum");
    const titleEl = document.querySelector(".feat .ftxt h3");
    const metaEl = document.querySelector(".feat .ftxt .meta");
    const pEl = document.querySelector(".feat .ftxt p");
    const artEl = document.getElementById("featArt");
    const num = epNum(ep);
    if (numEl) numEl.textContent = num ? ("EPISODE " + num) : "LATEST EPISODE";
    if (titleEl) titleEl.textContent = cleanTitle(ep.title);
    if (metaEl) metaEl.textContent = [ep.date, ep.len].filter(Boolean).join("  ·  ").toUpperCase();
    if (pEl) pEl.textContent = ep.blurb_full || ep.blurb || pEl.textContent;
    if (artEl){
      artEl.src = epArt(ep);
      artEl.alt = cleanTitle(ep.title) + " cover art";
    }
    setNowPlaying(ep.title);
  }

  async function loadData(){
    try{
      const [nRes, eRes] = await Promise.allSettled([
        fetch("data/news.json?" + Date.now()),
        fetch("data/episodes.json?" + Date.now())
      ]);
      if (nRes.status === "fulfilled" && nRes.value.ok){
        const nd = await nRes.value.json();
        if (nd.items && nd.items.length) news = nd.items;
      }
      if (eRes.status === "fulfilled" && eRes.value.ok){
        const ed = await eRes.value.json();
        if (ed.episodes && ed.episodes.length){
          episodes = ed.episodes;
          updateFeatured(episodes[0]);
        }
        applyBakedEmbeds(ed.latest_embeds);
      }
    } catch (err) { /* keep fallbacks */ }
    rebuildChips();
    renderNews();
    renderEps();
    renderRecent();
    renderTicker();
    refreshAppleEmbed();
  }

  function swEmbed(which){
    const a = which === "apple";
    const appleBox = document.getElementById("embApple");
    const spotBox = document.getElementById("embSpot");
    const tabApple = document.getElementById("tabApple");
    const tabSpot = document.getElementById("tabSpot");
    if (!appleBox || !spotBox || !tabApple || !tabSpot) return;
    appleBox.style.display = a ? "block" : "none";
    spotBox.style.display = a ? "none" : "block";
    appleBox.hidden = !a;
    spotBox.hidden = a;
    appleBox.setAttribute("aria-hidden", a ? "false" : "true");
    spotBox.setAttribute("aria-hidden", a ? "true" : "false");
    tabApple.classList.toggle("on", a);
    tabSpot.classList.toggle("on", !a);
    tabApple.setAttribute("aria-selected", a ? "true" : "false");
    tabSpot.setAttribute("aria-selected", a ? "false" : "true");
    tabApple.tabIndex = a ? 0 : -1;
    tabSpot.tabIndex = a ? -1 : 0;
  }

  function wireTabs(){
    const tabs = [document.getElementById("tabApple"), document.getElementById("tabSpot")];
    if (!tabs[0] || !tabs[1]) return;
    tabs.forEach((tab, i) => {
      tab.addEventListener("click", () => swEmbed(i === 0 ? "apple" : "spotify"));
      tab.addEventListener("keydown", ev => {
        const keys = {ArrowLeft: -1, ArrowRight: 1, Home: "start", End: "end"};
        if (!(ev.key in keys)) return;
        ev.preventDefault();
        let idx = i;
        if (keys[ev.key] === "start") idx = 0;
        else if (keys[ev.key] === "end") idx = tabs.length - 1;
        else idx = (i + keys[ev.key] + tabs.length) % tabs.length;
        tabs[idx].focus();
        swEmbed(idx === 0 ? "apple" : "spotify");
      });
    });
    swEmbed("apple");
  }

  let menuBusy = false;
  function toggleMenu(e){
    if (e) e.stopPropagation();
    if (menuBusy) return;
    menuBusy = true;
    setTimeout(() => { menuBusy = false; }, 350);
    const links = document.querySelector(".navlinks");
    const ham = document.getElementById("hamburger");
    const bd = document.getElementById("menuBackdrop");
    if (!links || !ham) return;
    const open = links.classList.toggle("open");
    ham.classList.toggle("open", open);
    if (bd) bd.classList.toggle("open", open);
    ham.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.style.overflow = open ? "hidden" : "";
    if (open){
      const first = links.querySelector("a");
      if (first) first.focus();
    }
  }

  window.toggleMenu = toggleMenu;
  window.swEmbed = swEmbed;

  document.addEventListener("DOMContentLoaded", () => {
    const epsearch = document.getElementById("epsearch");
    const search = document.getElementById("search");
    if (epsearch) epsearch.addEventListener("input", renderEps);
    if (search) search.addEventListener("input", renderNews);

    wireTabs();

    document.querySelectorAll(".navlinks a").forEach(a => a.addEventListener("click", () => {
      const links = document.querySelector(".navlinks");
      if (links && links.classList.contains("open")) toggleMenu();
    }));

    document.addEventListener("keydown", ev => {
      if (ev.key === "Escape"){
        const links = document.querySelector(".navlinks");
        if (links && links.classList.contains("open")){
          toggleMenu();
          const ham = document.getElementById("hamburger");
          if (ham) ham.focus();
        }
      }
    });

    const btt = document.getElementById("backToTop");
    if (btt){
      const onScroll = () => { btt.classList.toggle("show", window.scrollY > 500); };
      window.addEventListener("scroll", onScroll, {passive:true});
      onScroll();
    }

    loadData();
  });
})();
