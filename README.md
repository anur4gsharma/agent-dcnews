# AI Opportunity Discovery Agent

Python agent that discovers, ranks, and summarizes AI/ML opportunities — internships, hackathons, competitions, events, fellowships, and research — then delivers a curated daily digest to Discord.

## How It Works

The AI Opportunity Discovery Agent works through a fully automated pipeline designed to find the highest-signal opportunities for CS and AI/ML students:
1. **Scraping & Aggregation:** Pulls data from 20+ sources, including specialized RSS feeds, tech news, hackathon platforms (Devpost/MLH), open source trackers, and Reddit.
2. **LLM Evaluation (Gemini 2.0 Flash):** Evaluates all scraped items against a target profile. It filters out irrelevant content, extracts metadata (deadlines, cost, mode), and assigns a "Priority Score" (1-10) to opportunities.
3. **State Management & Deduplication:** Uses a local SQLite database (`digest.db`) to keep track of previously seen items, ensuring you never get duplicate content. It also maintains a dynamic user profile (`profile.json`) to adjust to changing interests.
4. **Publishing:** Formats the best items into clean, readable Discord embeds and archives a Markdown copy locally.

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

## Setup & How to Run it on Your Own Discord

If you're visiting and want to run this agent for your own Discord server, follow these steps:

### 1. Get a Discord Webhook URL
1. Go to your Discord server and open **Server Settings** > **Integrations** > **Webhooks**.
2. Click **New Webhook**, name it (e.g., "AI Digest Bot"), and choose the channel where you want to receive the digest.
3. Click **Copy Webhook URL** and save it.

### 2. Local Setup
1. Clone the repository and navigate to the folder.
2. Create and activate a Python 3.11 environment.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   GEMINI_API_KEY=your-gemini-key
   DISCORD_WEBHOOK_URL=your-discord-webhook-url
   GEMINI_MODEL=gemini-2.0-flash
   ```
   *(Do **not** commit real API keys or Discord webhooks!)*

### 3. Run Locally

Run the pipeline immediately:
```bash
python main.py --run-now
```

Run using deterministic mock data without making external API calls (great for testing):
```bash
python main.py --run-now --mock
```

## Schedule

### Running as a Local Background Process
You can run the built-in local scheduler to run every day:
```bash
python main.py --schedule
```

### GitHub Actions (Recommended)
GitHub Actions is configured in `.github/workflows/daily-digest.yml` to automatically run every day at 1:30 UTC (7:00 AM IST).

To enable this on your own fork:
1. Go to your GitHub repository **Settings** > **Secrets and variables** > **Actions**.
2. Add these repository secrets:
   - `GEMINI_API_KEY`
   - `DISCORD_WEBHOOK_URL`
3. Enable workflows in the **Actions** tab of your repository. 

## Outputs

- **Discord**: Two rich embeds delivered to your channel — one for Tech News, one for Opportunities, with structured metadata.
- **Markdown archive** in `digests/YYYY-MM-DD.md`.
- **SQLite state** in `digest.db` (maintains history to prevent duplicate alerts).
- **Rolling profile** in `profile.json`.

## Opportunity Format

Each opportunity includes: Title, Organization, Category, Mode (Remote/Hybrid/In-person), Deadline, Cost, Difficulty, Priority Score (1-10), and a concise relevance summary explaining why it matters for an AI/ML student.
