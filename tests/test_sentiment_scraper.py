"""Tests for sentiment_scraper backends and public API."""

import pytest

from analysis.sentiment.sentiment_scraper import (
    SentimentResult,
    mock_backend,
    xurl_backend,
    web_backend,
    scrape_sentiment,
    scrape_sentiment_batch,
    _mock_seed,
)


class TestMockBackend:
    def test_returns_sentiment_result(self):
        r = mock_backend("AAPL")
        assert isinstance(r, SentimentResult)
        assert r.ticker == "AAPL"
        assert r.source == "mock"

    def test_deterministic(self):
        r1 = mock_backend("TSLA")
        r2 = mock_backend("TSLA")
        assert r1.sentiment_score == r2.sentiment_score
        assert r1.mention_count == r2.mention_count
        assert r1.sample_posts == r2.sample_posts

    def test_sentiment_clamped(self):
        # Any ticker should produce a score in [-1, 1]
        for t in ("A", "ZZZZ", "BTC", "LONGTICKER"):
            r = mock_backend(t)
            assert -1.0 <= r.sentiment_score <= 1.0

    def test_mention_count_positive(self):
        r = mock_backend("NVDA")
        assert r.mention_count >= 0

    def test_sample_posts_present(self):
        r = mock_backend("META")
        assert len(r.sample_posts) == 2
        assert all(r.ticker in post for post in r.sample_posts)


class TestXurlBackend:
    def test_returns_none_when_xurl_missing(self, monkeypatch):
        monkeypatch.setattr("analysis.sentiment.sentiment_scraper.shutil.which", lambda _: None)
        assert xurl_backend("AAPL") is None

    def test_parses_json_posts(self, monkeypatch):
        fake_posts = [
            {"text": "Bullish on $AAPL, buying long!"},
            {"text": "Bearish dump sell short"},
        ]

        class FakeProc:
            stdout = str(__import__("json").dumps(fake_posts))
            stderr = ""
            returncode = 0

        monkeypatch.setattr(
            "analysis.sentiment.sentiment_scraper.shutil.which", lambda _: "/usr/bin/xurl"
        )
        monkeypatch.setattr(
            "analysis.sentiment.sentiment_scraper.subprocess.run", lambda *a, **k: FakeProc()
        )

        r = xurl_backend("AAPL")
        assert r is not None
        assert r.ticker == "AAPL"
        assert r.source == "xurl"
        assert r.mention_count == 2
        assert -1.0 <= r.sentiment_score <= 1.0

    def test_returns_none_on_subprocess_error(self, monkeypatch):
        monkeypatch.setattr("analysis.sentiment.sentiment_scraper.shutil.which", lambda _: "/usr/bin/xurl")
        monkeypatch.setattr(
            "analysis.sentiment.sentiment_scraper.subprocess.run",
            lambda *a, **k: (_ for _ in ()).throw(__import__("subprocess").CalledProcessError(1, "xurl")),
        )
        assert xurl_backend("AAPL") is None


class TestWebBackend:
    def test_returns_none_placeholder(self):
        assert web_backend("AAPL") is None


class TestScrapeSentiment:
    def test_mock_source(self):
        r = scrape_sentiment("GOOGL", source="mock")
        assert r.source == "mock"
        assert r.ticker == "GOOGL"

    def test_auto_falls_back_to_mock(self, monkeypatch):
        monkeypatch.setattr("analysis.sentiment.sentiment_scraper.shutil.which", lambda _: None)
        r = scrape_sentiment("MSFT", source="auto")
        assert r.source == "mock"

    def test_auto_uses_xurl_when_available(self, monkeypatch):
        fake_posts = [{"text": "Rocket to the moon!"}]

        class FakeProc:
            stdout = str(__import__("json").dumps(fake_posts))
            stderr = ""
            returncode = 0

        monkeypatch.setattr("analysis.sentiment.sentiment_scraper.shutil.which", lambda _: "/usr/bin/xurl")
        monkeypatch.setattr("analysis.sentiment.sentiment_scraper.subprocess.run", lambda *a, **k: FakeProc())

        r = scrape_sentiment("AMD", source="auto")
        assert r.source == "xurl"

    def test_unknown_source_raises(self):
        with pytest.raises(ValueError, match="Unknown source"):
            scrape_sentiment("IBM", source="unknown")

    def test_web_source_raises_when_none(self):
        with pytest.raises(RuntimeError, match="Backend 'web' returned no data"):
            scrape_sentiment("IBM", source="web")


class TestScrapeSentimentBatch:
    def test_batch_mock(self):
        tickers = ["AAPL", "TSLA", "NVDA"]
        results = scrape_sentiment_batch(tickers, source="mock")
        assert set(results.keys()) == set(tickers)
        for t, r in results.items():
            assert r.ticker == t
            assert r.source == "mock"

    def test_batch_graceful_failure(self, monkeypatch):
        # Force auto to fail everything except we intercept mock to also fail
        # Instead, just break xurl/web and let mock succeed
        monkeypatch.setattr("analysis.sentiment.sentiment_scraper.shutil.which", lambda _: None)
        results = scrape_sentiment_batch(["BAD"], source="auto")
        assert "BAD" in results
        assert results["BAD"].source == "mock"  # falls back to mock

    def test_batch_empty_list(self):
        assert scrape_sentiment_batch([], source="mock") == {}

    def test_batch_preserves_order(self):
        tickers = ["Z", "A", "M"]
        results = scrape_sentiment_batch(tickers, source="mock")
        assert list(results.keys()) == ["Z", "A", "M"]


class TestSentimentResultDataclass:
    def test_clamping(self):
        r = SentimentResult("X", "test", 2.5, 5)
        assert r.sentiment_score == 1.0

        r2 = SentimentResult("X", "test", -99.0, 5)
        assert r2.sentiment_score == -1.0

    def test_default_timestamp(self):
        r = SentimentResult("X", "test", 0.0, 0)
        assert r.timestamp is not None
        assert isinstance(r.timestamp, str)

    def test_mention_count_int(self):
        r = SentimentResult("X", "test", 0.0, 42)
        assert r.mention_count == 42
        assert isinstance(r.mention_count, int)
