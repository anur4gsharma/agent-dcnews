from __future__ import annotations

from pathlib import Path


def write_markdown_archive(digest: dict, digests_dir: Path) -> Path:
    digests_dir.mkdir(parents=True, exist_ok=True)
    path = digests_dir / f"{digest['date']}.md"
    lines = [f"# AI/Tech Digest - {digest['date']}", "", "## News", ""]
    for index, item in enumerate(digest.get("top_news", []), start=1):
        lines.extend(
            [
                f"{index}. [{item['title']}]({item['url']})",
                f"   - Source: {item.get('source', 'Unknown')}",
                f"   - Why it matters: {item['why_it_matters']}",
                "",
            ]
        )
    lines.extend(["## Opportunities", ""])
    for index, item in enumerate(digest.get("top_opportunities", []), start=1):
        lines.extend(
            [
                f"{index}. [{item['title']}]({item['url']})",
                f"   - Type: {item.get('type', 'opportunity')}",
                f"   - Why it matters: {item['why_it_matters']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

