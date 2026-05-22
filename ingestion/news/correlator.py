"""Correlator — cross-reference distilled insights against watchlist and portfolio."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from .distiller import DistilledInsight


@dataclass
class CorrelatedInsight(DistilledInsight):
    """An insight enriched with watchlist/portfolio relevance."""

    watchlist_match: bool = False
    portfolio_match: bool = False
    matched_tickers: list[str] = field(default_factory=list)
    relevance_score: float = 0.0  # 0.0 to 1.0


class WatchlistCorrelator:
    """Cross-reference insights against user's watchlist and portfolio."""

    def __init__(
        self,
        watchlist_path: Optional[str] = None,
        portfolio_path: Optional[str] = None,
    ):
        self.watchlist_path = watchlist_path or "config/watchlist.json"
        self.portfolio_path = portfolio_path or "config/persona.json"
        self.watchlist = self._load_watchlist()
        self.portfolio = self._load_portfolio()

    def _load_watchlist(self) -> list[str]:
        """Load tickers from watchlist config."""
        try:
            with open(self.watchlist_path, "r") as f:
                data = json.load(f)
                return [item["ticker"].upper() for item in data if item.get("status") == "active"]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _load_portfolio(self) -> list[str]:
        """Load tickers from portfolio/persona config."""
        try:
            with open(self.portfolio_path, "r") as f:
                data = json.load(f)
                positions = data.get("current_positions", [])
                return [pos["ticker"].upper() for pos in positions]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return []

    def correlate(self, insights: list[DistilledInsight]) -> list[CorrelatedInsight]:
        """Cross-reference insights against watchlist and portfolio."""
        correlated = []

        for insight in insights:
            matched = []
            watchlist_hit = False
            portfolio_hit = False

            for ticker in insight.tickers:
                ticker_upper = ticker.upper()
                if ticker_upper in self.watchlist:
                    matched.append(ticker_upper)
                    watchlist_hit = True
                if ticker_upper in self.portfolio:
                    matched.append(ticker_upper)
                    portfolio_hit = True

            # Deduplicate matched tickers
            matched = list(set(matched))

            # Calculate relevance score
            relevance = 0.0
            if watchlist_hit:
                relevance += 0.4
            if portfolio_hit:
                relevance += 0.5
            if insight.urgency >= 4:
                relevance += 0.1

            correlated.append(CorrelatedInsight(
                category=insight.category,
                headline=insight.headline,
                detail=insight.detail,
                tickers=insight.tickers,
                sentiment=insight.sentiment,
                urgency=insight.urgency,
                sources=insight.sources,
                themes=insight.themes,
                watchlist_match=watchlist_hit,
                portfolio_match=portfolio_hit,
                matched_tickers=matched,
                relevance_score=min(relevance, 1.0),
            ))

        # Sort by relevance (highest first), then urgency
        correlated.sort(key=lambda x: (x.relevance_score, x.urgency), reverse=True)
        return correlated

    def get_watchlist_hits(self, correlated: list[CorrelatedInsight]) -> list[CorrelatedInsight]:
        """Get only insights that match the watchlist."""
        return [c for c in correlated if c.watchlist_match or c.portfolio_match]

    def get_thematic_hits(self, correlated: list[CorrelatedInsight], themes: list[str]) -> list[CorrelatedInsight]:
        """Get insights matching specific themes (e.g., ['gold', 'copper', 'ai'])."""
        theme_set = set(t.lower() for t in themes)
        return [
            c for c in correlated
            if any(t.lower() in theme_set for t in c.themes)
        ]


if __name__ == "__main__":
    # Smoke test
    from .aggregator import NewsAggregator
    from .distiller import NewsDistiller

    agg = NewsAggregator()
    articles = agg.fetch_all(max_per_feed=2, max_newsapi=5)
    articles = agg.enrich_with_tickers(articles)

    distiller = NewsDistiller()
    insights = distiller.distill(articles)

    correlator = WatchlistCorrelator()
    correlated = correlator.correlate(insights)

    print(f"\nWatchlist: {correlator.watchlist}")
    print(f"Portfolio: {correlator.portfolio}\n")

    print("=== TOP INSIGHTS ===")
    for c in correlated[:10]:
        match_flag = ""
        if c.watchlist_match:
            match_flag += " [WATCHLIST]"
        if c.portfolio_match:
            match_flag += " [PORTFOLIO]"

        print(f"\n[{c.category.upper()}] Urgency: {c.urgency}/5 | Relevance: {c.relevance_score:.1f}{match_flag}")
        print(f"  {c.headline}")
        if c.matched_tickers:
            print(f"  Matched: {', '.join(c.matched_tickers)}")
