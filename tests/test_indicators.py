"""Tests for technical indicators module."""

import numpy as np
import pandas as pd
import pytest

from analysis.technical.indicators import (
    rsi,
    macd,
    moving_average,
    bollinger_bands,
    compute_all,
    summarize_latest,
)


class TestRSI:
    """Tests for RSI calculation."""

    def test_rsi_range(self, sample_price_data):
        """RSI should be between 0 and 100."""
        result = rsi(sample_price_data["Close"])
        assert result.min() >= 0
        assert result.max() <= 100

    def test_rsi_nan_initial_values(self, sample_price_data):
        """First 13 values should be NaN (need 14 periods)."""
        result = rsi(sample_price_data["Close"])
        assert result.iloc[:13].isna().all()
        assert not result.iloc[14:].isna().any()

    def test_rsi_strong_uptrend(self):
        """Strong uptrend should give high RSI."""
        prices = pd.Series(range(100, 200))  # Straight up
        result = rsi(prices)
        assert result.iloc[-1] > 70

    def test_rsi_strong_downtrend(self):
        """Strong downtrend should give low RSI."""
        prices = pd.Series(range(200, 100, -1))  # Straight down
        result = rsi(prices)
        assert result.iloc[-1] < 30


class TestMACD:
    """Tests for MACD calculation."""

    def test_macd_structure(self, sample_price_data):
        """MACD should return three series."""
        result = macd(sample_price_data["Close"])
        assert "macd_line" in result
        assert "signal_line" in result
        assert "histogram" in result

    def test_macd_histogram(self, sample_price_data):
        """Histogram = MACD line - signal line."""
        result = macd(sample_price_data["Close"])
        expected = result["macd_line"] - result["signal_line"]
        pd.testing.assert_series_equal(result["histogram"], expected)


class TestMovingAverage:
    """Tests for SMA."""

    def test_sma_length(self, sample_price_data):
        """First N-1 values should be NaN for N-period SMA."""
        result = moving_average(sample_price_data["Close"], 20)
        assert result.iloc[:19].isna().all()
        assert not result.iloc[20:].isna().any()

    def test_sma_simple_case(self):
        """SMA of [1,2,3,4,5] with period 3 = [NaN, NaN, 2, 3, 4]."""
        prices = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = moving_average(prices, 3)
        expected = pd.Series([np.nan, np.nan, 2.0, 3.0, 4.0])
        pd.testing.assert_series_equal(result, expected)


class TestBollingerBands:
    """Tests for Bollinger Bands."""

    def test_bb_structure(self, sample_price_data):
        """BB should return upper, middle, lower."""
        result = bollinger_bands(sample_price_data["Close"])
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result

    def test_bb_order(self, sample_price_data):
        """Upper >= Middle >= Lower (after warmup period)."""
        result = bollinger_bands(sample_price_data["Close"])
        # Skip first 20 days where SMA is NaN
        valid_idx = result["middle"].notna()
        assert (result["upper"][valid_idx] >= result["middle"][valid_idx]).all()
        assert (result["middle"][valid_idx] >= result["lower"][valid_idx]).all()


class TestComputeAll:
    """Tests for compute_all wrapper."""

    def test_compute_all_columns(self, sample_price_data):
        """Should add indicator columns."""
        result = compute_all(sample_price_data)
        expected_cols = [
            "RSI_14", "MACD", "MACD_Signal", "MACD_Histogram",
            "SMA_20", "SMA_50", "BB_Upper", "BB_Lower", "BB_Middle",
        ]
        for col in expected_cols:
            assert col in result.columns

    def test_compute_all_no_close_column(self):
        """Should raise error if no Close column."""
        df = pd.DataFrame({"Open": [1, 2, 3]})
        with pytest.raises(ValueError, match="Close"):
            compute_all(df)


class TestSummarizeLatest:
    """Tests for summary function."""

    def test_summary_structure(self, sample_price_data):
        """Summary should have expected keys."""
        df = compute_all(sample_price_data)
        summary = summarize_latest(df)
        expected_keys = [
            "price", "price_change_1d", "rsi_14", "macd",
            "macd_signal", "macd_histogram", "sma_20", "sma_50",
            "bb_upper", "bb_lower", "volume",
        ]
        for key in expected_keys:
            assert key in summary

    def test_summary_types(self, sample_price_data):
        """Summary values should be numeric."""
        df = compute_all(sample_price_data)
        summary = summarize_latest(df)
        assert isinstance(summary["price"], float)
        assert isinstance(summary["rsi_14"], float)
        assert isinstance(summary["volume"], int)
