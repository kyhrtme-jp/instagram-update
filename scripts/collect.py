import feedparser
from datetime import datetime, timezone, timedelta

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
