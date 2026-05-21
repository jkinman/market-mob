"""Tests for LLM analyst agent."""

import pytest

from agents.analyst.llm_analyst import (
    build_prompt,
    build_overview_prompt,
    build_alpha_prompt,
    parse_analysis_response,
    parse_overview_response,
    parse_alpha_response,
    analyze_stock,
    analyze_overview,
    analyze_alpha,
    AnalysisResult,
    OverviewResult,
    AlphaResult,
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


class TestBuildOverviewPrompt:
    """Tests for overview prompt building."""

    def test_overview_prompt_contains_tickers(self):
        """Overview prompt should list all tickers."""
        data = {
            "AAPL": {"price": 150.0, "price_change_1d": 2.5, "volume": 50000000, "rsi_14": 55.5, "macd": 0.5, "sma_20": 148.0, "sma_50": 145.0},
            "TSLA": {"price": 200.0, "price_change_1d": -1.0, "volume": 30000000, "rsi_14": 45.0, "macd": -0.2, "sma_20": 202.0, "sma_50": 205.0},
        }
        prompt = build_overview_prompt(data)
        assert "AAPL" in prompt
        assert "TSLA" in prompt
        assert "macro strategist" in prompt.lower()

    def test_overview_prompt_requests_json(self):
        """Overview prompt should request JSON output."""
        prompt = build_overview_prompt({"AAPL": {"price": 150.0}})
        assert "JSON" in prompt
        assert "market_sentiment" in prompt


class TestBuildAlphaPrompt:
    """Tests for alpha prompt building."""

    def test_alpha_prompt_contains_tickers(self):
        """Alpha prompt should list tickers."""
        data = {"NVDA": {"price": 400.0, "price_change_1d": 5.0, "volume": 100000000, "rsi_14": 65.0, "macd": 1.2}}
        prompt = build_alpha_prompt(data, [])
        assert "NVDA" in prompt
        assert "alpha hunter" in prompt.lower()

    def test_alpha_prompt_with_suspicious_moves(self):
        """Alpha prompt should include suspicious moves."""
        data = {"CDLX": {"price": 10.0, "price_change_1d": 12.0, "volume": 5000000, "rsi_14": 70.0, "macd": 0.3}}
        moves = [
            {"ticker": "CDLX", "move_pct": 12.5, "direction": "up", "volume_vs_avg": 3.5, "flagged_reason": "No news"}
        ]
        prompt = build_alpha_prompt(data, moves)
        assert "CDLX" in prompt
        assert "12.5%" in prompt
        assert "suspicious" in prompt.lower()

    def test_alpha_prompt_with_dataclass_moves(self):
        """Alpha prompt should handle dataclass-like suspicious moves."""
        from analysis.technical.suspicious_moves import SuspiciousMove
        data = {"CDLX": {"price": 10.0, "price_change_1d": 12.0, "volume": 5000000, "rsi_14": 70.0, "macd": 0.3}}
        move = SuspiciousMove(ticker="CDLX", move_pct=12.5, direction="up", volume_vs_avg=3.5, flagged_reason="No news")
        prompt = build_alpha_prompt(data, [move])
        assert "CDLX" in prompt
        assert "12.5%" in prompt

    def test_alpha_prompt_requests_json(self):
        """Alpha prompt should request JSON output."""
        prompt = build_alpha_prompt({"AAPL": {"price": 150.0}}, [])
        assert "JSON" in prompt
        assert "volatile_tickers" in prompt


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


class TestParseOverviewResponse:
    """Tests for overview response parsing."""

    def test_parse_valid_overview(self):
        """Should parse valid overview JSON."""
        response = '''{
            "market_sentiment": "bullish",
            "sector_trends": {"tech": "strong", "energy": "weak"},
            "watchlist_health": "healthy",
            "breadth_summary": "8 advancers, 2 decliners, avg RSI 55",
            "top_opportunities": ["AAPL: breakout above SMAs", "NVDA: momentum continuation"],
            "top_risks": ["TSLA: overbought RSI"],
            "reasoning": "Tech leading, breadth strong."
        }'''

        result = parse_overview_response(response)

        assert result is not None
        assert isinstance(result, OverviewResult)
        assert result.market_sentiment == "bullish"
        assert result.sector_trends == {"tech": "strong", "energy": "weak"}
        assert result.watchlist_health == "healthy"
        assert len(result.top_opportunities) == 2
        assert len(result.top_risks) == 1
        assert "Tech leading" in result.reasoning

    def test_parse_overview_missing_fields(self):
        """Should handle missing fields with defaults."""
        response = '{"market_sentiment": "neutral"}'
        result = parse_overview_response(response)

        assert result is not None
        assert result.market_sentiment == "neutral"
        assert result.sector_trends == {}
        assert result.top_opportunities == []
        assert result.top_risks == []

    def test_parse_overview_invalid_json(self):
        """Should return None for invalid JSON."""
        result = parse_overview_response("not json")
        assert result is None


class TestParseAlphaResponse:
    """Tests for alpha response parsing."""

    def test_parse_valid_alpha(self):
        """Should parse valid alpha JSON."""
        response = '''{
            "volatile_tickers": ["CDLX", "MSTR"],
            "suspicious_moves": [{"ticker": "CDLX", "move_pct": 12.5, "direction": "up", "notes": "No catalyst"}],
            "opportunity_setups": [{"ticker": "AAPL", "setup": "breakout", "notes": "Above resistance"}],
            "contrarian_signals": [{"ticker": "TSLA", "signal": "oversold_bounce", "notes": "RSI 28"}],
            "insider_signals": ["MSTR: unusual volume pre-move"],
            "reasoning": "Crypto sympathy driving volatility."
        }'''

        result = parse_alpha_response(response)

        assert result is not None
        assert isinstance(result, AlphaResult)
        assert "CDLX" in result.volatile_tickers
        assert len(result.suspicious_moves) == 1
        assert len(result.opportunity_setups) == 1
        assert len(result.contrarian_signals) == 1
        assert len(result.insider_signals) == 1
        assert "Crypto sympathy" in result.reasoning

    def test_parse_alpha_missing_fields(self):
        """Should handle missing fields with defaults."""
        response = '{"volatile_tickers": ["AAPL"]}'
        result = parse_alpha_response(response)

        assert result is not None
        assert result.volatile_tickers == ["AAPL"]
        assert result.suspicious_moves == []
        assert result.opportunity_setups == []
        assert result.contrarian_signals == []
        assert result.insider_signals == []

    def test_parse_alpha_invalid_json(self):
        """Should return None for invalid JSON."""
        result = parse_alpha_response("not json")
        assert result is None


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


class TestAnalyzeOverview:
    """Tests for overview analysis end-to-end."""

    def test_analyze_overview_with_mock_llm(self):
        """Should use custom LLM caller and return OverviewResult."""
        mock_response = '''{
            "market_sentiment": "bullish",
            "sector_trends": {"tech": "strong"},
            "watchlist_health": "healthy",
            "breadth_summary": "5 up, 1 down",
            "top_opportunities": ["AAPL: momentum"],
            "top_risks": ["TSLA: overbought"],
            "reasoning": "Broad strength."
        }'''

        def mock_caller(prompt: str) -> str:
            return mock_response

        data = {
            "AAPL": {"price": 150.0, "price_change_1d": 2.5, "volume": 50000000, "rsi_14": 55.5, "macd": 0.5, "sma_20": 148.0, "sma_50": 145.0},
            "TSLA": {"price": 200.0, "price_change_1d": -1.0, "volume": 30000000, "rsi_14": 75.0, "macd": -0.2, "sma_20": 202.0, "sma_50": 205.0},
        }

        result = analyze_overview(data, llm_caller=mock_caller)

        assert result is not None
        assert isinstance(result, OverviewResult)
        assert result.market_sentiment == "bullish"
        assert result.watchlist_health == "healthy"

    def test_analyze_overview_empty_data(self):
        """Should return None for empty ticker data."""
        result = analyze_overview({})
        assert result is None

    def test_analyze_overview_failing_llm(self):
        """Should return None if LLM fails."""
        def failing_caller(prompt: str) -> str:
            raise Exception("LLM timeout")

        data = {"AAPL": {"price": 150.0}}
        result = analyze_overview(data, llm_caller=failing_caller)
        assert result is None

    def test_analyze_overview_prompt_passed_to_llm(self):
        """Should build overview prompt and pass to LLM caller."""
        captured_prompt = None

        def capturing_caller(prompt: str) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return '{"market_sentiment": "neutral", "sector_trends": {}, "watchlist_health": "mixed", "breadth_summary": "", "top_opportunities": [], "top_risks": [], "reasoning": "test"}'

        data = {"AAPL": {"price": 150.0, "price_change_1d": 2.5, "volume": 50000000, "rsi_14": 55.5, "macd": 0.5, "sma_20": 148.0, "sma_50": 145.0}}
        analyze_overview(data, llm_caller=capturing_caller)

        assert captured_prompt is not None
        assert "AAPL" in captured_prompt
        assert "macro strategist" in captured_prompt.lower()


class TestAnalyzeAlpha:
    """Tests for alpha analysis end-to-end."""

    def test_analyze_alpha_with_mock_llm(self):
        """Should use custom LLM caller and return AlphaResult."""
        mock_response = '''{
            "volatile_tickers": ["MSTR"],
            "suspicious_moves": [{"ticker": "MSTR", "move_pct": 15.0, "direction": "up", "notes": "No news"}],
            "opportunity_setups": [{"ticker": "AAPL", "setup": "breakout", "notes": "Above SMAs"}],
            "contrarian_signals": [],
            "insider_signals": [],
            "reasoning": "Crypto sympathy."
        }'''

        def mock_caller(prompt: str) -> str:
            return mock_response

        data = {"AAPL": {"price": 150.0, "price_change_1d": 2.5, "volume": 50000000, "rsi_14": 55.5, "macd": 0.5}}
        moves = [{"ticker": "MSTR", "move_pct": 15.0, "direction": "up", "volume_vs_avg": 4.0, "flagged_reason": "No news"}]

        result = analyze_alpha(data, moves, llm_caller=mock_caller)

        assert result is not None
        assert isinstance(result, AlphaResult)
        assert "MSTR" in result.volatile_tickers
        assert len(result.suspicious_moves) == 1

    def test_analyze_alpha_empty_data(self):
        """Should return None for empty ticker data."""
        result = analyze_alpha({}, [])
        assert result is None

    def test_analyze_alpha_failing_llm(self):
        """Should return None if LLM fails."""
        def failing_caller(prompt: str) -> str:
            raise Exception("LLM timeout")

        data = {"AAPL": {"price": 150.0}}
        result = analyze_alpha(data, [], llm_caller=failing_caller)
        assert result is None

    def test_analyze_alpha_prompt_passed_to_llm(self):
        """Should build alpha prompt and pass to LLM caller."""
        captured_prompt = None

        def capturing_caller(prompt: str) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return '{"volatile_tickers": [], "suspicious_moves": [], "opportunity_setups": [], "contrarian_signals": [], "insider_signals": [], "reasoning": "test"}'

        data = {"NVDA": {"price": 400.0, "price_change_1d": 5.0, "volume": 100000000, "rsi_14": 65.0, "macd": 1.2}}
        moves = [{"ticker": "CDLX", "move_pct": 12.5, "direction": "up", "volume_vs_avg": 3.5, "flagged_reason": "No news"}]
        analyze_alpha(data, moves, llm_caller=capturing_caller)

        assert captured_prompt is not None
        assert "NVDA" in captured_prompt
        assert "CDLX" in captured_prompt
        assert "alpha hunter" in captured_prompt.lower()
