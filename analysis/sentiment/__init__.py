"""Sentiment analysis module — pluggable backends."""

from analysis.sentiment.sentiment_scraper import (
    SentimentResult,
    scrape_sentiment,
    scrape_sentiment_batch,
    mock_backend,
    xurl_backend,
    web_backend,
)
from analysis.sentiment.sentiment_formatter import (
    format_sentiment,
    format_sentiment_section,
)

__all__ = [
    "SentimentResult",
    "scrape_sentiment",
    "scrape_sentiment_batch",
    "mock_backend",
    "xurl_backend",
    "web_backend",
    "format_sentiment",
    "format_sentiment_section",
]
