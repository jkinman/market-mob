"""Tests for sentiment_formatter markdown output."""

import pytest

from analysis.sentiment.sentiment_scraper import SentimentResult, mock_backend
from analysis.sentiment.sentiment_formatter import (
    format_sentiment,
    format_sentiment_section,
    _label,
)


class TestFormatSentiment:
    def test_includes_ticker_and_source(self):
        r = mock_backend("AAPL")
        md = format_sentiment(r)
        assert "AAPL" in md
        assert "mock" in md

    def test_includes_score_and_label(self):
        r = SentimentResult("X", "mock", 0.75, 10)
        md = format_sentiment(r)
        assert "0.750" in md
        assert "Bullish" in md

    def test_includes_mentions(self):
        r = SentimentResult("X", "mock", 0.0, 42)
        md = format_sentiment(r)
        assert "42" in md

    def test_includes_sample_posts(self):
        r = SentimentResult("X", "mock", 0.0, 1, sample_posts=["Post one", "Post two"])
        md = format_sentiment(r)
        assert "Post one" in md
        assert "Post two" in md

    def test_limits_sample_posts(self):
        posts = [f"Post {i}" for i in range(10)]
        r = SentimentResult("X", "mock", 0.0, 1, sample_posts=posts)
        md = format_sentiment(r)
        # Only first 5 should appear
        assert md.count("Post ") == 5


class TestFormatSentimentSection:
    def test_empty_results(self):
        md = format_sentiment_section([])
        assert "No sentiment data available" in md

    def test_title_custom(self):
        md = format_sentiment_section([], title="Custom Title")
        assert "Custom Title" in md

    def test_multiple_results(self):
        results = [mock_backend("AAPL"), mock_backend("TSLA")]
        md = format_sentiment_section(results)
        assert "AAPL" in md
        assert "TSLA" in md
        assert "Social Sentiment" in md


class TestLabel:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0.6, "Bullish"),
            (0.5, "Bullish"),
            (0.3, "Slightly Bullish"),
            (0.1, "Slightly Bullish"),
            (0.05, "Neutral"),
            (0.0, "Neutral"),
            (-0.05, "Neutral"),
            (-0.1, "Slightly Bearish"),
            (-0.3, "Slightly Bearish"),
            (-0.5, "Bearish"),
            (-0.8, "Bearish"),
        ],
    )
    def test_label_mapping(self, score, expected):
        assert _label(score) == expected
