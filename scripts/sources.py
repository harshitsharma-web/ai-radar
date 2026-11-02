"""Where AI Radar gets its data, and how it tags what it finds.

Edit this file to add or remove feeds, companies or topics. Every source is
an official RSS/Atom feed or a public API, so nothing here scrapes HTML.
"""

# kind: lab | research | news | newsletter | community
# weight: how much one story from this source counts when ranking (1-3)
FEEDS = [
    # --- AI labs (official announcements) ---
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml", "kind": "lab", "weight": 3, "company": "OpenAI"},
    {"name": "Anthropic", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml", "kind": "lab", "weight": 3, "company": "Anthropic"},
    {"name": "Anthropic Research", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml", "kind": "research", "weight": 3, "company": "Anthropic"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "kind": "lab", "weight": 3, "company": "Google"},
    {"name": "Google AI", "url": "https://blog.google/technology/ai/rss/", "kind": "lab", "weight": 3, "company": "Google"},
    {"name": "Meta AI", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_meta_ai.xml", "kind": "lab", "weight": 3, "company": "Meta"},
    {"name": "Mistral", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_mistral.xml", "kind": "lab", "weight": 3, "company": "Mistral"},
    {"name": "NVIDIA", "url": "https://blogs.nvidia.com/feed/", "kind": "lab", "weight": 2, "company": "NVIDIA"},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "kind": "lab", "weight": 2, "company": "Hugging Face"},
    {"name": "AWS Machine Learning", "url": "https://aws.amazon.com/blogs/machine-learning/feed/", "kind": "lab", "weight": 1, "company": "Amazon"},

    # --- Research labs and blogs ---
    {"name": "Google Research", "url": "https://research.google/blog/rss/", "kind": "research", "weight": 2, "company": "Google"},
    {"name": "Microsoft Research", "url": "https://www.microsoft.com/en-us/research/feed/", "kind": "research", "weight": 2, "company": "Microsoft"},
    {"name": "Apple ML Research", "url": "https://machinelearning.apple.com/rss.xml", "kind": "research", "weight": 2, "company": "Apple"},
    {"name": "Berkeley AI Research", "url": "https://bair.berkeley.edu/blog/feed.xml", "kind": "research", "weight": 2},

    # --- News ---
    {"name": "TechCrunch", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "kind": "news", "weight": 2},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "kind": "news", "weight": 2},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "kind": "news", "weight": 2},
    {"name": "Ars Technica", "url": "https://arstechnica.com/ai/feed/", "kind": "news", "weight": 2},
    {"name": "Wired", "url": "https://www.wired.com/feed/tag/ai/latest/rss", "kind": "news", "weight": 2},
    {"name": "VentureBeat", "url": "https://venturebeat.com/category/ai/feed/", "kind": "news", "weight": 2},

    # --- Newsletters and analysts ---
    {"name": "Import AI", "url": "https://importai.substack.com/feed", "kind": "newsletter", "weight": 2},
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "kind": "newsletter", "weight": 1},
    {"name": "Latent Space", "url": "https://www.latent.space/feed", "kind": "newsletter", "weight": 2},
    {"name": "Interconnects", "url": "https://www.interconnects.ai/feed", "kind": "newsletter", "weight": 2},
    {"name": "Zvi Mowshowitz", "url": "https://thezvi.substack.com/feed", "kind": "newsletter", "weight": 1},
    {"name": "One Useful Thing", "url": "https://www.oneusefulthing.org/feed", "kind": "newsletter", "weight": 1},

    # --- Community ---
    {"name": "r/MachineLearning", "url": "https://www.reddit.com/r/MachineLearning/top/.rss?t=day", "kind": "community", "weight": 1},
    {"name": "r/LocalLLaMA", "url": "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day", "kind": "community", "weight": 1},
]

# Google News searches fill the gaps for companies with no official feed
# (xAI, DeepSeek, Qwen ...) and for cross-cutting themes like funding and policy.
GOOGLE_NEWS_QUERIES = [
    "xAI Grok", "DeepSeek", "Alibaba Qwen", "Moonshot Kimi OR Zhipu GLM",
    "Microsoft AI Copilot", "Apple Intelligence", "Meta superintelligence OR Llama",
    "Anthropic Claude", "OpenAI", "Gemini Google AI",
    "AI startup raises funding", "AI acquisition", "AI data center", "AI chips export",
    "AI regulation law", "EU AI Act", "India AI",
    "Scale AI OR Surge AI OR Mercor OR Turing AI data",
]
GOOGLE_NEWS_PER_QUERY = 12

# Hacker News: stories matching these words with enough points
HN_QUERIES = ["AI", "LLM", "OpenAI", "Anthropic", "Claude", "GPT", "Gemini", "DeepSeek",
              "Llama", "Mistral", "Qwen", "agent", "Nvidia", "model", "inference", "transformer"]
HN_MIN_POINTS = 60

ARXIV_CATEGORIES = ["cs.CL", "cs.AI", "cs.LG", "cs.CV", "cs.RO", "cs.MA"]
ARXIV_MAX = 250

GITHUB_TOPICS = ["llm", "ai-agents", "generative-ai", "large-language-models", "mcp", "rag"]

# Companies: name -> regexes (case-insensitive unless the pattern starts with "(?-i)")
COMPANIES = {
    "OpenAI": [r"\bopenai\b", r"\bchatgpt\b", r"\bgpt-?\d", r"\bsora\b", r"\bcodex\b", r"\bsam altman\b", r"\bo\d-(mini|pro)\b"],
    "Anthropic": [r"\banthropic\b", r"\bclaude\b", r"\bdario amodei\b"],
    "Google": [r"\bgoogle\b", r"\bdeepmind\b", r"\bgemini\b", r"\bgemma\b", r"\balphafold\b", r"\bveo\b", r"\btpu", r"\bsundar pichai\b", r"\bdemis hassabis\b"],
    "Meta": [r"(?-i:\bMeta\b)(?!-)", r"\bllama\b", r"\bzuckerberg\b", r"\bmeta ai\b", r"\bmeta superintelligence\b"],
    "Microsoft": [r"\bmicrosoft\b", r"\bcopilot\b", r"\bazure\b", r"\bsatya nadella\b", r"\bmustafa suleyman\b"],
    "xAI": [r"\bxai\b", r"\bgrok\b"],
    "Amazon": [r"\bamazon\b", r"\baws\b", r"\bbedrock\b", r"\balexa\b", r"\btrainium\b"],
    "Apple": [r"\bapple\b", r"\bsiri\b"],
    "NVIDIA": [r"\bnvidia\b", r"\bjensen huang\b", r"\bblackwell\b", r"\brubin\b", r"\bcuda\b"],
    "AMD": [r"\bamd\b", r"\binstinct mi\d"],
    "TSMC": [r"\btsmc\b"],
    "Mistral": [r"\bmistral\b"],
    "DeepSeek": [r"\bdeepseek\b"],
    "Alibaba / Qwen": [r"\bqwen\b", r"\balibaba\b"],
    "Moonshot / Kimi": [r"\bmoonshot ai\b", r"\bkimi\b"],
    "Zhipu / GLM": [r"\bzhipu\b", r"\bz\.ai\b", r"\bglm-?\d"],
    "Hugging Face": [r"\bhugging ?face\b"],
    "Perplexity": [r"\bperplexity\b"],
    "Cursor": [r"\bcursor\b", r"\banysphere\b"],
    "Cohere": [r"\bcohere\b"],
    "Thinking Machines": [r"\bthinking machines\b", r"\bmira murati\b"],
    "SSI": [r"\bsafe superintelligence\b", r"\bilya sutskever\b"],
    "Scale AI": [r"\bscale ai\b", r"\balexandr wang\b"],
    "Surge AI": [r"\bsurge ai\b"],
    "Mercor": [r"\bmercor\b"],
    "Turing": [r"(?-i:\bTuring\b)(?! (test|award|machine|complete))"],
    "ElevenLabs": [r"\belevenlabs\b"],
    "Midjourney": [r"\bmidjourney\b"],
    "Runway": [r"(?-i:\bRunway\b)"],
}

TOPICS = {
    "Models & launches": [r"\blaunch", r"\breleas", r"\bintroduc", r"\bunveil", r"\bnew model", r"\bgpt-?\d", r"\bclaude \w+ \d", r"\bgemini \d", r"\bllama \d", r"\bqwen\d", r"\bpreview\b"],
    "Agents": [r"\bagent", r"\bcomputer use\b", r"\bbrowser use\b", r"\bmcp\b", r"\bmodel context protocol\b", r"\bautonomous\b", r"\btool use\b"],
    "Coding": [r"\bcoding\b", r"\bcode\b", r"\bdevelopers?\b", r"\bswe-bench\b", r"\bprogramm", r"\bcursor\b", r"\bcopilot\b", r"\bcodex\b", r"\bclaude code\b"],
    "Reasoning": [r"\breasoning\b", r"\bthinking\b", r"\bchain[- ]of[- ]thought\b", r"\bmath", r"\btest[- ]time\b"],
    "Multimodal": [r"\bimage", r"\bvideo", r"\bvision\b", r"\bspeech\b", r"\baudio\b", r"\bvoice\b", r"\bmultimodal\b", r"\btext-to-"],
    "Robotics": [r"\brobot", r"\bhumanoid", r"\bembodied\b", r"\bself-driving\b", r"\bautonomous vehicle"],
    "Chips & compute": [r"\bgpus?\b", r"\bchips?\b", r"\bsemiconductor", r"\bdata ?cent(er|re)s?\b", r"\bcompute\b", r"\btpus?\b", r"\bnvidia\b", r"\bpower grid\b", r"\bgigawatt"],
    "Funding & deals": [r"\braises?\b", r"\braised\b", r"\bfunding\b", r"\bvaluation\b", r"\bacqui(re|res|red|sition)", r"\bipo\b", r"\binvest", r"\bseries [a-f]\b", r"\$\d+(\.\d+)? ?(b|bn|billion|m|million)\b", r"\bdeal\b", r"\bpartnership\b"],
    "Policy & safety": [r"\bregulat", r"\blaws?\b", r"\blegislat", r"\bpolicy\b", r"\bban(s|ned)?\b", r"\bsafety\b", r"\balignment\b", r"\bcopyright", r"\blawsuit", r"\bcourt\b", r"\bsenate\b", r"\bcongress\b", r"\bai act\b", r"\bexport control", r"\bgovernment\b", r"\bwhite house\b"],
    "Open source": [r"\bopen[- ]source", r"\bopen[- ]weights?\b", r"\bopen model", r"\bhugging ?face\b", r"\bgithub\b"],
    "Evals & benchmarks": [r"\bbenchmark", r"\beval(s|uation)?\b", r"\bleaderboard", r"\barena\b"],
    "Training data & RL": [r"\btraining data\b", r"\bdatasets?\b", r"\bsynthetic data\b", r"\brlhf\b", r"\breinforcement learning\b", r"\bannotat", r"\blabel(l)?ing\b", r"\brl environments?\b", r"\bpost-training\b", r"\bfine-?tun"],
    "Business & products": [r"\brevenue\b", r"\bsubscri", r"\benterprise\b", r"\bcustomers?\b", r"\bpricing\b", r"\bearnings\b", r"\busers\b"],
    "Jobs & society": [r"\bjobs?\b", r"\bworkers?\b", r"\blayoffs?\b", r"\beducation\b", r"\bstudents?\b", r"\bhealth", r"\belection"],
}

# Words that mark a Hacker News / Google News / community story as AI-related
AI_FILTER = r"\b(ai|a\.i\.|llms?|gpt|openai|anthropic|claude|gemini|deepmind|llama|mistral|deepseek|qwen|grok|xai|nvidia|machine learning|neural|transformer|agents?|agentic|chatbot|copilot|inference|diffusion|hugging ?face|model|models)\b"
