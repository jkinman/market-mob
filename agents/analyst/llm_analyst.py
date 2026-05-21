"""LLM analyst agent that generates stock analysis from price data + indicators."""

import json
import os
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class AnalysisResult:
    """Container for LLM analysis output."""

    ticker: str
    trend: str
    support_level: float
    resistance_level: float
    prediction_7d: str
    prediction_30d: str
    confidence: str
    risk_level: str
    reasoning: str
    raw_response: str


@dataclass
class OverviewResult:
    """Container for market overview analysis output."""

    market_sentiment: str
    sector_trends: dict
    watchlist_health: str
    breadth_summary: str
    top_opportunities: list[str]
    top_risks: list[str]
    reasoning: str
    raw_response: str


@dataclass
class AlphaResult:
    """Container for daily alpha analysis output."""

    volatile_tickers: list[str]
    suspicious_moves: list[dict]
    opportunity_setups: list[dict]
    contrarian_signals: list[dict]
    insider_signals: list[str]
    reasoning: str
    raw_response: str


def build_prompt(ticker: str, price_summary: dict, indicators_summary: dict) -> str:
    """Build a structured prompt for the LLM analyst.

    Args:
        ticker: Stock symbol
        price_summary: Dict with price data (from fetch_prices)
        indicators_summary: Dict with indicator values (from indicators.summarize_latest)

    Returns:
        Formatted prompt string
    """
    prompt = f"""You are a senior technical analyst at a hedge fund. Analyze the following stock data and provide a structured investment assessment.

## Stock: {ticker}

### Price Data
- Current Price: ${indicators_summary['price']}
- 1-Day Change: ${indicators_summary['price_change_1d']}
- Volume: {indicators_summary['volume']:,}

### Technical Indicators
- RSI (14): {indicators_summary['rsi_14']}
- MACD: {indicators_summary['macd']}
- MACD Signal: {indicators_summary['macd_signal']}
- MACD Histogram: {indicators_summary['macd_histogram']}
- SMA 20: {indicators_summary['sma_20']}
- SMA 50: {indicators_summary['sma_50']}
- Bollinger Upper: {indicators_summary['bb_upper']}
- Bollinger Lower: {indicators_summary['bb_lower']}

### Instructions
1. Identify the current trend (bullish/bearish/sideways)
2. Estimate support and resistance levels
3. Predict price direction for next 7 days and 30 days
4. Assess confidence level (high/medium/low)
5. Assess risk level (low/medium/high)
6. Provide concise reasoning (2-3 sentences)

Output STRICTLY as JSON:
{{
  "trend": "bullish|bearish|sideways",
  "support_level": 123.45,
  "resistance_level": 145.67,
  "prediction_7d": "up 5%|down 3%|flat",
  "prediction_30d": "up 10%|down 8%|flat",
  "confidence": "high|medium|low",
  "risk_level": "low|medium|high",
  "reasoning": "..."
}}

No markdown, no explanation outside JSON."""

    return prompt


def build_overview_prompt(tickers_data: dict) -> str:
    """Build a market overview prompt for the LLM analyst.

    Args:
        tickers_data: Dict mapping ticker -> indicators summary dict

    Returns:
        Formatted prompt string
    """
    ticker_summaries = []
    for ticker, data in tickers_data.items():
        summary = (
            f"- {ticker}: Price ${data.get('price', 'N/A')}, "
            f"Change ${data.get('price_change_1d', 'N/A')}, "
            f"RSI {data.get('rsi_14', 'N/A')}, "
            f"MACD {data.get('macd', 'N/A')}, "
            f"SMA20 {data.get('sma_20', 'N/A')}, "
            f"SMA50 {data.get('sma_50', 'N/A')}, "
            f"Volume {data.get('volume', 'N/A')}"
        )
        ticker_summaries.append(summary)

    summaries_text = "\n".join(ticker_summaries)

    prompt = f"""You are a senior macro strategist at a hedge fund. Provide a broad market overview based on the following watchlist data.

## Watchlist Summary
{summaries_text}

### Instructions
1. Assess overall market sentiment (bullish/bearish/neutral/mixed)
2. Identify sector trends (which sectors are strong/weak)
3. Assess watchlist health (how many tickers are trending well vs poorly)
4. Summarize market breadth (advancers vs decliners, RSI distribution)
5. List top 3 opportunities (tickers with best setups)
6. List top 3 risks (tickers showing weakness or warning signs)
7. Provide concise reasoning (3-5 sentences)

Output STRICTLY as JSON:
{{
  "market_sentiment": "bullish|bearish|neutral|mixed",
  "sector_trends": {{"tech": "strong", "energy": "weak"}},
  "watchlist_health": "healthy|mixed|unhealthy",
  "breadth_summary": "X advancers, Y decliners, average RSI Z",
  "top_opportunities": ["TICKER: reason", "TICKER: reason", "TICKER: reason"],
  "top_risks": ["TICKER: reason", "TICKER: reason", "TICKER: reason"],
  "reasoning": "..."
}}

No markdown, no explanation outside JSON."""

    return prompt


def build_alpha_prompt(tickers_data: dict, suspicious_moves: list) -> str:
    """Build a daily alpha prompt for the LLM analyst.

    Args:
        tickers_data: Dict mapping ticker -> indicators summary dict
        suspicious_moves: List of SuspiciousMove-like dicts or dataclasses

    Returns:
        Formatted prompt string
    """
    ticker_summaries = []
    for ticker, data in tickers_data.items():
        summary = (
            f"- {ticker}: Price ${data.get('price', 'N/A')}, "
            f"Change ${data.get('price_change_1d', 'N/A')}, "
            f"RSI {data.get('rsi_14', 'N/A')}, "
            f"MACD {data.get('macd', 'N/A')}, "
            f"Volume {data.get('volume', 'N/A')}"
        )
        ticker_summaries.append(summary)

    summaries_text = "\n".join(ticker_summaries)

    moves_text = "None detected"
    if suspicious_moves:
        move_lines = []
        for move in suspicious_moves:
            if hasattr(move, "ticker"):
                line = (
                    f"- {move.ticker}: {move.move_pct}% {move.direction}, "
                    f"volume {move.volume_vs_avg}x avg, reason: {move.flagged_reason}"
                )
            else:
                line = (
                    f"- {move.get('ticker', 'UNKNOWN')}: {move.get('move_pct', 'N/A')}% "
                    f"{move.get('direction', 'N/A')}, volume {move.get('volume_vs_avg', 'N/A')}x avg"
                )
            move_lines.append(line)
        moves_text = "\n".join(move_lines)

    prompt = f"""You are a senior alpha hunter at a hedge fund. Find volatile stocks, suspicious moves, and opportunity setups from the following data.

## Watchlist Summary
{summaries_text}

## Suspicious Moves
{moves_text}

### Instructions
1. List volatile tickers (largest moves, widest ranges, unusual volume)
2. Summarize suspicious moves (what's moving without clear catalyst)
3. Identify opportunity setups (breakouts, reversals, squeeze candidates)
4. List contrarian signals (oversold bounces, overbought shorts, divergences)
5. Flag any insider-like signals (unusual pre-move volume, gap patterns)
6. Provide concise reasoning (3-5 sentences)

Output STRICTLY as JSON:
{{
  "volatile_tickers": ["TICKER", "TICKER"],
  "suspicious_moves": [
    {{"ticker": "TICKER", "move_pct": 12.5, "direction": "up", "notes": "..."}}
  ],
  "opportunity_setups": [
    {{"ticker": "TICKER", "setup": "breakout|reversal|squeeze", "notes": "..."}}
  ],
  "contrarian_signals": [
    {{"ticker": "TICKER", "signal": "oversold_bounce|overbought_short|divergence", "notes": "..."}}
  ],
  "insider_signals": ["TICKER: unusual volume pattern", "TICKER: gap up pre-news"],
  "reasoning": "..."
}}

No markdown, no explanation outside JSON."""

    return prompt


def parse_analysis_response(response: str, ticker: str) -> Optional[AnalysisResult]:
    """Parse LLM JSON response into AnalysisResult.

    Args:
        response: Raw LLM output (should contain JSON)
        ticker: Stock symbol for context

    Returns:
        AnalysisResult or None if parsing fails
    """
    try:
        data = _extract_json(response)

        return AnalysisResult(
            ticker=ticker,
            trend=data.get("trend", "unknown"),
            support_level=float(data.get("support_level", 0)),
            resistance_level=float(data.get("resistance_level", 0)),
            prediction_7d=data.get("prediction_7d", "unknown"),
            prediction_30d=data.get("prediction_30d", "unknown"),
            confidence=data.get("confidence", "low"),
            risk_level=data.get("risk_level", "high"),
            reasoning=data.get("reasoning", ""),
            raw_response=response,
        )
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] Failed to parse LLM response: {e}")
        print(f"[ERROR] Raw response: {response[:500]}")
        return None


def parse_overview_response(response: str) -> Optional[OverviewResult]:
    """Parse LLM JSON response into OverviewResult.

    Args:
        response: Raw LLM output (should contain JSON)

    Returns:
        OverviewResult or None if parsing fails
    """
    try:
        data = _extract_json(response)

        return OverviewResult(
            market_sentiment=data.get("market_sentiment", "unknown"),
            sector_trends=data.get("sector_trends", {}),
            watchlist_health=data.get("watchlist_health", "unknown"),
            breadth_summary=data.get("breadth_summary", ""),
            top_opportunities=data.get("top_opportunities", []),
            top_risks=data.get("top_risks", []),
            reasoning=data.get("reasoning", ""),
            raw_response=response,
        )
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] Failed to parse overview response: {e}")
        print(f"[ERROR] Raw response: {response[:500]}")
        return None


def parse_alpha_response(response: str) -> Optional[AlphaResult]:
    """Parse LLM JSON response into AlphaResult.

    Args:
        response: Raw LLM output (should contain JSON)

    Returns:
        AlphaResult or None if parsing fails
    """
    try:
        data = _extract_json(response)

        return AlphaResult(
            volatile_tickers=data.get("volatile_tickers", []),
            suspicious_moves=data.get("suspicious_moves", []),
            opportunity_setups=data.get("opportunity_setups", []),
            contrarian_signals=data.get("contrarian_signals", []),
            insider_signals=data.get("insider_signals", []),
            reasoning=data.get("reasoning", ""),
            raw_response=response,
        )
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] Failed to parse alpha response: {e}")
        print(f"[ERROR] Raw response: {response[:500]}")
        return None


def _extract_json(response: str) -> dict:
    """Extract and parse JSON from LLM response, handling markdown code blocks."""
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    return json.loads(cleaned)


# Default LLM caller — can be overridden for testing or different providers
def _default_llm_call(prompt: str) -> str:
    """Call LLM. Override this or pass a custom caller to analyze_stock."""
    provider = os.getenv("LLM_PROVIDER", "ollama")

    if provider == "ollama":
        return _call_ollama(prompt)
    elif provider == "openai":
        return _call_openai(prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def _call_ollama(prompt: str, model: Optional[str] = None) -> str:
    """Call local Ollama instance."""
    import requests

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = model or os.getenv("OLLAMA_MODEL", "llama3.2")

    response = requests.post(
        f"{host}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"]


def _call_openai(prompt: str, model: Optional[str] = None) -> str:
    """Call OpenAI-compatible API (supports xAI Grok, etc.)."""
    import requests

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def analyze_stock(
    ticker: str,
    price_summary: dict,
    indicators_summary: dict,
    llm_caller: Optional[Callable[[str], str]] = None,
) -> Optional[AnalysisResult]:
    """Analyze a stock using LLM.

    Args:
        ticker: Stock symbol
        price_summary: Price data summary
        indicators_summary: Technical indicator summary
        llm_caller: Optional custom LLM function (for testing)

    Returns:
        AnalysisResult or None if analysis fails
    """
    prompt = build_prompt(ticker, price_summary, indicators_summary)

    caller = llm_caller or _default_llm_call

    try:
        response = caller(prompt)
        return parse_analysis_response(response, ticker)
    except Exception as e:
        print(f"[ERROR] LLM analysis failed for {ticker}: {e}")
        return None


def analyze_overview(
    tickers_data: dict,
    llm_caller: Optional[Callable[[str], str]] = None,
) -> Optional[OverviewResult]:
    """Run a market overview analysis on a watchlist using LLM.

    Args:
        tickers_data: Dict mapping ticker -> indicators summary dict
        llm_caller: Optional custom LLM function (for testing)

    Returns:
        OverviewResult or None if analysis fails
    """
    if not tickers_data:
        print("[ERROR] No ticker data provided for overview")
        return None

    prompt = build_overview_prompt(tickers_data)
    caller = llm_caller or _default_llm_call

    try:
        response = caller(prompt)
        return parse_overview_response(response)
    except Exception as e:
        print(f"[ERROR] LLM overview analysis failed: {e}")
        return None


def analyze_alpha(
    tickers_data: dict,
    suspicious_moves: list,
    llm_caller: Optional[Callable[[str], str]] = None,
) -> Optional[AlphaResult]:
    """Run a daily alpha scan on a watchlist using LLM.

    Args:
        tickers_data: Dict mapping ticker -> indicators summary dict
        suspicious_moves: List of SuspiciousMove-like objects or dicts
        llm_caller: Optional custom LLM function (for testing)

    Returns:
        AlphaResult or None if analysis fails
    """
    if not tickers_data:
        print("[ERROR] No ticker data provided for alpha scan")
        return None

    prompt = build_alpha_prompt(tickers_data, suspicious_moves)
    caller = llm_caller or _default_llm_call

    try:
        response = caller(prompt)
        return parse_alpha_response(response)
    except Exception as e:
        print(f"[ERROR] LLM alpha analysis failed: {e}")
        return None


if __name__ == "__main__":
    # Smoke test with dummy data
    dummy_price = {"latest_close": 150.0, "days_of_data": 90}
    dummy_indicators = {
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

    # Test prompt building
    prompt = build_prompt("AAPL", dummy_price, dummy_indicators)
    print("Prompt built successfully:")
    print(prompt[:500] + "...")

    # Test parsing with mock response
    mock_response = '''{
        "trend": "bullish",
        "support_level": 145.0,
        "resistance_level": 155.0,
        "prediction_7d": "up 3%",
        "prediction_30d": "up 8%",
        "confidence": "medium",
        "risk_level": "medium",
        "reasoning": "RSI neutral, MACD turning positive, price above both SMAs."
    }'''

    result = parse_analysis_response(mock_response, "AAPL")
    if result:
        print(f"\nParsed result: {result.trend}, confidence={result.confidence}")

    # Test overview prompt
    overview_prompt = build_overview_prompt({"AAPL": dummy_indicators, "TSLA": dummy_indicators})
    print("\nOverview prompt built successfully:")
    print(overview_prompt[:500] + "...")

    # Test alpha prompt
    alpha_prompt = build_alpha_prompt({"AAPL": dummy_indicators}, [])
    print("\nAlpha prompt built successfully:")
    print(alpha_prompt[:500] + "...")
