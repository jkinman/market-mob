"""LLM analyst agent that generates stock analysis from price data + indicators."""

import json
import os
from dataclasses import dataclass
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


def parse_analysis_response(response: str, ticker: str) -> Optional[AnalysisResult]:
    """Parse LLM JSON response into AnalysisResult.

    Args:
        response: Raw LLM output (should contain JSON)
        ticker: Stock symbol for context

    Returns:
        AnalysisResult or None if parsing fails
    """
    try:
        # Extract JSON from response (handle markdown code blocks)
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)

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
