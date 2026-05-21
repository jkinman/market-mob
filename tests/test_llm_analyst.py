"""Tests for LLM analyst agent."""

import pytest

from agents.analyst.llm_analyst import (
    build_prompt,
    parse_analysis_response,
    analyze_stock,
    AnalysisResult,
)


class TestBuildPrompt:
    """Tests for prompt building."""

    def test_prompt_contains_ticker(self):
        """Prompt should mention the ticker."""
        indicators = {
            "price": 150.0,
            "price_change_1d": 2.5,
            "volume": 50000000,
            "rsi_14": 55.5,
            "macd": 0.5,
            "macd_signal": 0.3,
            "macd_histogram": 0.2,
            "sma_20": 148.0,
            "sma_50": 145.0,
            "bb_upper": 155.0,
            "bb_lower": 142.0,
        }
        prompt = build_prompt("AAPL", {}, indicators)
        assert "AAPL" in prompt

    def test_prompt_contains_price_data(self):
        """Prompt should include price and indicators."""
        indicators = {
            "price": 150.0,
            "price_change_1d": 2.5,
            "volume": 50000000,
            "rsi_14": 55.5,
            "macd": 0.5,
            "macd_signal": 0.3,
            "macd_histogram": 0.2,
            "sma_20": 148.0,
            "sma_50": 145.0,
            "bb_upper": 155.0,
            "bb_lower": 142.0,
        }
        prompt = build_prompt("TSLA", {}, indicators)
        assert "$150.0" in prompt or "150.0" in prompt
        assert "RSI" in prompt
        assert "MACD" in prompt

    def test_prompt_requests_json(self):
        """Prompt should ask for JSON output."""
        indicators = {
            "price": 300.0,
            "price_change_1d": 1.0,
            "volume": 1000000,
            "rsi_14": 50.0,
            "macd": 0.1,
            "macd_signal": 0.0,
            "macd_histogram": 0.1,
            "sma_20": 298.0,
            "sma_50": 295.0,
            "bb_upper": 305.0,
            "bb_lower": 292.0,
        }
        prompt = build_prompt("META", {}, indicators)
        assert "JSON" in prompt


class TestParseAnalysisResponse:
    """Tests for response parsing."""

    def test_parse_valid_json(self):
        """Should parse valid JSON response."""
        response = '''{
            "trend": "bullish",
            "support_level": 145.0,
            "resistance_level": 155.0,
            "prediction_7d": "up 3%",
            "prediction_30d": "up 8%",
            "confidence": "medium",
            "risk_level": "medium",
            "reasoning": "Price above SMAs, MACD positive."
        }'''

        result = parse_analysis_response(response, "AAPL")

        assert result is not None
        assert result.ticker == "AAPL"
        assert result.trend == "bullish"
        assert result.support_level == 145.0
        assert result.confidence == "medium"
        assert "Price above SMAs" in result.reasoning

    def test_parse_json_in_code_block(self):
        """Should handle markdown code blocks."""
        response = '''```json
        {
            "trend": "bearish",
            "support_level": 100.0,
            "resistance_level": 110.0,
            "prediction_7d": "down 5%",
            "prediction_30d": "down 10%",
            "confidence": "high",
            "risk_level": "high",
            "reasoning": "RSI overbought."
        }
        ```'''

        result = parse_analysis_response(response, "TSLA")

        assert result is not None
        assert result.trend == "bearish"
        assert result.confidence == "high"

    def test_parse_invalid_json(self):
        """Should return None for invalid JSON."""
        result = parse_analysis_response("not json", "AAPL")
        assert result is None

    def test_parse_missing_fields(self):
        """Should handle missing fields gracefully."""
        response = '{"trend": "sideways"}'
        result = parse_analysis_response(response, "META")

        assert result is not None
        assert result.trend == "sideways"
        assert result.confidence == "low"  # default
        assert result.reasoning == ""  # default


class TestAnalyzeStock:
    """Tests for end-to-end analysis."""

    def test_analyze_with_mock_llm(self):
        """Should use custom LLM caller and return result."""
        mock_response = '''{
            "trend": "bullish",
            "support_level": 140.0,
            "resistance_level": 160.0,
            "prediction_7d": "up 2%",
            "prediction_30d": "up 5%",
            "confidence": "medium",
            "risk_level": "low",
            "reasoning": "Good momentum."
        }'''

        def mock_caller(prompt: str) -> str:
            return mock_response

        indicators = {
            "price": 150.0,
            "price_change_1d": 1.0,
            "volume": 1000000,
            "rsi_14": 50.0,
            "macd": 0.1,
            "macd_signal": 0.0,
            "macd_histogram": 0.1,
            "sma_20": 148.0,
            "sma_50": 145.0,
            "bb_upper": 155.0,
            "bb_lower": 142.0,
        }

        result = analyze_stock("AAPL", {}, indicators, llm_caller=mock_caller)

        assert result is not None
        assert result.ticker == "AAPL"
        assert result.trend == "bullish"

    def test_analyze_with_failing_llm(self):
        """Should return None if LLM fails."""
        def failing_caller(prompt: str) -> str:
            raise Exception("LLM timeout")

        indicators = {
            "price": 150.0,
            "price_change_1d": 1.0,
            "volume": 1000000,
            "rsi_14": 50.0,
            "macd": 0.1,
            "macd_signal": 0.0,
            "macd_histogram": 0.1,
            "sma_20": 148.0,
            "sma_50": 145.0,
            "bb_upper": 155.0,
            "bb_lower": 142.0,
        }

        result = analyze_stock("AAPL", {}, indicators, llm_caller=failing_caller)

        assert result is None

    def test_analyze_prompt_passed_to_llm(self):
        """Should build prompt and pass to LLM caller."""
        captured_prompt = None

        def capturing_caller(prompt: str) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return '{"trend": "bullish", "support_level": 100, "resistance_level": 110, "prediction_7d": "up", "prediction_30d": "up", "confidence": "high", "risk_level": "low", "reasoning": "test"}'

        indicators = {
            "price": 150.0,
            "price_change_1d": 1.0,
            "volume": 1000000,
            "rsi_14": 50.0,
            "macd": 0.1,
            "macd_signal": 0.0,
            "macd_histogram": 0.1,
            "sma_20": 148.0,
            "sma_50": 145.0,
            "bb_upper": 155.0,
            "bb_lower": 142.0,
        }

        analyze_stock("NVDA", {}, indicators, llm_caller=capturing_caller)

        assert captured_prompt is not None
        assert "NVDA" in captured_prompt
        assert "RSI" in captured_prompt
