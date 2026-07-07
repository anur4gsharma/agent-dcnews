# AI/Tech Weekly Digest Agent

Python agent that collects AI/tech news and opportunities, runs a multi-stage Gemini editor pipeline, posts the final digest to Discord, and archives a Markdown copy.

## Setup

1. Create and activate a Python 3.11 environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in:

```bash
GEMINI_API_KEY=your-rotated-gemini-key
DISCORD_WEBHOOK_URL=your-rotated-discord-webhook-url
GEMINI_MODEL=gemini-1.5-pro
```

Do not commit real API keys or Discord webhooks. If either was pasted into a chat or log, rotate it.

## Run Once

Use real sources and Gemini if credentials exist:

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

GitHub Actions is configured in `.github/workflows/daily-digest.yml` to run every Sunday at 1:30 UTC, which is Sunday 7:00 AM IST.

Add these repository secrets in GitHub:

- `GEMINI_API_KEY`
- `DISCORD_WEBHOOK_URL`

## Outputs

- Discord embed with News and Opportunities sections.
- Markdown archive in `digests/YYYY-MM-DD.md`.
- SQLite state in `digest.db`.
- Rolling profile state in `profile.json`.

