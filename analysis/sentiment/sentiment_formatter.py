"""Format SentimentResult objects into markdown for reports."""

from analysis.sentiment.sentiment_scraper import SentimentResult


def format_sentiment(result: SentimentResult) -> str:
    """Format a single SentimentResult as markdown.

    Args:
        result: SentimentResult dataclass

    Returns:
        Markdown string
    """
    sentiment_label = _label(result.sentiment_score)
    lines = [
        f"- **Ticker**: {result.ticker}",
        f"- **Source**: {result.source}",
        f"- **Sentiment Score**: {result.sentiment_score:+.3f} ({sentiment_label})",
        f"- **Mentions**: {result.mention_count}",
        f"- **Timestamp**: {result.timestamp}",
    ]

    if result.sample_posts:
        lines.append("- **Sample Posts**:")
        for post in result.sample_posts[:5]:
            lines.append(f"  - {post}")

    return "\n".join(lines)


def format_sentiment_section(results: list[SentimentResult], title: str = "Social Sentiment") -> str:
    """Format a list of SentimentResults as a markdown section.

    Args:
        results: List of SentimentResult objects
        title: Section heading

    Returns:
        Markdown string
    """
    if not results:
        return f"## {title}\n\nNo sentiment data available.\n"

    lines = [f"## {title}", ""]
    for r in results:
        lines.append(format_sentiment(r))
        lines.append("")

    return "\n".join(lines)


def _label(score: float) -> str:
    """Map a sentiment score to a human-readable label."""
    if score >= 0.5:
        return "Bullish"
    if score >= 0.1:
        return "Slightly Bullish"
    if score <= -0.5:
        return "Bearish"
    if score <= -0.1:
        return "Slightly Bearish"
    return "Neutral"


if __name__ == "__main__":
    # Smoke test
    from analysis.sentiment.sentiment_scraper import mock_backend

    r = mock_backend("TSLA")
    print(format_sentiment(r))
    print("---")
    print(format_sentiment_section([r, mock_backend("AAPL")]))
