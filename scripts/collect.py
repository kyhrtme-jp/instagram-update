import feedparser
import anthropic
from datetime import datetime, timezone, timedelta
from typing import Optional

SOURCES = [
    {
        "name": "Meta公式ブログ",
        "url": "https://about.fb.com/news/feed/"
    },
    {
        "name": "Later.com",
        "url": "https://later.com/blog/feed/"
    },
    {
        "name": "Social Media Today",
        "url": "https://www.socialmediatoday.com/rss/"
    }
]


def fetch_recent_entries(feed_url: str, days: int = 7) -> list[dict]:
    """RSSフィードから過去N日以内の記事を取得する"""
    try:
        feed = feedparser.parse(feed_url)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        entries = []

        for entry in feed.entries:
            try:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                if published >= cutoff:
                    entries.append({
                        "title": entry.title,
                        "url": entry.link,
                        "published": published.strftime("%Y-%m-%d"),
                    })
            except (AttributeError, TypeError):
                continue

        return entries
    except Exception:
        return []


def summarize_in_japanese(text: str, title: str) -> str:
    """Claude APIでテキストを日本語200字以内に要約する"""
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"以下の英語記事を日本語200字以内で要約してください。\n"
                        f"タイトル: {title}\n"
                        f"本文: {text[:1000]}"
                    )
                }
            ]
        )
        return response.content[0].text
    except Exception:
        return ""


def build_markdown(entries_by_source: dict, date_str: str) -> Optional[str]:
    """収集結果からMarkdownレポートを生成する"""
    all_empty = all(len(entries) == 0 for entries in entries_by_source.values())
    if all_empty:
        return None

    lines = [f"# Instagram アルゴリズム情報 - {date_str}\n"]

    for source_name, entries in entries_by_source.items():
        if not entries:
            continue
        lines.append(f"## {source_name}\n")
        for entry in entries:
            lines.append(f"### {entry['title']}")
            lines.append(f"- 元記事: [{entry['url']}]({entry['url']})")
            lines.append(f"- 公開日: {entry['published']}")
            if entry.get("summary"):
                lines.append(f"- 要約: {entry['summary']}")
            lines.append("")

    return "\n".join(lines)
