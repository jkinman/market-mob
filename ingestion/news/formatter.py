"""Formatter — generate the Mob Intel briefing output."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .correlator import CorrelatedInsight


class MobIntelFormatter:
    """Format correlated insights into the Mob Intel briefing."""

    def __init__(self, timezone_str: str = "America/Vancouver"):
        from config.loader import get_config
        cfg = get_config()
        self.timezone_str = cfg.settings.timezone

    def _now(self) -> str:
        """Get current timestamp in user's timezone."""
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(self.timezone_str))
        return now.strftime("%Y-%m-%d %H:%M %Z")

    def _urgency_emoji(self, urgency: int) -> str:
        """Get emoji for urgency level."""
        return {5: "🔥", 4: "⚡", 3: "📢", 2: "📌", 1: "💡"}.get(urgency, "💡")

    def _sentiment_emoji(self, sentiment: str) -> str:
        """Get emoji for sentiment."""
        return {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(sentiment, "⚪")

    def format_briefing(self, insights: list[CorrelatedInsight]) -> str:
        """Generate the full Mob Intel briefing."""
        lines = [
            f"🚨 MOB INTEL — {self._now()}",
            "",
            "=" * 50,
            "",
        ]

        # Section 1: Breaking / Market-Moving
        breaking = [i for i in insights if i.category == "breaking" and i.urgency >= 4]
        if breaking:
            lines.append("🔥 BREAKING / MARKET-MOVING:")
            lines.append("")
            for insight in breaking[:5]:
                emoji = self._urgency_emoji(insight.urgency)
                sent = self._sentiment_emoji(insight.sentiment)
                lines.append(f"{emoji} {sent} {insight.headline}")
                lines.append(f"   {insight.detail}")
                if insight.tickers:
                    lines.append(f"   Tickers: {', '.join(insight.tickers)}")
                lines.append("")

        # Section 2: Industry Intel
        industry = [i for i in insights if i.category == "industry"]
        if industry:
            lines.append("🏭 INDUSTRY INTEL:")
            lines.append("")
            for insight in industry[:6]:
                sent = self._sentiment_emoji(insight.sentiment)
                lines.append(f"{sent} {insight.headline}")
                lines.append(f"   {insight.detail}")
                if insight.themes:
                    lines.append(f"   Themes: {', '.join(insight.themes)}")
                lines.append("")

        # Section 3: Emerging Narratives
        emerging = [i for i in insights if i.category == "emerging"]
        if emerging:
            lines.append("🎯 EMERGING NARRATIVES:")
            lines.append("")
            for insight in emerging[:5]:
                sent = self._sentiment_emoji(insight.sentiment)
                lines.append(f"{sent} {insight.headline}")
                lines.append(f"   {insight.detail}")
                if insight.themes:
                    lines.append(f"   Themes: {', '.join(insight.themes)}")
                lines.append("")

        # Section 4: Market Predictions / Consensus
        predictions = [i for i in insights if i.category == "prediction"]
        if predictions:
            lines.append("📊 MARKET PREDICTIONS / CONSENSUS:")
            lines.append("")
            for insight in predictions[:5]:
                sent = self._sentiment_emoji(insight.sentiment)
                lines.append(f"{sent} {insight.headline}")
                lines.append(f"   {insight.detail}")
                lines.append("")

        # Section 5: Macro / Policy
        macro = [i for i in insights if i.category in ("macro", "policy")]
        if macro:
            lines.append("🏛️ MACRO / POLICY:")
            lines.append("")
            for insight in macro[:5]:
                sent = self._sentiment_emoji(insight.sentiment)
                lines.append(f"{sent} {insight.headline}")
                lines.append(f"   {insight.detail}")
                lines.append("")

        # Section 6: Commodities
        commodities = [i for i in insights if i.category == "commodity"]
        if commodities:
            lines.append("⛏️ COMMODITIES:")
            lines.append("")
            for insight in commodities[:5]:
                sent = self._sentiment_emoji(insight.sentiment)
                lines.append(f"{sent} {insight.headline}")
                lines.append(f"   {insight.detail}")
                lines.append("")

        # Section 7: Contrarian Signals
        contrarian = [i for i in insights if i.category == "contrarian"]
        if contrarian:
            lines.append("⚠️ CONTRARIAN / UNUSUAL SIGNALS:")
            lines.append("")
            for insight in contrarian[:5]:
                sent = self._sentiment_emoji(insight.sentiment)
                lines.append(f"{sent} {insight.headline}")
                lines.append(f"   {insight.detail}")
                lines.append("")

        # Section 8: Watchlist / Portfolio Intersections
        watchlist_hits = [i for i in insights if i.watchlist_match or i.portfolio_match]
        if watchlist_hits:
            lines.append("🎯 YOUR WATCHLIST INTERSECTIONS:")
            lines.append("")
            for insight in watchlist_hits[:8]:
                flag = ""
                if insight.portfolio_match:
                    flag += " [PORTFOLIO]"
                if insight.watchlist_match:
                    flag += " [WATCHLIST]"
                sent = self._sentiment_emoji(insight.sentiment)
                lines.append(f"{sent}{flag} {insight.headline}")
                lines.append(f"   {insight.detail}")
                if insight.matched_tickers:
                    lines.append(f"   Matched: {', '.join(insight.matched_tickers)}")
                lines.append("")

        lines.append("=" * 50)
        lines.append("")
        lines.append("📡 Sources scanned: Bloomberg, CNBC, MarketWatch, Seeking Alpha, FT, Yahoo Finance, Investing.com, ZeroHedge")
        lines.append("🔄 Next update: Tomorrow 7:00 AM PT")

        return "\n".join(lines)

    def format_compact(self, insights: list[CorrelatedInsight]) -> str:
        """Generate a compact one-screen version for quick checks."""
        lines = [
            f"🚨 MOB INTEL — {self._now()}",
            "",
        ]

        # Top 3 most important
        top = insights[:3]
        for insight in top:
            emoji = self._urgency_emoji(insight.urgency)
            sent = self._sentiment_emoji(insight.sentiment)
            flag = ""
            if insight.portfolio_match:
                flag += " [YOUR STOCK]"
            elif insight.watchlist_match:
                flag += " [WATCHLIST]"
            lines.append(f"{emoji} {sent}{flag} {insight.headline}")

        # Watchlist hits count
        hits = len([i for i in insights if i.watchlist_match or i.portfolio_match])
        if hits:
            lines.append(f"\n🎯 {hits} stories relevant to your positions")

        return "\n".join(lines)


if __name__ == "__main__":
    # Smoke test
    from .aggregator import NewsAggregator
    from .distiller import NewsDistiller
    from .correlator import WatchlistCorrelator

    agg = NewsAggregator()
    articles = agg.fetch_all(max_per_feed=2, max_newsapi=5)
    articles = agg.enrich_with_tickers(articles)

    distiller = NewsDistiller()
    insights = distiller.distill(articles)

    correlator = WatchlistCorrelator()
    correlated = correlator.correlate(insights)

    formatter = MobIntelFormatter()
    briefing = formatter.format_briefing(correlated)
    print(briefing)
