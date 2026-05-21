"""Tests for investor persona loader, formatter, and prompt injection."""

import json
import os
import tempfile

import pytest

from agents.persona.persona_loader import (
    Persona,
    Position,
    load_persona,
    format_persona_for_prompt,
    get_position_for_ticker,
    format_position_context,
)
from agents.analyst.llm_analyst import (
    build_prompt,
    build_overview_prompt,
    build_alpha_prompt,
    analyze_stock,
    analyze_overview,
    analyze_alpha,
)


class TestLoadPersona:
    """Tests for persona loading from JSON."""

    def test_load_valid_persona(self):
        """Should load a valid persona JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "name": "Test Investor",
                    "risk_tolerance": "aggressive",
                    "time_horizon": "short",
                    "preferred_sectors": ["tech", "crypto"],
                    "avoid_sectors": ["utilities"],
                    "current_positions": [
                        {"ticker": "TSLA", "shares": 50, "avg_cost": 200.0}
                    ],
                    "max_position_size_pct": 15.0,
                    "min_liquidity": 10.0,
                    "notes": "Likes high-growth names.",
                },
                f,
            )
            path = f.name

        try:
            persona = load_persona(path)
            assert persona is not None
            assert persona.name == "Test Investor"
            assert persona.risk_tolerance == "aggressive"
            assert persona.time_horizon == "short"
            assert persona.preferred_sectors == ["tech", "crypto"]
            assert persona.avoid_sectors == ["utilities"]
            assert len(persona.current_positions) == 1
            assert persona.current_positions[0].ticker == "TSLA"
            assert persona.current_positions[0].shares == 50
            assert persona.current_positions[0].avg_cost == 200.0
            assert persona.max_position_size_pct == 15.0
            assert persona.min_liquidity == 10.0
            assert persona.notes == "Likes high-growth names."
        finally:
            os.unlink(path)

    def test_load_missing_file_returns_none(self):
        """Should return None if file does not exist."""
        result = load_persona("config/nonexistent_persona.json")
        assert result is None

    def test_load_invalid_json_returns_none(self):
        """Should return None for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            path = f.name

        try:
            result = load_persona(path)
            assert result is None
        finally:
            os.unlink(path)

    def test_load_defaults_for_missing_fields(self):
        """Should use defaults for missing fields."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({}, f)
            path = f.name

        try:
            persona = load_persona(path)
            assert persona is not None
            assert persona.name == "Default Investor"
            assert persona.risk_tolerance == "moderate"
            assert persona.time_horizon == "medium"
            assert persona.preferred_sectors == []
            assert persona.avoid_sectors == []
            assert persona.current_positions == []
            assert persona.max_position_size_pct == 10.0
            assert persona.min_liquidity == 5.0
            assert persona.notes == ""
        finally:
            os.unlink(path)

    def test_load_skips_malformed_positions(self):
        """Should skip malformed position entries."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "current_positions": [
                        {"ticker": "AAPL", "shares": "abc", "avg_cost": 150.0},
                        {"ticker": "NVDA", "shares": 10, "avg_cost": 400.0},
                    ]
                },
                f,
            )
            path = f.name

        try:
            persona = load_persona(path)
            assert persona is not None
            assert len(persona.current_positions) == 1
            assert persona.current_positions[0].ticker == "NVDA"
        finally:
            os.unlink(path)


class TestFormatPersonaForPrompt:
    """Tests for formatting persona as prompt snippet."""

    def test_format_returns_empty_for_none(self):
        """Should return empty string when persona is None."""
        assert format_persona_for_prompt(None) == ""

    def test_format_includes_key_fields(self):
        """Should include name, risk, horizon, etc."""
        persona = Persona(
            name="Alice",
            risk_tolerance="conservative",
            time_horizon="long",
            preferred_sectors=["finance", "healthcare"],
            avoid_sectors=["gambling"],
            max_position_size_pct=5.0,
            min_liquidity=20.0,
            notes="Dividend focus.",
        )
        text = format_persona_for_prompt(persona)
        assert "Alice" in text
        assert "conservative" in text
        assert "long" in text
        assert "finance" in text
        assert "healthcare" in text
        assert "gambling" in text
        assert "5.0" in text
        assert "20.0" in text
        assert "Dividend focus" in text

    def test_format_omits_empty_lists(self):
        """Should not include empty sector lists."""
        persona = Persona(name="Bob", risk_tolerance="moderate", time_horizon="medium")
        text = format_persona_for_prompt(persona)
        assert "Preferred Sectors" not in text
        assert "Avoid Sectors" not in text


class TestGetPositionForTicker:
    """Tests for position lookup."""

    def test_find_existing_position(self):
        """Should return position dict for held ticker."""
        persona = Persona(
            current_positions=[Position(ticker="AAPL", shares=100, avg_cost=150.0)]
        )
        pos = get_position_for_ticker(persona, "AAPL")
        assert pos is not None
        assert pos["ticker"] == "AAPL"
        assert pos["shares"] == 100
        assert pos["avg_cost"] == 150.0

    def test_case_insensitive_lookup(self):
        """Should match tickers case-insensitively."""
        persona = Persona(
            current_positions=[Position(ticker="aapl", shares=50, avg_cost=140.0)]
        )
        pos = get_position_for_ticker(persona, "AAPL")
        assert pos is not None
        assert pos["ticker"] == "aapl"

    def test_none_persona_returns_none(self):
        """Should return None if persona is None."""
        assert get_position_for_ticker(None, "AAPL") is None

    def test_missing_position_returns_none(self):
        """Should return None for unheld ticker."""
        persona = Persona(current_positions=[])
        assert get_position_for_ticker(persona, "TSLA") is None


class TestFormatPositionContext:
    """Tests for position context sentence."""

    def test_returns_sentence_for_position(self):
        """Should format a sentence describing the position."""
        persona = Persona(
            current_positions=[Position(ticker="NVDA", shares=25, avg_cost=450.0)]
        )
        text = format_position_context(persona, "NVDA")
        assert "25 shares" in text
        assert "NVDA" in text
        assert "$450.00" in text

    def test_returns_empty_for_no_position(self):
        """Should return empty string if no position."""
        persona = Persona(current_positions=[])
        assert format_position_context(persona, "META") == ""


class TestPromptInjection:
    """Tests that persona context is injected into LLM prompts."""

    def test_build_prompt_includes_persona(self):
        """Stock prompt should include persona block."""
        persona = Persona(
            name="Test",
            risk_tolerance="aggressive",
            time_horizon="short",
            current_positions=[Position(ticker="TSLA", shares=10, avg_cost=200.0)],
        )
        indicators = {
            "price": 250.0,
            "price_change_1d": 5.0,
            "volume": 1000000,
            "rsi_14": 60.0,
            "macd": 0.5,
            "macd_signal": 0.3,
            "macd_histogram": 0.2,
            "sma_20": 245.0,
            "sma_50": 240.0,
            "bb_upper": 260.0,
            "bb_lower": 230.0,
        }
        prompt = build_prompt("TSLA", {}, indicators, persona=persona)
        assert "Investor Profile" in prompt
        assert "aggressive" in prompt
        assert "10 shares" in prompt
        assert "$200.00" in prompt

    def test_build_prompt_no_persona(self):
        """Stock prompt should not include persona block when None."""
        indicators = {
            "price": 250.0,
            "price_change_1d": 5.0,
            "volume": 1000000,
            "rsi_14": 60.0,
            "macd": 0.5,
            "macd_signal": 0.3,
            "macd_histogram": 0.2,
            "sma_20": 245.0,
            "sma_50": 240.0,
            "bb_upper": 260.0,
            "bb_lower": 230.0,
        }
        prompt = build_prompt("TSLA", {}, indicators, persona=None)
        assert "Investor Profile" not in prompt

    def test_build_overview_prompt_includes_persona(self):
        """Overview prompt should include persona block."""
        persona = Persona(name="Macro", risk_tolerance="moderate", time_horizon="long")
        data = {"AAPL": {"price": 150.0, "rsi_14": 55.0, "macd": 0.5}}
        prompt = build_overview_prompt(data, persona=persona)
        assert "Investor Profile" in prompt
        assert "moderate" in prompt

    def test_build_alpha_prompt_includes_persona(self):
        """Alpha prompt should include persona block."""
        persona = Persona(name="Alpha", risk_tolerance="aggressive", time_horizon="short")
        data = {"NVDA": {"price": 400.0, "rsi_14": 65.0, "macd": 1.2}}
        prompt = build_alpha_prompt(data, [], persona=persona)
        assert "Investor Profile" in prompt
        assert "aggressive" in prompt

    def test_analyze_stock_passes_persona_to_prompt(self):
        """analyze_stock should inject persona into the prompt sent to LLM."""
        captured_prompt = None

        def capturing_caller(prompt: str) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return '{"trend": "bullish", "support_level": 100, "resistance_level": 110, "prediction_7d": "up", "prediction_30d": "up", "confidence": "high", "risk_level": "low", "reasoning": "test"}'

        persona = Persona(
            name="Capturer",
            risk_tolerance="conservative",
            time_horizon="long",
        )
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

        result = analyze_stock("AAPL", {}, indicators, llm_caller=capturing_caller, persona=persona)

        assert result is not None
        assert captured_prompt is not None
        assert "Capturer" in captured_prompt
        assert "conservative" in captured_prompt

    def test_analyze_overview_passes_persona(self):
        """analyze_overview should inject persona into the prompt."""
        captured_prompt = None

        def capturing_caller(prompt: str) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return '{"market_sentiment": "neutral", "sector_trends": {}, "watchlist_health": "mixed", "breadth_summary": "", "top_opportunities": [], "top_risks": [], "reasoning": "test"}'

        persona = Persona(name="Overview", risk_tolerance="moderate", time_horizon="medium")
        data = {"AAPL": {"price": 150.0, "rsi_14": 55.0, "macd": 0.5}}

        result = analyze_overview(data, llm_caller=capturing_caller, persona=persona)

        assert result is not None
        assert captured_prompt is not None
        assert "Overview" in captured_prompt

    def test_analyze_alpha_passes_persona(self):
        """analyze_alpha should inject persona into the prompt."""
        captured_prompt = None

        def capturing_caller(prompt: str) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return '{"volatile_tickers": [], "suspicious_moves": [], "opportunity_setups": [], "contrarian_signals": [], "insider_signals": [], "reasoning": "test"}'

        persona = Persona(name="AlphaTest", risk_tolerance="aggressive", time_horizon="short")
        data = {"NVDA": {"price": 400.0, "rsi_14": 65.0, "macd": 1.2}}

        result = analyze_alpha(data, [], llm_caller=capturing_caller, persona=persona)

        assert result is not None
        assert captured_prompt is not None
        assert "AlphaTest" in captured_prompt
