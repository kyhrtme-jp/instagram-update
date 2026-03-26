import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.collect import fetch_recent_entries, SOURCES

def test_sources_defined():
    """RSSソースが3つ定義されていること"""
    assert len(SOURCES) == 3
    for source in SOURCES:
        assert "name" in source
        assert "url" in source

def test_fetch_recent_entries_returns_entries():
    """過去7日以内の記事のみ返すこと"""
    mock_entry = MagicMock()
    mock_entry.title = "Test Article"
    mock_entry.link = "https://example.com/article"
    mock_entry.published_parsed = (datetime.now(timezone.utc) - timedelta(days=3)).timetuple()

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]

    with patch("feedparser.parse", return_value=mock_feed):
        entries = fetch_recent_entries("https://example.com/feed", days=7)

    assert len(entries) == 1
    assert entries[0]["title"] == "Test Article"
    assert entries[0]["url"] == "https://example.com/article"

def test_fetch_recent_entries_filters_old():
    """7日以上前の記事は除外すること"""
    mock_entry = MagicMock()
    mock_entry.title = "Old Article"
    mock_entry.link = "https://example.com/old"
    mock_entry.published_parsed = (datetime.now(timezone.utc) - timedelta(days=10)).timetuple()

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]

    with patch("feedparser.parse", return_value=mock_feed):
        entries = fetch_recent_entries("https://example.com/feed", days=7)

    assert len(entries) == 0

def test_fetch_recent_entries_handles_error():
    """RSS取得エラー時は空リストを返すこと"""
    with patch("feedparser.parse", side_effect=Exception("Network error")):
        entries = fetch_recent_entries("https://example.com/feed", days=7)

    assert entries == []
