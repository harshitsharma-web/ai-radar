// AI Radar front-end: loads data/feed.json (written daily by scripts/fetch.py) and renders the views.

const state = { data: null, byId: {}, q: "", feed: { range: 3, kind: "all", topic: "", company: "", limit: 60 },
  research: { tab: "hot", topic: "", limit: 60 } };
const LAB_SOURCES = ["OpenAI", "Anthropic", "Anthropic Research", "Google DeepMind", "Google AI", "Google Research", "Meta AI",
  "Mistral", "NVIDIA", "Microsoft Research", "Apple ML Research", "Hugging Face", "AWS Machine Learning", "Berkeley AI Research"];
const KINDS = { all: "All", lab: "Labs", news: "News", newsletter: "Newsletters", community: "Community", research: "Research blogs", paper: "Papers" };
const $ = (s) => document.querySelector(s);

// ---------- utils ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const hoursAgo = (iso) => (Date.now() - new Date(iso).getTime()) / 36e5;
function ago(iso) {
  const h = hoursAgo(iso);
  if (h < 1) return `${Math.max(1, Math.round(h * 60))}m ago`;
  if (h < 24) return `${Math.round(h)}h ago`;
  const d = Math.round(h / 24);
  return d < 30 ? `${d}d ago` : new Date(iso).toLocaleDateString();
}
const fmtNum = (n) => n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : String(n ?? 0);
const fmtDate = (d) => new Date(d + "T12:00:00Z").toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

function store(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}
function save(key, val) { try { localStorage.setItem(key, JSON.stringify(val)); } catch { /* storage unavailable */ } }
let saved = store("radar.saved", {});

function matchesQuery(it) {
  if (!state.q) return true;
  const hay = `${it.title} ${it.summary} ${it.source} ${(it.companies || []).join(" ")} ${(it.topics || []).join(" ")} ${(it.authors || []).join(" ")}`.toLowerCase();
  return state.q.toLowerCase().split(/\s+/).every((w) => hay.includes(w));
}

// tiny markdown for the AI brief: headings, bullets, bold, links (input is escaped first)
function md(text) {
  const inline = (s) => esc(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, (_, t, u) => `<a href="${u}" target="_blank" rel="noopener">${t}</a>`);
  let out = "", inList = false;
  for (const line of text.split("\n")) {
    const l = line.trim();
    if (/^[-*] /.test(l)) { if (!inList) { out += "<ul>"; inList = true; } out += `<li>${inline(l.slice(2))}</li>`; continue; }
    if (inList) { out += "</ul>"; inList = false; }
    if (/^#{1,3} /.test(l)) out += `<h3>${inline(l.replace(/^#+ /, ""))}</h3>`;
    else if (l) out += `<p>${inline(l)}</p>`;
  }
  return out + (inList ? "</ul>" : "");
}

// ---------- pieces ----------
const starIcon = '<svg viewBox="0 0 24 24"><path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>';
const starBtn = (it) => `<button class="star ${saved[it.id] ? "on" : ""}" data-star="${it.id}" title="Save" aria-label="Save">${starIcon}</button>`;

function tagsHtml(it, max = 4) {
  const co = (it.companies || []).slice(0, max).map((c) => `<button class="tag co" data-company="${esc(c)}">${esc(c)}</button>`);
  const tp = (it.topics || []).slice(0, 3).map((t) => `<button class="tag" data-topic="${esc(t)}">${esc(t)}</button>`);
  return co.length || tp.length ? `<div class="tags">${co.join("")}${tp.join("")}</div>` : "";
}

function itemHtml(it) {
  const links = it.kind === "paper" && it.arxiv ? ` · <a href="${esc(it.arxiv)}" target="_blank" rel="noopener">arXiv</a>` : "";
  return `<div class="item">${starBtn(it)}<div class="body">
    <a class="title" href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a>
    <div class="meta">${metaParts(it).join(" · ")}${links}</div>
    ${it.summary ? `<div class="summary">${esc(it.summary)}</div>` : ""}
    ${tagsHtml(it)}</div></div>`;
}

function metaParts(it) {
  const p = [`<span class="kind ${it.kind}">${esc(kindLabel(it.kind))}</span> ${esc(it.source)}`, ago(it.published)];
  if (it.points) p.push(`<a class="hot" href="${esc(it.discussion)}" target="_blank" rel="noopener">▲ ${it.points} · ${it.comments || 0} comments</a>`);
  if (it.upvotes) p.push(`<span class="hot">▲ ${it.upvotes}</span>`);
  if (it.org) p.push(esc(it.org));
  if (it.kind === "paper" && it.authors?.length) p.push(esc(it.authors.slice(0, 3).join(", ") + (it.authors.length > 3 ? " et al." : "")));
  return p;
}
const kindLabel = (k) => ({ lab: "Lab", news: "News", newsletter: "Newsletter", community: "Community", research: "Research", paper: "Paper" }[k] || k);

function miniHtml(it, extra = "") {
  return `<div class="mini"><a class="title" href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a>
    <div class="meta">${esc(it.source)} · ${ago(it.published)}${extra}</div></div>`;
}

function list(items, limit) {
  if (!items.length) return `<div class="empty">Nothing matches. Try a wider time range or clear the filters.</div>`;
  const more = items.length > limit ? `<button class="chip loadmore" data-more>Show more (${items.length - limit} left)</button>` : "";
  return `<div class="panel pad" style="padding-top:2px;padding-bottom:2px">${items.slice(0, limit).map(itemHtml).join("")}</div>${more}`;
}

// ---------- views ----------
function viewToday() {
  const d = state.data, brief = d.briefs?.[0];
  const stories = d.top.map((s) => ({ ...s, it: state.byId[s.lead] })).filter((s) => s.it && matchesQuery(s.it));
  const storyHtml = stories.map((s, i) => {
    const rel = s.related.map((id) => state.byId[id]).filter(Boolean);
    const relHtml = rel.length ? `<details><summary>+ ${rel.length} more ${rel.length === 1 ? "story" : "stories"} on this</summary><ul class="related">${rel.map((r) =>
      `<li><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a> <span class="meta" style="display:inline">· ${esc(r.source)}</span></li>`).join("")}</ul></details>` : "";
    const outlets = s.sources.length > 1 ? `<span class="hot">${s.sources.length} outlets</span>` : "";
    return `<div class="story"><div class="rank">${i + 1}</div><div>
      <a class="title" href="${esc(s.it.url)}" target="_blank" rel="noopener">${esc(s.it.title)}</a>
      <div class="meta">${metaParts(s.it).join(" · ")}${outlets ? " · " + outlets : ""}</div>
      ${s.it.summary ? `<div class="summary">${esc(s.it.summary)}</div>` : ""}
      ${tagsHtml(s.it)}${relHtml}</div></div>`;
  }).join("");

  const labs = d.items.filter((i) => LAB_SOURCES.includes(i.source) && i.weight >= 2 && hoursAgo(i.published) < 24 * 7 && matchesQuery(i)).slice(0, 8);
  const papers = d.papers.map((id) => state.byId[id]).filter((p) => p && matchesQuery(p)).slice(0, 6);
  const models = d.models.slice(0, 6);

  return `<h1 class="page">${brief ? fmtDate(brief.date) : "Today"}</h1>
    <p class="sub">What's happening in AI right now. Updated automatically every morning from ${d.health.length} sources.</p>
    <div class="grid"><div>
      ${brief?.ai_summary && !state.q ? `<h2 class="sec">Daily brief</h2><div class="panel brief"><span class="brief-tag">Written by Claude from today's sources</span>${md(brief.ai_summary)}</div>` : ""}
      <h2 class="sec">Top stories · last 36 hours <a class="more" href="#feed">All news →</a></h2>
      <div class="panel pad" style="padding-top:0;padding-bottom:0">${storyHtml || '<div class="empty">No matching stories.</div>'}</div>
    </div>
    <aside class="side">
      <h2 class="sec">From the labs <a class="more" href="#labs">All →</a></h2>
      <div class="panel">${labs.map((i) => miniHtml(i)).join("") || '<div class="empty">Nothing this week.</div>'}</div>
      <h2 class="sec">Trending papers <a class="more" href="#research">All →</a></h2>
      <div class="panel">${papers.map((p) => miniHtml(p, ` · <span class="hot">▲ ${p.upvotes}</span>`)).join("")}</div>
      <h2 class="sec">Trending open models <a class="more" href="#models">All →</a></h2>
      <div class="panel">${models.map((m) => `<div class="mini"><a class="title" href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.id)}</a>
        <div class="meta">${esc(m.task || "model")} · ♥ ${fmtNum(m.likes)} · ↓ ${fmtNum(m.downloads)}</div></div>`).join("")}</div>
    </aside></div>`;
}

function chips(options, current, attr) {
  return options.map(([v, label]) => `<button class="chip ${String(current) === String(v) ? "on" : ""}" data-${attr}="${esc(v)}">${esc(label)}</button>`).join("");
}

function viewFeed() {
  const f = state.feed, d = state.data;
  const items = d.items.filter((i) => hoursAgo(i.published) <= f.range * 24
    && (f.kind === "all" ? i.kind !== "paper" : i.kind === f.kind)
    && (!f.topic || i.topics.includes(f.topic)) && (!f.company || i.companies.includes(f.company)) && matchesQuery(i));
  return `<h1 class="page">Feed</h1><p class="sub">Every story from labs, news sites, newsletters and the community, newest first.</p>
    <div class="filters">
      <div class="frow"><span>When</span>${chips([[1, "24 hours"], [3, "3 days"], [7, "7 days"], [30, "30 days"]], f.range, "range")}</div>
      <div class="frow"><span>Type</span>${chips(Object.entries(KINDS), f.kind, "kind")}</div>
      <div class="frow"><span>Filter</span>
        <select class="chip" data-sel="company"><option value="">All companies</option>${d.companies.map((c) => `<option ${c === f.company ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
        <select class="chip" data-sel="topic"><option value="">All topics</option>${d.topics.map((t) => `<option ${t === f.topic ? "selected" : ""}>${esc(t)}</option>`).join("")}</select>
        ${f.company || f.topic ? `<button class="chip" data-clear>Clear</button>` : ""}
      </div>
    </div>
    <p class="count">${items.length} items</p>${list(items, f.limit)}`;
}

function viewLabs() {
  const groups = {};
  for (const i of state.data.items) {
    if (!LAB_SOURCES.includes(i.source) || !matchesQuery(i)) continue;
    const key = i.source.replace(/ Research$/, "").replace("Google AI", "Google DeepMind");
    (groups[key] ||= []).push(i);
  }
  const order = Object.entries(groups).sort((a, b) => b[1][0].published.localeCompare(a[1][0].published));
  return `<h1 class="page">Labs</h1><p class="sub">Official announcements and research posts from the major AI labs, last 30 days. Most recently active first.</p>
    <div class="lab-cols">${order.map(([name, its]) => `<div class="panel"><h3>${esc(name)} <small>${its.length} posts · latest ${ago(its[0].published)}</small></h3>
      ${its.slice(0, 6).map((i) => miniHtml(i)).join("")}</div>`).join("")}</div>`;
}

function viewResearch() {
  const r = state.research, d = state.data;
  let items = d.items.filter((i) => (r.tab === "blogs" ? i.kind === "research" : i.kind === "paper") && matchesQuery(i));
  if (r.tab === "hot") items = items.filter((i) => i.source === "HF Daily Papers").sort((a, b) => (b.upvotes || 0) - (a.upvotes || 0));
  if (r.tab === "arxiv") items = items.filter((i) => i.source === "arXiv");
  if (r.topic) items = items.filter((i) => i.topics.includes(r.topic));
  const topics = d.topics.filter((t) => t !== "Research");
  return `<h1 class="page">Research</h1><p class="sub">Papers the community is upvoting, the newest arXiv papers in AI, and research posts from the labs.</p>
    <div class="filters">
      <div class="frow"><span>Show</span>${chips([["hot", "Trending papers"], ["arxiv", "Latest arXiv"], ["blogs", "Lab research blogs"]], r.tab, "rtab")}</div>
      <div class="frow"><span>Topic</span><select class="chip" data-sel="rtopic"><option value="">All topics</option>${topics.map((t) => `<option ${t === r.topic ? "selected" : ""}>${esc(t)}</option>`).join("")}</select></div>
    </div><p class="count">${items.length} items</p>${list(items, r.limit)}`;
}

function viewModels() {
  const d = state.data;
  const models = d.models.filter((m) => !state.q || `${m.id} ${m.task}`.toLowerCase().includes(state.q.toLowerCase()));
  const repos = d.repos.filter((r) => !state.q || `${r.name} ${r.description} ${r.topics.join(" ")}`.toLowerCase().includes(state.q.toLowerCase()));
  return `<h1 class="page">Models &amp; Code</h1><p class="sub">Open models trending on Hugging Face right now, and the fastest-growing new AI repos on GitHub (created in the last 14 days).</p>
    <h2 class="sec">Trending open models</h2>
    <div class="panel tbl"><table class="models"><thead><tr><th>Model</th><th>Task</th><th>License</th><th class="num">Likes</th><th class="num">Downloads</th><th class="num">Released</th></tr></thead><tbody>
    ${models.map((m) => `<tr><td><a href="${esc(m.url)}" target="_blank" rel="noopener"><b>${esc(m.id.split("/")[1] || m.id)}</b></a><div class="meta">${esc(m.org)}</div></td>
      <td>${esc(m.task || "—")}</td><td>${esc(m.license || "—")}</td><td class="num">${fmtNum(m.likes)}</td><td class="num">${fmtNum(m.downloads)}</td>
      <td class="num">${m.created ? ago(m.created) : "—"}</td></tr>`).join("")}</tbody></table></div>
    <h2 class="sec">New repos gaining stars</h2>
    <div class="panel pad" style="padding-top:2px;padding-bottom:2px">${repos.map((r) => `<div class="item"><div class="body">
      <a class="title" href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.name)}</a>
      <div class="meta"><span class="hot">★ ${fmtNum(r.stars)}</span> · ${esc(r.language || "")} · created ${ago(r.created)}</div>
      <div class="summary">${esc(r.description)}</div>
      <div class="tags">${r.topics.map((t) => `<span class="tag">${esc(t)}</span>`).join("")}</div></div></div>`).join("")}</div>`;
}

function viewCompanies() {
  const d = state.data, stats = {};
  for (const c of d.companies) stats[c] = { now: 0, prev: 0, latest: null };
  for (const i of d.items) {
    if (i.kind === "paper") continue;
    const h = hoursAgo(i.published);
    for (const c of i.companies) {
      const s = stats[c]; if (!s) continue;
      if (h <= 168) { s.now++; if (!s.latest) s.latest = i; } else if (h <= 336) s.prev++;
    }
  }
  const rows = Object.entries(stats).filter(([c, s]) => (s.now || s.prev) && (!state.q || c.toLowerCase().includes(state.q.toLowerCase())))
    .sort((a, b) => b[1].now - a[1].now);
  const max = Math.max(1, ...rows.map(([, s]) => s.now));
  return `<h1 class="page">Companies</h1><p class="sub">How much each company is in the news this week (stories mentioning it in the last 7 days, compared with the 7 days before). Click a company to see its stories.</p>
    <div class="cards">${rows.map(([c, s]) => {
      const diff = s.now - s.prev, pct = s.prev ? Math.round((diff / s.prev) * 100) : null;
      const trend = pct === null ? (s.now ? '<span class="trend up">new</span>' : "") : `<span class="trend ${diff >= 0 ? "up" : "down"}">${diff >= 0 ? "▲" : "▼"} ${Math.abs(pct)}%</span>`;
      return `<div class="panel card" data-company="${esc(c)}"><h3>${esc(c)} ${trend}<span class="n">${s.now}</span></h3>
        <div class="bar"><i style="width:${(s.now / max) * 100}%"></i></div>
        <div class="latest">${s.latest ? esc(s.latest.title) : "No stories this week"}</div></div>`;
    }).join("")}</div>`;
}

function viewPast() {
  const briefs = state.data.briefs || [];
  return `<h1 class="page">Past days</h1><p class="sub">Each morning's top stories, kept for 30 days, so you can catch up after time away.</p>
    ${briefs.map((b, idx) => `<details class="panel day" ${idx === 0 ? "open" : ""}><summary><b>${fmtDate(b.date)}</b><span>${esc(b.stories[0]?.title || "")}</span></summary>
      <div class="inner">${b.ai_summary ? `<div class="brief" style="padding:4px 0 8px 14px">${md(b.ai_summary)}</div>` : `<ol class="related" style="padding-left:20px">${b.stories.map((s) =>
        `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a> <span class="meta" style="display:inline">· ${s.sources.length} ${s.sources.length === 1 ? "source" : "sources"}</span></li>`).join("")}</ol>
        <h2 class="sec" style="margin-top:14px">Trending papers</h2><ul class="related">${b.papers.map((p) => `<li><a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a> <span class="hot">▲ ${p.upvotes}</span></li>`).join("")}</ul>`}
      </div></details>`).join("") || '<div class="empty">The archive starts with the first daily run.</div>'}`;
}

function viewSaved() {
  const items = Object.values(saved).filter(matchesQuery).sort((a, b) => b.published.localeCompare(a.published));
  return `<h1 class="page">Saved</h1><p class="sub">Stories you starred. Saved in this browser only.</p>
    ${items.length ? list(items, 500) : '<div class="empty">Star any story (☆) to keep it here.</div>'}`;
}

const VIEWS = { today: viewToday, feed: viewFeed, labs: viewLabs, research: viewResearch, models: viewModels, companies: viewCompanies, past: viewPast, saved: viewSaved };

function render() {
  const route = location.hash.slice(1) || "today";
  const name = VIEWS[route] ? route : "today";
  document.querySelectorAll("#tabs a").forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#" + name));
  $("#view").innerHTML = VIEWS[name]();
}

function renderChrome() {
  const d = state.data, ok = d.health.filter((h) => h.ok).length;
  const when = new Date(d.generated_at);
  $("#status").innerHTML = `Updated ${ago(d.generated_at)} · <b>${d.new_today} new</b> since the last update`;
  $("#status").title = when.toLocaleString();
  $("#foot").innerHTML = `<details><summary>${ok} of ${d.health.length} sources answered in the last update (${when.toLocaleString()}). Show details</summary>
    <div class="health">${d.health.map((h) => `<div><span class="${h.ok ? "ok" : "fail"}">${h.ok ? "●" : "✕"}</span> ${esc(h.source.replace(/^(feed|gnews):/, ""))}${h.ok ? ` · ${h.count}` : ` · <span title="${esc(h.error)}">failed</span>`}</div>`).join("")}</div></details>
    <p>AI Radar collects public feeds from AI labs, news sites, newsletters, arXiv, Hugging Face, Hacker News and GitHub. Headlines link to the original source.</p>`;
}

// ---------- events ----------
document.addEventListener("click", (e) => {
  const t = e.target.closest("button, .card");
  if (!t) return;
  const ds = t.dataset;
  if (ds.star) {
    const it = state.byId[ds.star] || saved[ds.star];
    if (saved[ds.star]) delete saved[ds.star]; else if (it) saved[ds.star] = it;
    save("radar.saved", saved);
    t.classList.toggle("on", !!saved[ds.star]);
    return;
  }
  if (ds.company !== undefined || ds.topic !== undefined) {
    Object.assign(state.feed, { company: ds.company ?? "", topic: ds.topic ?? "", kind: "all", range: 7, limit: 60 });
    location.hash === "#feed" ? render() : (location.hash = "feed");
    window.scrollTo(0, 0);
    return;
  }
  if (ds.range) state.feed.range = +ds.range;
  if (ds.kind) state.feed.kind = ds.kind;
  if (ds.rtab) state.research.tab = ds.rtab;
  if (ds.clear !== undefined) Object.assign(state.feed, { company: "", topic: "" });
  if (ds.more !== undefined) { location.hash === "#research" ? (state.research.limit += 60) : (state.feed.limit += 60); }
  else { state.feed.limit = 60; state.research.limit = 60; }
  render();
});
document.addEventListener("change", (e) => {
  const s = e.target.dataset.sel;
  if (s === "company" || s === "topic") state.feed[s] = e.target.value;
  if (s === "rtopic") state.research.topic = e.target.value;
  render();
});
let qTimer;
$("#q").addEventListener("input", (e) => { clearTimeout(qTimer); qTimer = setTimeout(() => { state.q = e.target.value.trim(); render(); }, 150); });
window.addEventListener("hashchange", () => { render(); window.scrollTo(0, 0); });

$("#theme").addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "light" : "dark";
  save("radar.theme", document.documentElement.dataset.theme);
});
const theme = store("radar.theme", null);
if (theme) document.documentElement.dataset.theme = theme;

// ---------- boot ----------
fetch("data/feed.json", { cache: "no-cache" })
  .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then((data) => {
    state.data = data;
    for (const i of data.items) state.byId[i.id] = i;
    renderChrome();
    render();
  })
  .catch((err) => {
    $("#status").textContent = "Could not load data";
    $("#view").innerHTML = `<div class="empty">Couldn't load <code>data/feed.json</code> (${esc(err.message)}).<br>
      Run <code>python3 scripts/fetch.py</code>, then serve this folder, e.g. <code>python3 -m http.server</code>.</div>`;
  });
