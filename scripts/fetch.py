"""AI Radar daily update.

Pulls every source in sources.py, tags and ranks what it finds, keeps a
rolling archive, and writes the files the website reads:

  data/archive.json   every item from the last ARCHIVE_DAYS days (the store)
  data/feed.json      what the site loads: items, top stories, papers, models, repos
  data/briefs/<date>.json   that day's brief, kept for the "Past days" view

Run it with:  python3 scripts/fetch.py
Only the standard library is needed. If ANTHROPIC_API_KEY is set and the
`anthropic` package is installed, brief.py also writes an AI summary.
"""

import concurrent.futures as cf
import email.utils
import hashlib
import html
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sources as S  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ARCHIVE_DAYS = 45
ARXIV_KEEP_DAYS = 7
FEED_DAYS = 30
UA = "Mozilla/5.0 (compatible; AI-Radar/1.0; +https://github.com)"
NOW = datetime.now(timezone.utc)


# ---------- helpers ----------

def http_get(url, accept=None, headers=None, timeout=25):
    h = {"User-Agent": UA}
    if accept:
        h["Accept"] = accept
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    last = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - any network error just means "retry once, then skip"
            last = e
            time.sleep(2 + attempt * 3)
    raise last


def get_json(url, **kw):
    return json.loads(http_get(url, accept="application/json", **kw))


def clean(text, limit=320):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def item_id(url, title=""):
    return hashlib.sha1((url or title).split("#")[0].rstrip("/").encode()).hexdigest()[:12]


def compile_map(m):
    return {k: [re.compile(p, re.I) for p in v] for k, v in m.items()}


COMPANY_RX = compile_map(S.COMPANIES)
TOPIC_RX = compile_map(S.TOPICS)
AI_RX = re.compile(S.AI_FILTER, re.I)


def tag(item):
    text = f"{item['title']} {item.get('summary', '')}"
    title = item["title"]
    companies = [c for c, rxs in COMPANY_RX.items() if any(r.search(text) for r in rxs)]
    if item.get("company") and item["company"] not in companies:
        companies.insert(0, item["company"])
    # a company named only in the summary is a weaker signal: keep it, but title hits come first
    companies.sort(key=lambda c: 0 if any(r.search(title) for r in COMPANY_RX.get(c, [])) or c == item.get("company") else 1)
    topics = [t for t, rxs in TOPIC_RX.items() if any(r.search(text) for r in rxs)]
    if item["kind"] == "paper" and "Research" not in topics:
        topics.insert(0, "Research")
    item["companies"] = companies[:6]
    item["topics"] = topics[:5]
    item.pop("company", None)
    return item


def make(title, url, source, kind, published, summary="", weight=1, **extra):
    return {
        "id": item_id(url, title),
        "title": clean(title, 220),
        "url": url,
        "source": source,
        "kind": kind,
        "published": iso(published or NOW),
        "summary": clean(summary),
        "weight": weight,
        **extra,
    }


# ---------- RSS / Atom ----------

def local(tag_name):
    return tag_name.rsplit("}", 1)[-1]


def child_text(el, *names):
    for c in el:
        if local(c.tag) in names and (c.text or "").strip():
            return c.text.strip()
    return ""


def child_link(el):
    for c in el:
        if local(c.tag) == "link":
            if c.get("href") and c.get("rel", "alternate") == "alternate":
                return c.get("href")
            if (c.text or "").strip():
                return c.text.strip()
    for c in el:
        if local(c.tag) == "link" and c.get("href"):
            return c.get("href")
    return child_text(el, "guid", "id")


def parse_feed(raw):
    root = ET.fromstring(raw)
    entries = [e for e in root.iter() if local(e.tag) in ("item", "entry")]
    out = []
    for e in entries:
        title = child_text(e, "title")
        link = child_link(e)
        if not title or not link:
            continue
        date = parse_date(child_text(e, "pubDate", "published", "updated", "date"))
        summary = child_text(e, "description", "summary", "content", "encoded")
        out.append((title, link, date, summary))
    return out


def fetch_feed(f, max_age_days=ARCHIVE_DAYS):
    raw = http_get(f["url"])
    cutoff = NOW - timedelta(days=max_age_days)
    items = []
    for title, link, date, summary in parse_feed(raw):
        if date and date < cutoff:
            continue
        if f["kind"] == "community" and not AI_RX.search(title + " " + summary) and "LocalLLaMA" not in f["name"] and "MachineLearning" not in f["name"]:
            continue
        items.append(make(title, link, f["name"], f["kind"], date, summary, f["weight"], company=f.get("company")))
    return items


def fetch_google_news(q):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"{q} when:3d", "hl": "en-US", "gl": "US", "ceid": "US:en"})
    items = []
    for title, link, date, _ in parse_feed(http_get(url))[: S.GOOGLE_NEWS_PER_QUERY]:
        # Google News titles end in " - Publisher"
        headline, _, publisher = title.rpartition(" - ")
        if not headline or len(publisher) > 60:
            headline, publisher = title, "Google News"
        publisher = re.sub(r"^https?://(www\.)?|/$", "", publisher.strip())
        if not AI_RX.search(headline) and not any(r.search(headline) for rxs in COMPANY_RX.values() for r in rxs):
            continue
        items.append(make(headline, link, publisher, "news", date, "", 1, via="Google News"))
    return items


# ---------- APIs ----------

def fetch_hn():
    since = int((NOW - timedelta(days=3)).timestamp())
    seen, items = set(), []
    for q in S.HN_QUERIES:
        url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode({
            "query": q, "tags": "story", "hitsPerPage": 50,
            "numericFilters": f"created_at_i>{since},points>{S.HN_MIN_POINTS}"})
        for h in get_json(url).get("hits", []):
            if h["objectID"] in seen or not h.get("title") or not AI_RX.search(h["title"]):
                continue
            seen.add(h["objectID"])
            disc = f"https://news.ycombinator.com/item?id={h['objectID']}"
            items.append(make(h["title"], h.get("url") or disc, "Hacker News", "community",
                              parse_date(h.get("created_at")), "", 1,
                              points=h.get("points", 0), comments=h.get("num_comments", 0), discussion=disc))
    return items


def fetch_hf_papers():
    items = []
    for p in get_json("https://huggingface.co/api/daily_papers?limit=100"):
        pp = p.get("paper", {})
        pid = pp.get("id")
        if not pid:
            continue
        items.append(make(pp.get("title") or p.get("title", ""), f"https://huggingface.co/papers/{pid}",
                          "HF Daily Papers", "paper", parse_date(p.get("publishedAt") or pp.get("publishedAt")),
                          pp.get("ai_summary") or pp.get("summary", ""), 2,
                          upvotes=pp.get("upvotes", 0), arxiv=f"https://arxiv.org/abs/{pid}",
                          authors=[a.get("name") for a in pp.get("authors", [])[:6] if a.get("name")],
                          org=(pp.get("organization") or p.get("organization") or {}).get("fullname"),
                          github=pp.get("githubRepo"), stars=pp.get("githubStars")))
    return items


def fetch_arxiv():
    q = " OR ".join(f"cat:{c}" for c in S.ARXIV_CATEGORIES)
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": q, "sortBy": "submittedDate", "sortOrder": "descending", "max_results": S.ARXIV_MAX})
    root = ET.fromstring(http_get(url, timeout=60))
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    items = []
    for e in root.findall("a:entry", ns):
        link = e.findtext("a:id", "", ns).strip().replace("http://", "https://")
        cat = e.find("x:primary_category", ns)
        items.append(make(e.findtext("a:title", "", ns), link, "arXiv", "paper",
                          parse_date(e.findtext("a:published", "", ns)), e.findtext("a:summary", "", ns), 1,
                          authors=[a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)[:6]],
                          category=cat.get("term") if cat is not None else None))
    return items


def fetch_hf_models():
    models = get_json("https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=40")
    out = []
    for m in models:
        mid = m.get("id") or m.get("modelId")
        out.append({"id": mid, "url": f"https://huggingface.co/{mid}", "org": mid.split("/")[0],
                    "task": m.get("pipeline_tag"), "likes": m.get("likes", 0), "downloads": m.get("downloads", 0),
                    "trending": m.get("trendingScore", 0), "created": m.get("createdAt"),
                    "license": next((t.split(":", 1)[1] for t in m.get("tags", []) if t.startswith("license:")), None)})
    return out


def fetch_github():
    since = (NOW - timedelta(days=14)).strftime("%Y-%m-%d")
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    repos = {}
    for topic in S.GITHUB_TOPICS:
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
            {"q": f"topic:{topic} created:>{since}", "sort": "stars", "order": "desc", "per_page": 15})
        for r in get_json(url, headers=headers).get("items", []):
            if not (r.get("description") or "").strip():
                continue
            repos[r["full_name"]] = {"name": r["full_name"], "url": r["html_url"], "description": clean(r.get("description") or "", 200),
                                     "stars": r["stargazers_count"], "language": r.get("language"),
                                     "created": r["created_at"], "topics": r.get("topics", [])[:6]}
    return sorted(repos.values(), key=lambda r: -r["stars"])[:40]


# ---------- ranking ----------

STOP = set("a an the of to in on for and or with is are was be by at from as its it this that new how why what who will can after over into about vs ai".split())


def tokens(title):
    return {w for w in re.findall(r"[a-z0-9][a-z0-9.\-]+", title.lower()) if w not in STOP and len(w) > 2}


def cluster(items):
    """Group stories about the same event (similar titles) so each event appears once."""
    clusters = []
    for it in sorted(items, key=lambda i: -i["weight"]):
        tk = tokens(it["title"])
        best = None
        for c in clusters:
            inter = len(tk & c["tokens"])
            if inter >= 3 and inter / max(1, min(len(tk), len(c["tokens"]))) >= 0.5:
                best = c
                break
        if best:
            best["items"].append(it)
            best["tokens"] |= tk
        else:
            clusters.append({"tokens": set(tk), "items": [it]})
    return clusters


def item_score(it):
    age_h = max(0.0, (NOW - parse_date(it["published"])).total_seconds() / 3600)
    s = it["weight"]
    if it.get("points"):
        s += math.log10(1 + it["points"]) * 1.5
    if it.get("upvotes"):
        s += math.log10(1 + it["upvotes"]) * 1.5
    return s * math.exp(-age_h / 36)


def top_stories(items, hours=36, n=15):
    recent = [i for i in items if i["kind"] in ("lab", "news", "newsletter", "community", "research")
              and parse_date(i["published"]) >= NOW - timedelta(hours=hours)]
    out = []
    for c in cluster(recent):
        its = c["items"]
        sources = {i["source"] for i in its}
        score = sum(item_score(i) for i in its) + 1.2 * (len(sources) - 1)
        lead = max(its, key=lambda i: (i["kind"] == "lab", i["weight"], len(i.get("summary", ""))))
        out.append({"lead": lead["id"], "score": round(score, 2), "count": len(its),
                    "sources": sorted(sources), "related": [i["id"] for i in its if i["id"] != lead["id"]][:8]})
    out.sort(key=lambda c: -c["score"])
    return out[:n]


# ---------- main ----------

def run_jobs():
    jobs = {f"feed:{f['name']}": (fetch_feed, f) for f in S.FEEDS}
    jobs.update({f"gnews:{q}": (fetch_google_news, q) for q in S.GOOGLE_NEWS_QUERIES})
    jobs.update({"hn": (fetch_hn, None), "hf_papers": (fetch_hf_papers, None), "arxiv": (fetch_arxiv, None),
                 "hf_models": (fetch_hf_models, None), "github": (fetch_github, None)})
    results, health = {}, []
    with cf.ThreadPoolExecutor(12) as ex:
        futs = {ex.submit(fn, *([arg] if arg is not None else [])): name for name, (fn, arg) in jobs.items()}
        for fut in cf.as_completed(futs):
            name = futs[fut]
            try:
                results[name] = fut.result()
                health.append({"source": name, "ok": True, "count": len(results[name])})
            except Exception as e:  # noqa: BLE001 - one broken source must not stop the run
                health.append({"source": name, "ok": False, "error": str(e)[:120]})
    return results, sorted(health, key=lambda h: (h["ok"], h["source"]))


def main():
    DATA.mkdir(exist_ok=True)
    (DATA / "briefs").mkdir(exist_ok=True)
    results, health = run_jobs()
    models = results.pop("hf_models", [])
    repos = results.pop("github", [])

    archive_path = DATA / "archive.json"
    archive = json.loads(archive_path.read_text()) if archive_path.exists() else {}
    new = 0
    for batch in results.values():
        for it in batch:
            tag(it)
            old = archive.get(it["id"])
            if old is None:
                new += 1
                it["first_seen"] = iso(NOW)
            else:
                it["first_seen"] = old.get("first_seen", it["published"])
            archive[it["id"]] = it

    # drop old items; arXiv is high volume, so keep it for less time
    def keep(it):
        age = NOW - parse_date(it["published"])
        if it["source"] == "arXiv":
            return age <= timedelta(days=ARXIV_KEEP_DAYS)
        return age <= timedelta(days=ARCHIVE_DAYS)
    archive = {k: v for k, v in archive.items() if keep(v)}
    archive_path.write_text(json.dumps(archive, ensure_ascii=False, separators=(",", ":")))

    feed_cut = NOW - timedelta(days=FEED_DAYS)
    items = sorted((i for i in archive.values() if parse_date(i["published"]) >= feed_cut),
                   key=lambda i: i["published"], reverse=True)
    stories = top_stories(items)
    papers = sorted((i for i in items if i["source"] == "HF Daily Papers"
                     and parse_date(i["published"]) >= NOW - timedelta(days=4)),
                    key=lambda i: -i.get("upvotes", 0))[:12]

    today = NOW.strftime("%Y-%m-%d")
    by_id = {i["id"]: i for i in items}
    brief = {"date": today, "generated_at": iso(NOW),
             "stories": [{**s, "title": by_id[s["lead"]]["title"], "url": by_id[s["lead"]]["url"]} for s in stories[:10]],
             "papers": [{"id": p["id"], "title": p["title"], "url": p["url"], "upvotes": p.get("upvotes", 0)} for p in papers[:6]],
             "models": models[:6]}

    try:
        import brief as ai_brief
        summary = ai_brief.write_summary(items, stories, papers, models, repos)
        if summary:
            brief["ai_summary"] = summary
    except Exception as e:  # noqa: BLE001 - the AI summary is optional
        print(f"AI summary skipped: {e}")
    (DATA / "briefs" / f"{today}.json").write_text(json.dumps(brief, ensure_ascii=False, indent=1))

    briefs = []
    for p in sorted((DATA / "briefs").glob("*.json"), reverse=True)[:FEED_DAYS]:
        briefs.append(json.loads(p.read_text()))

    feed = {"generated_at": iso(NOW), "new_today": new, "items": items, "top": stories,
            "papers": [p["id"] for p in papers], "models": models, "repos": repos,
            "briefs": briefs, "health": health,
            "companies": list(S.COMPANIES), "topics": ["Research"] + list(S.TOPICS)}
    (DATA / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, separators=(",", ":")))

    ok = sum(h["ok"] for h in health)
    print(f"{len(items)} items in feed, {new} new, {ok}/{len(health)} sources OK")
    for h in health:
        if not h["ok"]:
            print(f"  FAILED {h['source']}: {h['error']}")


if __name__ == "__main__":
    main()
