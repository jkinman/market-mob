"""Tests for basket analyzer module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np
import pytest

from analysis.technical.fetch_prices import PriceData
from analysis.sector.basket_analyzer import (
    StockScore,
    SectorAnalysis,
    _score_stock,
    analyze_sector,
)


class TestScoreStock:
    """Unit tests for _score_stock helper."""

    def test_score_stock_baseline(self):
        """Baseline stock should get reasonable scores."""
        summary = {
            "price": 100.0,
            "price_change_1d": 0.0,
            "rsi_14": 50.0,
            "sma_20": 100.0,
            "sma_50": 100.0,
            "macd": 0.0,
            "macd_signal": 0.0,
        }
        score = _score_stock(summary, "FAKE")
        assert isinstance(score, StockScore)
        assert score.ticker == "FAKE"
        assert 0 <= score.momentum_score <= 100
        assert 0 <= score.risk_score <= 100

    def test_score_stock_bullish(self):
        """Bullish stock should have high momentum score."""
        summary = {
            "price": 120.0,
            "price_change_1d": 3.0,
            "rsi_14": 55.0,
            "sma_20": 110.0,
            "sma_50": 105.0,
            "macd": 1.0,
            "macd_signal": 0.5,
        }
        score = _score_stock(summary, "BULL")
        assert score.above_sma_20 is True
        assert score.above_sma_50 is True
        assert score.macd_bullish is True
        assert score.momentum_score > 70

    def test_score_stock_bearish(self):
        """Bearish stock should have lower momentum score and higher risk."""
        summary = {
            "price": 80.0,
            "price_change_1d": -4.0,
            "rsi_14": 25.0,
            "sma_20": 90.0,
            "sma_50": 100.0,
            "macd": -1.0,
            "macd_signal": -0.5,
        }
        score = _score_stock(summary, "BEAR")
        assert score.above_sma_20 is False
        assert score.above_sma_50 is False
        assert score.macd_bullish is False
        assert score.risk_score > 50


class TestAnalyzeSector:
    """Unit tests for analyze_sector."""

    def _make_price_data(self, ticker: str, prices: list[float]) -> PriceData:
        """Helper to create PriceData with realistic columns."""
        dates = pd.date_range("2024-01-01", periods=len(prices), freq="D")
        df = pd.DataFrame({
            "Open": [p - 1 for p in prices],
            "High": [p + 2 for p in prices],
            "Low": [p - 2 for p in prices],
            "Close": prices,
            "Volume": [1_000_000 + i * 10_000 for i in range(len(prices))],
        }, index=dates)
        return PriceData(ticker=ticker, df=df, period="30d", interval="1d")

    @patch("analysis.sector.basket_analyzer.fetch_multi")
    def test_analyze_sector_success(self, mock_fetch_multi):
        """Successful analysis should return SectorAnalysis with metrics."""
        np.random.seed(42)
        mock_data = {
            "AAPL": self._make_price_data("AAPL", list(100 + np.cumsum(np.random.randn(30) * 2))),
            "MSFT": self._make_price_data("MSFT", list(200 + np.cumsum(np.random.randn(30) * 2))),
        }
        mock_fetch_multi.return_value = mock_data

        result = analyze_sector("tech", ["AAPL", "MSFT"])

        assert isinstance(result, SectorAnalysis)
        assert result.sector_name == "tech"
        assert len(result.tickers_analyzed) == 2
        assert result.tickers_failed == []
        assert result.avg_rsi > 0
        assert 0 <= result.pct_above_sma20 <= 100
        assert result.top_momentum is not None
        assert result.worst_performer is not None
        assert len(result.ranked_stocks) == 2
        assert result.ranked_stocks[0].opportunity_rank == 1

    @patch("analysis.sector.basket_analyzer.fetch_multi")
    def test_analyze_sector_with_failure(self, mock_fetch_multi):
        """Failed fetches should be tracked in tickers_failed."""
        mock_data = {
            "AAPL": self._make_price_data("AAPL", list(100 + np.cumsum(np.random.randn(30) * 2))),
            "FAKE": None,
        }
        mock_fetch_multi.return_value = mock_data

        result = analyze_sector("test", ["AAPL", "FAKE"])

        assert "FAKE" in result.tickers_failed
        assert "AAPL" in result.tickers_analyzed

    @patch("analysis.sector.basket_analyzer.fetch_multi")
    def test_analyze_sector_empty_data(self, mock_fetch_multi):
        """Empty dataframe should be treated as failure."""
        empty_df = pd.DataFrame({"Open": [], "High": [], "Low": [], "Close": [], "Volume": []})
        empty_pdata = PriceData(ticker="EMPTY", df=empty_df, period="30d", interval="1d")
        mock_data = {"EMPTY": empty_pdata}
        mock_fetch_multi.return_value = mock_data

        result = analyze_sector("test", ["EMPTY"])

        assert "EMPTY" in result.tickers_failed
        assert result.tickers_analyzed == []

    @patch("analysis.sector.basket_analyzer.fetch_multi")
    def test_analyze_sector_suspicious_moves(self, mock_fetch_multi):
        """Large moves should be flagged as suspicious."""
        prices = [100.0] * 29 + [115.0]  # 15% move on last day
        mock_data = {
            "VOLA": self._make_price_data("VOLA", prices),
        }
        mock_fetch_multi.return_value = mock_data

        result = analyze_sector("test", ["VOLA"], suspicious_threshold=10.0)

        assert len(result.suspicious_moves) == 1
        assert result.suspicious_moves[0].ticker == "VOLA"

    @patch("analysis.sector.basket_analyzer.fetch_multi")
    def test_analyze_sector_all_fail(self, mock_fetch_multi):
        """If all tickers fail, return empty analysis."""
        mock_fetch_multi.return_value = {"A": None, "B": None}

        result = analyze_sector("test", ["A", "B"])

        assert result.tickers_analyzed == []
        assert set(result.tickers_failed) == {"A", "B"}
        assert result.top_momentum is None
