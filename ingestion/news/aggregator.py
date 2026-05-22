"""News aggregator — fetch headlines from multiple free sources."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests


@dataclass
class RawArticle:
    """Raw article before distillation."""

    title: str
    source: str
    url: str
    published: str
    summary: str
    content: str = ""
    tickers: list[str] = field(default_factory=list)


class NewsAggregator:
    """Aggregate news from RSS feeds and free APIs."""

    # Default RSS feeds for financial news
    DEFAULT_FEEDS = [
        ("Reuters Markets", "https://www.reutersagency.com/feed/?taxonomy=markets&post_type=reuters-best"),
        ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
        ("CNBC Finance", "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
        ("MarketWatch Top Stories", "https://www.marketwatch.com/rss/topstories"),
        ("Seeking Alpha Latest", "https://seekingalpha.com/market_currents.xml"),
        ("Financial Times", "https://www.ft.com/?format=rss"),
        ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
        ("Investing.com", "https://www.investing.com/rss/news.rss"),
        ("ZeroHedge", "https://feeds.feedburner.com/zerohedge/feed"),
        ("Kitco Gold", "https://www.kitco.com/rss/news/gold.xml"),
    ]

    def __init__(self, newsapi_key: Optional[str] = None):
        self.newsapi_key = newsapi_key or os.getenv("NEWSAPI_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MarketMob/1.0 (Financial News Aggregator)"
        })

    def fetch_rss_feed(self, name: str, url: str, max_articles: int = 10) -> list[RawArticle]:
        """Fetch articles from a single RSS feed."""
        articles = []
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            for entry in feed.entries[:max_articles]:
                article = RawArticle(
                    title=entry.get("title", "").strip(),
                    source=name,
                    url=entry.get("link", ""),
                    published=entry.get("published", datetime.now(timezone.utc).isoformat()),
                    summary=entry.get("summary", "").strip()[:500],
                    content=entry.get("summary", "").strip(),
                )
                articles.append(article)
        except Exception as e:
            print(f"[WARN] Failed to fetch {name}: {e}")

        return articles

    def fetch_newsapi(self, query: str = "stock market OR finance OR earnings", max_articles: int = 20) -> list[RawArticle]:
        """Fetch from NewsAPI (free tier: 100 requests/day)."""
        if not self.newsapi_key:
            return []

        articles = []
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": max_articles,
                "apiKey": self.newsapi_key,
            }
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            for item in data.get("articles", []):
                article = RawArticle(
                    title=item.get("title", "").strip(),
                    source=item.get("source", {}).get("name", "NewsAPI"),
                    url=item.get("url", ""),
                    published=item.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                    summary=item.get("description", "").strip()[:500],
                    content=item.get("content", "").strip(),
                )
                articles.append(article)
        except Exception as e:
            print(f"[WARN] NewsAPI fetch failed: {e}")

        return articles

    def fetch_all(self, max_per_feed: int = 10, max_newsapi: int = 20) -> list[RawArticle]:
        """Fetch from all sources and deduplicate by URL."""
        all_articles = []

        # RSS feeds
        for name, url in self.DEFAULT_FEEDS:
            articles = self.fetch_rss_feed(name, url, max_per_feed)
            all_articles.extend(articles)

        # NewsAPI
        newsapi_articles = self.fetch_newsapi(max_articles=max_newsapi)
        all_articles.extend(newsapi_articles)

        # Deduplicate by URL
        seen_urls = set()
        unique = []
        for article in all_articles:
            if article.url and article.url not in seen_urls:
                seen_urls.add(article.url)
                unique.append(article)

        # Sort by published date (newest first)
        unique.sort(key=lambda a: a.published, reverse=True)

        return unique

    def extract_tickers_from_text(self, text: str) -> list[str]:
        """Extract potential stock tickers from article text."""
        import re
        # Match $TICKER or standalone 1-5 char uppercase words
        ticker_pattern = r'\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b'
        matches = re.findall(ticker_pattern, text)
        tickers = set()
        for m in matches:
            ticker = m[0] or m[1]
            # Filter out common words
            if ticker not in {"CEO", "CFO", "COO", "IPO", "ETF", "USA", "FED", "GDP", "CPI", "PPI", "API", "URL", "HTML", "RSS", "HTTP", "HTTPS"}:
                tickers.add(ticker)
        return sorted(tickers)

    def enrich_with_tickers(self, articles: list[RawArticle]) -> list[RawArticle]:
        """Extract tickers from article titles and summaries."""
        for article in articles:
            text = f"{article.title} {article.summary}"
            article.tickers = self.extract_tickers_from_text(text)
        return articles


if __name__ == "__main__":
    # Smoke test
    agg = NewsAggregator()
    articles = agg.fetch_all(max_per_feed=3, max_newsapi=5)
    articles = agg.enrich_with_tickers(articles)
    print(f"Fetched {len(articles)} unique articles")
    for a in articles[:5]:
        print(f"\n[{a.source}] {a.title}")
        print(f"  Tickers: {a.tickers}")
        print(f"  URL: {a.url}")
