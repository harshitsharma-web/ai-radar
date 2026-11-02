# AI Radar

A website that keeps you up to date on the AI industry. It updates itself every
morning with:

- **Top stories**: the day's biggest news, grouped so one event shows once, ranked by how many outlets cover it
- **Labs**: official posts from OpenAI, Anthropic, Google DeepMind, Meta, Mistral, NVIDIA, Microsoft, Apple and others
- **Research**: trending papers (Hugging Face Daily Papers), the newest arXiv AI papers, and lab research blogs
- **Models & Code**: open models trending on Hugging Face, and new GitHub repos gaining stars
- **Companies**: how much each company is in the news this week, and its latest story
- **Past days**: each morning's brief, kept for 30 days
- **Daily brief** (optional): a written summary by Claude, if you add an Anthropic API key

Everything comes from public RSS feeds and APIs; edit `scripts/sources.py` to
add or remove sources, companies or topics.

## How it runs

```
GitHub Actions (6:00 am IST daily)
  -> scripts/fetch.py        pulls ~50 sources, tags and ranks them
  -> data/feed.json          what the site reads (data/archive.json keeps 45 days)
  -> GitHub Pages            publishes index.html + data at your public URL
```

## Put it online (free, one time)

1. Create a new **public** repo on GitHub, e.g. `ai-radar` (no README).
2. Push this folder to it:
   ```bash
   git remote add origin https://github.com/<your-username>/ai-radar.git
   git push -u origin main
   ```
3. In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. **Actions** tab → **Daily update** → **Run workflow**. In about 2 minutes the
   site is live at `https://<your-username>.github.io/ai-radar/`.

Optional: for the written daily brief, add a secret in **Settings → Secrets and
variables → Actions** named `ANTHROPIC_API_KEY`. It costs a few cents a day.

## Run it on your Mac

```bash
python3 scripts/fetch.py
python3 -m http.server 8000
```

Then open http://localhost:8000.
