from __future__ import annotations

from pathlib import Path


def write_markdown_archive(digest: dict, digests_dir: Path) -> Path:
    digests_dir.mkdir(parents=True, exist_ok=True)
    path = digests_dir / f"{digest['date']}.md"

    lines = [f"# AI/Tech Opportunity Digest — {digest['date']}", ""]

    # --- News ---
    lines.extend(["## 📰 Top News", ""])
    for index, item in enumerate(digest.get("top_news", []), start=1):
        lines.extend([
            f"### {index}. [{item['title']}]({item['url']})",
            f"- **Source:** {item.get('source', 'Unknown')}",
            f"- **Why it matters:** {item['why_it_matters']}",
            "",
        ])

    # --- Opportunities ---
    lines.extend(["## 🚀 Opportunities", ""])
    for index, item in enumerate(digest.get("top_opportunities", []), start=1):
        lines.append(f"### {index}. [{item['title']}]({item['url']})")
        lines.append(f"- **Organization:** {item.get('organization', 'Unknown')}")
        lines.append(f"- **Category:** {item.get('category', 'opportunity')}")
        lines.append(f"- **Mode:** {item.get('mode', 'Unknown')}")
        lines.append(f"- **Deadline:** {item.get('deadline', 'Unknown')}")
        lines.append(f"- **Cost:** {item.get('cost', 'Unknown')}")
        lines.append(f"- **Difficulty:** {item.get('difficulty', 'Unknown')}")
        lines.append(f"- **Priority Score:** {item.get('priority_score', '—')}/10")
        lines.append(f"- **Why it matters:** {item['why_it_matters']}")
        lines.append("")

    # --- Community Pulse (Reddit Sentiment) ---
    sentiment = digest.get("sentiment", [])
    if sentiment:
        lines.extend(["## 💬 Community Pulse", ""])
        lines.append("What the AI/ML community is talking about this week:")
        lines.append("")
        for item in sentiment[:8]:
            score = item.get("score", 0)
            comments = item.get("comments", 0)
            subreddit = item.get("subreddit", "")
            title = item.get("title", "")
            url = item.get("url", "")
            lines.append(f"- **[{title}]({url})** — r/{subreddit} · ⬆ {score:,} · 💬 {comments:,}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
