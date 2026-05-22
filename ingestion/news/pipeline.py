"""Mob Intel pipeline — end-to-end news scanning and briefing generation."""

from __future__ import annotations

import os
from typing import Optional

from .aggregator import NewsAggregator
from .distiller import NewsDistiller
from .correlator import WatchlistCorrelator
from .formatter import MobIntelFormatter


class MobIntelPipeline:
    """End-to-end pipeline: fetch → distill → correlate → format."""

    def __init__(
        self,
        newsapi_key: Optional[str] = None,
        watchlist_path: Optional[str] = None,
        portfolio_path: Optional[str] = None,
    ):
        self.aggregator = NewsAggregator(newsapi_key=newsapi_key)
        self.distiller = NewsDistiller()
        self.correlator = WatchlistCorrelator(
            watchlist_path=watchlist_path,
            portfolio_path=portfolio_path,
        )
        self.formatter = MobIntelFormatter()

    def run(
        self,
        max_articles: int = 100,
        output_format: str = "full",
    ) -> str:
        """Run the full pipeline and return formatted briefing.

        Args:
            max_articles: Max articles to fetch per source
            output_format: "full" or "compact"

        Returns:
            Formatted briefing string
        """
        print("[MobIntel] Fetching news...")
        articles = self.aggregator.fetch_all(
            max_per_feed=min(max_articles // 10, 10),
            max_newsapi=min(max_articles // 2, 20),
        )
        print(f"[MobIntel] Fetched {len(articles)} articles")

        if not articles:
            return "🚨 MOB INTEL — No news available at this time."

        print("[MobIntel] Enriching with tickers...")
        articles = self.aggregator.enrich_with_tickers(articles)

        print("[MobIntel] Distilling insights...")
        insights = self.distiller.distill_batch(articles)
        print(f"[MobIntel] Distilled {len(insights)} insights")

        print("[MobIntel] Correlating with watchlist...")
        correlated = self.correlator.correlate(insights)
        hits = len(self.correlator.get_watchlist_hits(correlated))
        print(f"[MobIntel] {hits} watchlist/portfolio hits")

        print("[MobIntel] Formatting briefing...")
        if output_format == "compact":
            return self.formatter.format_compact(correlated)
        return self.formatter.format_briefing(correlated)

    def run_for_ticker(self, ticker: str) -> str:
        """Run pipeline focused on a specific ticker.

        Args:
            ticker: Stock symbol to focus on

        Returns:
            Formatted briefing string
        """
        print(f"[MobIntel] Fetching news for {ticker}...")
        articles = self.aggregator.fetch_all(max_per_feed=5, max_newsapi=10)
        articles = self.aggregator.enrich_with_tickers(articles)

        # Filter to articles mentioning the ticker
        ticker_upper = ticker.upper()
        filtered = [a for a in articles if ticker_upper in [t.upper() for t in a.tickers]]

        if not filtered:
            return f"🚨 MOB INTEL — No recent news found for {ticker}."

        print(f"[MobIntel] Found {len(filtered)} articles mentioning {ticker}")
        insights = self.distiller.distill(filtered)
        correlated = self.correlator.correlate(insights)

        return self.formatter.format_briefing(correlated)


if __name__ == "__main__":
    # Full pipeline smoke test
    pipeline = MobIntelPipeline()
    briefing = pipeline.run(output_format="full")
    print(briefing)
