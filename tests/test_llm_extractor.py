"""Tests for LLM pick extractor."""

import pytest

from agents.pick_extractor.llm_extractor import (
    build_extraction_prompt,
    parse_extraction_response,
    extract_picks_from_transcript,
    picks_to_watchlist,
    StockPick,
    ExtractionResult,
)


class TestBuildExtractionPrompt:
    """Tests for prompt building."""

    def test_prompt_contains_source(self):
        """Prompt should mention the source."""
        prompt = build_extraction_prompt("some transcript", "Test Channel")
        assert "Test Channel" in prompt

    def test_prompt_contains_transcript(self):
        """Prompt should include transcript text."""
        prompt = build_extraction_prompt("AAPL is great", "Source")
        assert "AAPL is great" in prompt

    def test_prompt_truncates_long_transcript(self):
        """Very long transcripts should be truncated."""
        long_transcript = "x" * 20000
        prompt = build_extraction_prompt(long_transcript, "Source")
        assert "truncated" in prompt
        assert len(prompt) < 15000

    def test_prompt_requests_json(self):
        """Prompt should ask for JSON output."""
        prompt = build_extraction_prompt("test", "Source")
        assert "JSON" in prompt


class TestParseExtractionResponse:
    """Tests for response parsing."""

    def test_parse_valid_response(self):
        """Should parse valid JSON response."""
        response = '''{
            "picks": [
                {
                    "ticker": "AAPL",
                    "company_name": "Apple Inc.",
                    "action": "buy",
                    "target_price": "$200",
                    "timeframe": "medium-term",
                    "confidence": "high",
                    "reasoning": "Great valuation",
                    "timestamp_in_video": "2:30"
                }
            ],
            "market_commentary": "Bullish",
            "sentiment": "bullish"
        }'''

        result = parse_extraction_response(response, "Test Channel", "2024-01-01")

        assert result is not None
        assert len(result.picks) == 1
        assert result.picks[0].ticker == "AAPL"
        assert result.picks[0].action == "buy"
        assert result.picks[0].source == "Test Channel"
        assert result.sentiment == "bullish"

    def test_parse_json_in_code_block(self):
        """Should handle markdown code blocks."""
        response = '''```json
        {
            "picks": [],
            "market_commentary": "No picks today",
            "sentiment": "neutral"
        }
        ```'''

        result = parse_extraction_response(response, "Source", "2024-01-01")

        assert result is not None
        assert len(result.picks) == 0
        assert result.sentiment == "neutral"

    def test_parse_invalid_json(self):
        """Should return None for invalid JSON."""
        result = parse_extraction_response("not json", "Source", "2024-01-01")
        assert result is None

    def test_parse_missing_optional_fields(self):
        """Should handle missing optional fields."""
        response = '{"picks": [{"ticker": "TSLA"}]}'
        result = parse_extraction_response(response, "Source", "2024-01-01")

        assert result is not None
        assert result.picks[0].ticker == "TSLA"
        assert result.picks[0].action == "watch"  # default
        assert result.picks[0].company_name is None

    def test_ticker_uppercase(self):
        """Tickers should be normalized to uppercase."""
        response = '{"picks": [{"ticker": "aapl", "action": "buy"}]}'
        result = parse_extraction_response(response, "Source", "2024-01-01")

        assert result.picks[0].ticker == "AAPL"


class TestExtractPicksFromTranscript:
    """Tests for end-to-end extraction."""

    def test_extract_with_mock_llm(self):
        """Should use custom LLM and return picks."""
        mock_response = '''{
            "picks": [
                {
                    "ticker": "NVDA",
                    "company_name": "NVIDIA",
                    "action": "buy",
                    "target_price": "$900",
                    "confidence": "high",
                    "reasoning": "AI boom"
                }
            ],
            "sentiment": "bullish"
        }'''

        def mock_llm(prompt: str) -> str:
            return mock_response

        result = extract_picks_from_transcript(
            "NVIDIA is great",
            source="Test Channel",
            llm_caller=mock_llm,
        )

        assert result is not None
        assert len(result.picks) == 1
        assert result.picks[0].ticker == "NVDA"

    def test_extract_with_failing_llm(self):
        """Should return None if LLM fails."""
        def failing_llm(prompt: str) -> str:
            raise Exception("Timeout")

        result = extract_picks_from_transcript(
            "test",
            source="Source",
            llm_caller=failing_llm,
        )

        assert result is None

    def test_extract_prompt_passed_to_llm(self):
        """Should build prompt and pass to LLM."""
        captured_prompt = None

        def capturing_llm(prompt: str) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return '{"picks": [], "sentiment": "neutral"}'

        extract_picks_from_transcript(
            "Some transcript about stocks",
            source="YouTube Channel",
            video_title="Market Analysis",
            llm_caller=capturing_llm,
        )

        assert captured_prompt is not None
        assert "YouTube Channel" in captured_prompt
        assert "Market Analysis" in captured_prompt
        assert "Some transcript" in captured_prompt


class TestPicksToWatchlist:
    """Tests for watchlist conversion."""

    def test_convert_single_pick(self):
        """Should convert StockPick to watchlist dict."""
        pick = StockPick(
            ticker="AAPL",
            company_name="Apple",
            action="buy",
            target_price="$200",
            timeframe="medium-term",
            confidence="high",
            reasoning="Good value",
            timestamp_in_video="2:30",
            source="Test",
            extracted_at="2024-01-01",
        )

        watchlist = picks_to_watchlist([pick])

        assert len(watchlist) == 1
        assert watchlist[0]["ticker"] == "AAPL"
        assert watchlist[0]["action"] == "buy"
        assert watchlist[0]["status"] == "active"

    def test_convert_multiple_picks(self):
        """Should convert multiple picks."""
        picks = [
            StockPick("AAPL", None, "buy", None, None, None, None, None, "Source", "2024-01-01"),
            StockPick("TSLA", None, "watch", None, None, None, None, None, "Source", "2024-01-01"),
        ]

        watchlist = picks_to_watchlist(picks)

        assert len(watchlist) == 2
        assert watchlist[0]["ticker"] == "AAPL"
        assert watchlist[1]["ticker"] == "TSLA"
