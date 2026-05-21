"""Tests for YouTube RSS monitor."""

import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch, mock_open

import pytest

from ingestion.youtube.rss_monitor import (
    get_channel_rss_url,
    fetch_channel_videos,
    load_seen_videos,
    save_seen_videos,
    check_channels_for_new_videos,
    run_monitor,
)


class TestGetChannelRssUrl:
    """Tests for RSS URL building."""

    def test_builds_correct_url(self):
        """Should build correct RSS URL."""
        url = get_channel_rss_url("UC1234567890")
        assert url == "https://www.youtube.com/feeds/videos.xml?channel_id=UC1234567890"


class TestFetchChannelVideos:
    """Tests for RSS fetching."""

    @patch("ingestion.youtube.rss_monitor.feedparser.parse")
    def test_fetch_success(self, mock_parse):
        """Should parse RSS feed entries."""
        mock_entry = MagicMock()
        mock_entry.yt_videoid = "abc123"
        mock_entry.title = "Test Video"
        mock_entry.published = "2024-01-01T00:00:00Z"
        mock_entry.link = "https://youtu.be/abc123"
        mock_entry.author = "Test Channel"

        # feedparser uses .get() for some attributes
        mock_entry.get.side_effect = lambda key, default="": {
            "yt_videoid": "abc123",
            "title": "Test Video",
            "published": "2024-01-01T00:00:00Z",
            "link": "https://youtu.be/abc123",
            "author": "Test Channel",
        }.get(key, default)

        mock_parse.return_value = MagicMock(entries=[mock_entry])

        result = fetch_channel_videos("UC123")

        assert len(result) == 1
        assert result[0]["id"] == "abc123"
        assert result[0]["title"] == "Test Video"

    @patch("ingestion.youtube.rss_monitor.feedparser.parse")
    def test_fetch_empty(self, mock_parse):
        """Should return empty list for empty feed."""
        mock_parse.return_value = MagicMock(entries=[])

        result = fetch_channel_videos("UC123")

        assert result == []

    @patch("ingestion.youtube.rss_monitor.feedparser.parse")
    def test_fetch_error(self, mock_parse):
        """Should return empty list on error."""
        mock_parse.side_effect = Exception("Network error")

        result = fetch_channel_videos("UC123")

        assert result == []


class TestSeenVideos:
    """Tests for seen video tracking."""

    def test_load_nonexistent(self, tmp_path):
        """Should return empty dict if file doesn't exist."""
        path = str(tmp_path / "seen.json")
        result = load_seen_videos(path)
        assert result == {}

    def test_load_existing(self, tmp_path):
        """Should load existing seen videos."""
        path = str(tmp_path / "seen.json")
        data = {"vid1": {"title": "Test"}}
        with open(path, "w") as f:
            json.dump(data, f)

        result = load_seen_videos(path)
        assert result == data

    def test_save_and_load(self, tmp_path):
        """Should save and load roundtrip."""
        path = str(tmp_path / "seen.json")
        data = {"vid1": {"title": "Test", "detected_at": "2024-01-01"}}

        save_seen_videos(data, path)
        loaded = load_seen_videos(path)

        assert loaded == data


class TestCheckChannels:
    """Tests for channel checking."""

    @patch("ingestion.youtube.rss_monitor.fetch_channel_videos")
    @patch("ingestion.youtube.rss_monitor.load_seen_videos")
    @patch("ingestion.youtube.rss_monitor.save_seen_videos")
    def test_find_new_videos(self, mock_save, mock_load, mock_fetch):
        """Should detect new videos."""
        mock_load.return_value = {}  # No seen videos
        mock_fetch.return_value = [
            {"id": "new1", "title": "New Video", "published": "2024-01-01"}
        ]

        channels = [{"name": "Test", "channel_id": "UC123", "trust_level": "high"}]
        result = check_channels_for_new_videos(channels)

        assert len(result) == 1
        assert result[0]["id"] == "new1"
        mock_save.assert_called_once()

    @patch("ingestion.youtube.rss_monitor.fetch_channel_videos")
    @patch("ingestion.youtube.rss_monitor.load_seen_videos")
    @patch("ingestion.youtube.rss_monitor.save_seen_videos")
    def test_ignore_seen_videos(self, mock_save, mock_load, mock_fetch):
        """Should not return already seen videos."""
        mock_load.return_value = {"old1": {"title": "Old"}}
        mock_fetch.return_value = [
            {"id": "old1", "title": "Old Video", "published": "2024-01-01"}
        ]

        channels = [{"name": "Test", "channel_id": "UC123"}]
        result = check_channels_for_new_videos(channels)

        assert len(result) == 0

    @patch("ingestion.youtube.rss_monitor.fetch_channel_videos")
    @patch("ingestion.youtube.rss_monitor.load_seen_videos")
    @patch("ingestion.youtube.rss_monitor.save_seen_videos")
    def test_multiple_channels(self, mock_save, mock_load, mock_fetch):
        """Should check multiple channels."""
        mock_load.return_value = {}
        mock_fetch.side_effect = [
            [{"id": "vid1", "title": "Video 1"}],
            [{"id": "vid2", "title": "Video 2"}],
        ]

        channels = [
            {"name": "Ch1", "channel_id": "UC1"},
            {"name": "Ch2", "channel_id": "UC2"},
        ]
        result = check_channels_for_new_videos(channels)

        assert len(result) == 2
        assert mock_fetch.call_count == 2


class TestRunMonitor:
    """Tests for full monitor run."""

    @patch("ingestion.youtube.rss_monitor.check_channels_for_new_videos")
    @patch("builtins.open", mock_open(read_data='{"channels": [{"name": "Test", "channel_id": "UC123"}]}'))
    def test_run_with_config(self, mock_check):
        """Should load config and check channels."""
        mock_check.return_value = []

        result = run_monitor("config/sources.json")

        assert result == []
        mock_check.assert_called_once()

    def test_run_without_config(self):
        """Should return empty if no config."""
        result = run_monitor("nonexistent.json")
        assert result == []
