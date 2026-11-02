"""Optional: Claude writes a short daily brief from what fetch.py collected.

Runs only when ANTHROPIC_API_KEY is set and the `anthropic` package is
installed (the GitHub Action installs it). Without them the site still shows
the ranked top stories; it just has no written summary.
"""

import os

MODEL = "claude-opus-5-5"

PROMPT = """You write the daily brief for "AI Radar", a dashboard that keeps a busy reader up to date on the AI industry.

Below are today's top story clusters (with how many outlets covered each), plus recent items, trending papers, trending open models and new GitHub repos. Write the brief in this exact format:

## The big picture
Two or three sentences on what mattered most in AI in the last day.

## Top stories
- **Short headline**: one or two sentences on what happened and why it matters. [Source](url)
(5 to 8 bullets, most important first. Merge items that cover the same event.)

## Research to watch
- **Paper or result**: one sentence on why it is interesting. [Link](url)
(3 to 4 bullets)

## Open models and tools
- **Name**: one sentence. [Link](url)
(2 to 4 bullets)

## Signals
- One-line trends or things to keep an eye on (2 or 3 bullets).

Use only facts in the material below. Do not invent numbers, dates or quotes. Use only the URLs given. Plain, direct language; no hype.

---
{material}"""


def _material(items, stories, papers, models, repos):
    by_id = {i["id"]: i for i in items}
    lines = ["TOP STORY CLUSTERS:"]
    for s in stories[:15]:
        lead = by_id[s["lead"]]
        lines.append(f"- [{s['count']} outlets: {', '.join(s['sources'][:5])}] {lead['title']} | {lead['url']} | {lead.get('summary', '')[:300]}")
        for rid in s["related"][:3]:
            r = by_id.get(rid)
            if r:
                lines.append(f"    also: {r['title']} ({r['source']})")
    lines.append("\nLAB ANNOUNCEMENTS (last 3 days):")
    labs = [i for i in items if i["kind"] == "lab"][:15]
    lines += [f"- {i['source']}: {i['title']} | {i['url']}" for i in labs]
    lines.append("\nTRENDING PAPERS:")
    lines += [f"- ({p.get('upvotes', 0)} upvotes) {p['title']} | {p['url']} | {p.get('summary', '')[:250]}" for p in papers[:10]]
    lines.append("\nTRENDING OPEN MODELS (Hugging Face):")
    lines += [f"- {m['id']} ({m.get('task')}, {m['likes']} likes) | {m['url']}" for m in models[:10]]
    lines.append("\nNEW GITHUB REPOS:")
    lines += [f"- {r['name']} ({r['stars']} stars): {r['description']} | {r['url']}" for r in repos[:8]]
    return "\n".join(lines)


def write_summary(items, stories, papers, models, repos):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": PROMPT.format(material=_material(items, stories, papers, models, repos))}],
    )
    if response.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text or None
