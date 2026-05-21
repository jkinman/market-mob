"""Pluggable sentiment scraper with mock, xurl, and web backends."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class SentimentResult:
    """Container for sentiment data."""

    ticker: str
    source: str
    sentiment_score: float  # -1.0 to 1.0
    mention_count: int
    sample_posts: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        # Clamp sentiment_score
        self.sentiment_score = max(-1.0, min(1.0, float(self.sentiment_score)))
        self.mention_count = int(self.mention_count)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

def _mock_seed(ticker: str) -> float:
    """Deterministic float in [-1, 1] derived from ticker name."""
    h = hashlib.md5(ticker.upper().encode()).hexdigest()
    return (int(h, 16) % 2001 - 1000) / 1000.0


def mock_backend(ticker: str) -> SentimentResult:
    """Return deterministic mock sentiment for testing."""
    seed = _mock_seed(ticker)
    mention_count = abs(int(seed * 1000)) + 10
    sentiment = round(seed, 3)
    sample_posts = [
        f"Mock post A about ${ticker.upper()}",
        f"Mock post B about ${ticker.upper()}",
    ]
    return SentimentResult(
        ticker=ticker.upper(),
        source="mock",
        sentiment_score=sentiment,
        mention_count=mention_count,
        sample_posts=sample_posts,
    )


def xurl_backend(ticker: str) -> Optional[SentimentResult]:
    """Placeholder backend using xurl CLI (requires manual OAuth setup).

    Returns None if xurl is not installed or exits non-zero.
    """
    if shutil.which("xurl") is None:
        return None

    try:
        proc = subprocess.run(
            ["xurl", "search", f"${ticker.upper()}", "--json", "--limit", "20"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        data = json.loads(proc.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None

    posts = data if isinstance(data, list) else data.get("posts", [])
    if not posts:
        return SentimentResult(
            ticker=ticker.upper(),
            source="xurl",
            sentiment_score=0.0,
            mention_count=0,
            sample_posts=[],
        )

    # Very naive sentiment: count words
    positive_words = {"bullish", "moon", "rocket", "buy", "long", "up", "gain", "breakout"}
    negative_words = {"bearish", "dump", "sell", "short", "down", "loss", "crash", "panic"}

    pos = neg = 0
    sample_posts: list[str] = []
    for p in posts[:20]:
        text = p.get("text", p.get("content", "")).lower()
        sample_posts.append(text[:140])
        words = set(text.split())
        pos += len(words & positive_words)
        neg += len(words & negative_words)

    total = pos + neg
    if total == 0:
        score = 0.0
    else:
        score = round((pos - neg) / total, 3)

    return SentimentResult(
        ticker=ticker.upper(),
        source="xurl",
        sentiment_score=score,
        mention_count=len(posts),
        sample_posts=sample_posts[:5],
    )


def web_backend(ticker: str) -> Optional[SentimentResult]:
    """Placeholder web scraping backend using requests.

    Currently returns None (not implemented) to avoid accidental scraping.
    Can be extended to hit a public API or search endpoint.
    """
    # TODO: implement real web scraping (e.g., Reddit, StockTwits public)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_BACKENDS = {
    "mock": mock_backend,
    "xurl": xurl_backend,
    "web": web_backend,
}


def scrape_sentiment(ticker: str, source: str = "auto") -> SentimentResult:
    """Scrape sentiment for a single ticker.

    Args:
        ticker: Stock symbol
        source: Backend to use — "mock", "xurl", "web", or "auto"
                (auto tries xurl → web → mock)

    Returns:
        SentimentResult

    Raises:
        ValueError: If source is unknown.
    """
    ticker = ticker.upper()

    if source == "auto":
        for name in ("xurl", "web", "mock"):
            backend = _BACKENDS[name]
            result = backend(ticker)
            if result is not None:
                return result
        # Fallback should never happen because mock always returns
        return mock_backend(ticker)

    if source not in _BACKENDS:
        raise ValueError(f"Unknown source '{source}'. Choose from: {list(_BACKENDS.keys()) + ['auto']}")

    backend = _BACKENDS[source]
    result = backend(ticker)
    if result is None:
        raise RuntimeError(f"Backend '{source}' returned no data for {ticker}")
    return result


def scrape_sentiment_batch(tickers: list[str], source: str = "auto") -> dict[str, SentimentResult]:
    """Scrape sentiment for multiple tickers.

    Args:
        tickers: List of stock symbols
        source: Backend to use (see scrape_sentiment)

    Returns:
        Dict mapping ticker -> SentimentResult
    """
    results: dict[str, SentimentResult] = {}
    for ticker in tickers:
        try:
            results[ticker.upper()] = scrape_sentiment(ticker, source=source)
        except Exception as exc:
            # Graceful per-ticker failure — store a zero-sentiment result
            results[ticker.upper()] = SentimentResult(
                ticker=ticker.upper(),
                source="error",
                sentiment_score=0.0,
                mention_count=0,
                sample_posts=[f"Error: {exc}"],
            )
    return results


if __name__ == "__main__":
    # Smoke test
    for src in ("mock", "auto"):
        r = scrape_sentiment("AAPL", source=src)
        print(f"[{src}] {r.ticker}: score={r.sentiment_score}, mentions={r.mention_count}")
