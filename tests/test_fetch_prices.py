"""Tests for fetch_prices module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analysis.technical.fetch_prices import fetch_prices, fetch_multi


class TestFetchPrices:
    """Unit tests for price fetching."""

    @patch("analysis.technical.fetch_prices.yf.Ticker")
    def test_fetch_success(self, mock_ticker_class):
        """Test successful price fetch returns PriceData."""
        # Arrange
        mock_ticker = MagicMock()
        mock_history = pd.DataFrame({
            "Open": [100, 101, 102],
            "High": [101, 102, 103],
            "Low": [99, 100, 101],
            "Close": [100.5, 101.5, 102.5],
            "Volume": [1000000, 1100000, 1200000],
        }, index=pd.date_range("2024-01-01", periods=3, freq="D"))
        mock_ticker.history.return_value = mock_history
        mock_ticker_class.return_value = mock_ticker

        # Act
        result = fetch_prices("AAPL", period="3d")

        # Assert
        assert result is not None
        assert result.ticker == "AAPL"
        assert result.latest_close == 102.5
        assert result.latest_volume == 1200000
        assert result.days_of_data == 3
        mock_ticker.history.assert_called_once_with(period="3d", interval="1d")

    @patch("analysis.technical.fetch_prices.yf.Ticker")
    def test_fetch_empty_data(self, mock_ticker_class):
        """Test empty DataFrame returns None."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_class.return_value = mock_ticker

        result = fetch_prices("FAKE")

        assert result is None

    @patch("analysis.technical.fetch_prices.yf.Ticker")
    def test_fetch_exception(self, mock_ticker_class):
        """Test exception handling returns None."""
        mock_ticker_class.side_effect = Exception("Network error")

        result = fetch_prices("AAPL")

        assert result is None

    @patch("analysis.technical.fetch_prices.yf.Ticker")
    def test_fetch_multi(self, mock_ticker_class):
        """Test fetching multiple tickers."""
        mock_ticker = MagicMock()
        mock_history = pd.DataFrame({
            "Open": [100],
            "High": [101],
            "Low": [99],
            "Close": [100.5],
            "Volume": [1000000],
        }, index=pd.date_range("2024-01-01", periods=1))
        mock_ticker.history.return_value = mock_history
        mock_ticker_class.return_value = mock_ticker

        results = fetch_multi(["AAPL", "MSFT"])

        assert len(results) == 2
        assert results["AAPL"] is not None
        assert results["MSFT"] is not None
        assert results["AAPL"].ticker == "AAPL"

    @patch("analysis.technical.fetch_prices.yf.Ticker")
    def test_ticker_uppercase(self, mock_ticker_class):
        """Test ticker is normalized to uppercase."""
        mock_ticker = MagicMock()
        mock_history = pd.DataFrame({
            "Open": [100],
            "High": [101],
            "Low": [99],
            "Close": [100.5],
            "Volume": [1000000],
        }, index=pd.date_range("2024-01-01", periods=1))
        mock_ticker.history.return_value = mock_history
        mock_ticker_class.return_value = mock_ticker

        result = fetch_prices("aapl")

        assert result.ticker == "AAPL"
