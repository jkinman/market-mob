"""End-to-end test: fetch prices → indicators → analysis → report."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analysis.technical.fetch_prices import fetch_prices
from analysis.technical.indicators import compute_all, summarize_latest
from agents.analyst.llm_analyst import analyze_stock, AnalysisResult
from output.obsidian.report_formatter import format_daily_report, save_report


class TestEndToEnd:
    """End-to-end integration test with mocked external APIs."""

    @patch("analysis.technical.fetch_prices.yf.Ticker")
    def test_full_pipeline(self, mock_ticker_class, tmp_path):
        """Test complete pipeline from price fetch to markdown report."""
        # Arrange: Mock yfinance data
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        np.random.seed(42)
        prices = 100 + pd.Series(range(60)) * 0.5 + pd.Series(np.random.randn(60) * 2)

        mock_history = pd.DataFrame({
            "Open": prices - 1,
            "High": prices + 2,
            "Low": prices - 2,
            "Close": prices,
            "Volume": [1000000 + i * 1000 for i in range(60)],
        }, index=dates)

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history
        mock_ticker_class.return_value = mock_ticker

        # Step 1: Fetch prices
        price_data = fetch_prices("AAPL", period="60d")
        assert price_data is not None
        assert price_data.ticker == "AAPL"

        # Step 2: Compute indicators
        df_with_indicators = compute_all(price_data.df)
        assert "RSI_14" in df_with_indicators.columns
        assert "MACD" in df_with_indicators.columns

        # Step 3: Summarize for LLM
        indicators_summary = summarize_latest(df_with_indicators)
        assert "price" in indicators_summary
        assert "rsi_14" in indicators_summary

        # Step 4: Mock LLM analysis
        mock_response = '''{
            "trend": "bullish",
            "support_level": 115.0,
            "resistance_level": 135.0,
            "prediction_7d": "up 3%",
            "prediction_30d": "up 8%",
            "confidence": "medium",
            "risk_level": "medium",
            "reasoning": "Price above both SMAs, MACD turning positive. RSI neutral at 55."
        }'''

        def mock_llm(prompt: str) -> str:
            return mock_response

        analysis = analyze_stock("AAPL", {}, indicators_summary, llm_caller=mock_llm)
        assert analysis is not None
        assert analysis.trend == "bullish"

        # Step 5: Format report
        report = format_daily_report("AAPL", {}, indicators_summary, analysis)
        assert "AAPL" in report
        assert "bullish" in report
        assert "RSI" in report
        assert "Not financial advice" in report

        # Step 6: Save report
        output_dir = str(tmp_path / "reports")
        filepath = save_report("AAPL", report, output_dir=output_dir)
        assert filepath.endswith("--aapl.md")

        with open(filepath, "r") as f:
            saved_content = f.read()
        assert saved_content == report

    @patch("analysis.technical.fetch_prices.yf.Ticker")
    def test_pipeline_with_failed_fetch(self, mock_ticker_class):
        """Pipeline should handle fetch failure gracefully."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_class.return_value = mock_ticker

        price_data = fetch_prices("FAKE")
        assert price_data is None

    def test_report_formatting(self):
        """Report formatter should produce valid markdown."""
        analysis = AnalysisResult(
            ticker="TSLA",
            trend="bearish",
            support_level=200.0,
            resistance_level=250.0,
            prediction_7d="down 5%",
            prediction_30d="down 15%",
            confidence="high",
            risk_level="high",
            reasoning="RSI overbought, negative MACD divergence.",
            raw_response="",
        )

        indicators = {
            "price": 230.0,
            "price_change_1d": -5.0,
            "volume": 75000000,
            "rsi_14": 72.5,
            "macd": -0.5,
            "macd_signal": 0.2,
            "macd_histogram": -0.7,
            "sma_20": 240.0,
            "sma_50": 235.0,
            "bb_upper": 260.0,
            "bb_lower": 220.0,
        }

        report = format_daily_report("TSLA", {}, indicators, analysis, source="youtube")

        assert "TSLA" in report
        assert "bearish" in report
        assert "youtube" in report
        assert "| RSI (14) | 72.5 |" in report
        assert "$200.0" in report  # support level
        assert "[[Stock Watchlist]]" in report


# Need numpy for the test
import numpy as np
