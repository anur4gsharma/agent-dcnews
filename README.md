# AI Opportunity Discovery Agent

Python agent that discovers, ranks, and summarizes AI/ML opportunities — internships, hackathons, competitions, events, fellowships, and research — then delivers a curated weekly digest to Discord.

## Sources (20+)

| Category | Sources |
|---|---|
| **News** | TechCrunch, The Verge, Ars Technica, VentureBeat, MIT Tech Review, OpenAI, DeepMind, Google AI, Microsoft Research, NVIDIA, HuggingFace, Anthropic, Hacker News, arXiv |
| **Hackathons** | Devpost, MLH |
| **Competitions** | Kaggle, AIcrowd, Zindi, DrivenData, HuggingFace Competitions |
| **Jobs** | RemoteOK (AI/ML/SWE filtered) |
| **Events** | Luma, Eventbrite |
| **Fellowships** | Google Summer of Code, MLH Fellowship, Outreachy, LFX Mentorship, Season of KDE |
| **Open Source** | GitHub Trending |
| **Startup** | Product Hunt, Y Combinator Blog |
| **Sentiment** | Reddit (r/MachineLearning, r/technology) |

## Setup

1. Create and activate a Python 3.11 environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in:

```bash
GEMINI_API_KEY=your-gemini-key
DISCORD_WEBHOOK_URL=your-discord-webhook-url
GEMINI_MODEL=gemini-2.0-flash
```

Do **not** commit real API keys or Discord webhooks.

## Run Once

```bash
python main.py --run-now
```

Use deterministic sample data without external API calls:

```bash
python main.py --run-now --mock
```

## Schedule

Local scheduler:

```bash
python main.py --schedule
```

GitHub Actions is configured in `.github/workflows/daily-digest.yml` to run every Sunday at 1:30 UTC (Sunday 7:00 AM IST).

Add these repository secrets in GitHub:

- `GEMINI_API_KEY`
- `DISCORD_WEBHOOK_URL`

## Outputs

- **Discord**: Two embeds — News + Opportunities with structured metadata.
- **Markdown archive** in `digests/YYYY-MM-DD.md`.
- **SQLite state** in `digest.db`.
- **Rolling profile** in `profile.json`.

## Opportunity Format

Each opportunity includes: Title, Organization, Category, Mode (Remote/Hybrid/In-person), Deadline, Cost, Difficulty, Priority Score (1-10), and a relevance summary.
