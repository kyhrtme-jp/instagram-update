import feedparser
import anthropic
import requests
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path

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
                    description = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                    entries.append({
                        "title": entry.title,
                        "url": entry.link,
                        "published": published.strftime("%Y-%m-%d"),
                        "description": description,
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


def translate_title(title: str) -> str:
    """Claude APIで記事タイトルを日本語に翻訳する"""
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": f"以下の英語タイトルを自然な日本語に翻訳してください。翻訳結果のみ返してください。\n{title}"
                }
            ]
        )
        result = response.content[0].text.strip()
        print(f"  翻訳: {title} → {result}")
        return result
    except Exception as e:
        print(f"  翻訳失敗: {title} ({e})")
        return title


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
            title_ja = entry.get("title_ja") or entry["title"]
            lines.append(f"### {title_ja}")
            lines.append(f"- 元記事: [{entry['title']}]({entry['url']})")
            lines.append(f"- 公開日: {entry['published']}")
            if entry.get("summary"):
                lines.append(f"- 要約: {entry['summary']}")
            lines.append("")

    return "\n".join(lines)


def notify_google_chat(
    webhook_url: str,
    entries_by_source: dict,
    date_str: str,
    report_url: str
) -> None:
    """Google Chat Webhookに週次サマリーを送信する"""
    all_entries = [e for entries in entries_by_source.values() for e in entries]
    if not all_entries:
        return

    lines = [f"📱 今週のInstagramアルゴリズム情報 ({date_str})\n"]
    for entry in all_entries[:10]:
        source = next(
            (name for name, entries in entries_by_source.items() if entry in entries),
            ""
        )
        title_ja = entry.get("title_ja") or entry["title"]
        lines.append(f"【{source}】{title_ja}")

    lines.append(f"\n詳細: {report_url}")

    payload = {"text": "\n".join(lines)}
    requests.post(webhook_url, json=payload, timeout=10)


def main(updates_dir: str = "updates") -> None:
    """メイン実行関数"""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")

    entries_by_source = {}
    for source in SOURCES:
        print(f"Fetching {source['name']}...")
        entries = fetch_recent_entries(source["url"])
        for entry in entries:
            entry["title_ja"] = translate_title(entry.get("title", ""))
            entry["summary"] = summarize_in_japanese(entry.get("description", ""), entry.get("title", ""))
        entries_by_source[source["name"]] = entries
        print(f"  {len(entries)} entries found")

    markdown = build_markdown(entries_by_source, date_str)
    if markdown is None:
        print("No new entries this week. Skipping.")
        return

    output_path = Path(updates_dir) / f"{date_str}.md"
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Saved: {output_path}")

    if webhook_url:
        report_url = (
            f"https://github.com/kyhrtme-jp/instagram-update/blob/main/updates/{date_str}.md"
        )
        notify_google_chat(webhook_url, entries_by_source, date_str, report_url)
        print("Notified Google Chat.")


if __name__ == "__main__":
    main()
