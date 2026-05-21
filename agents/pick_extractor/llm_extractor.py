"""LLM-based stock pick extraction from video transcripts."""

import json
import re
from dataclasses import dataclass, asdict
from typing import Optional, Callable, List


@dataclass
class StockPick:
    """A single extracted stock pick."""

    ticker: str
    company_name: Optional[str]
    action: str  # buy, sell, hold, watch
    target_price: Optional[str]
    timeframe: Optional[str]
    confidence: Optional[str]
    reasoning: Optional[str]
    timestamp_in_video: Optional[str]
    source: str  # youtube channel, newsletter, etc.
    extracted_at: str


@dataclass
class ExtractionResult:
    """Full extraction result from a transcript."""

    picks: List[StockPick]
    market_commentary: Optional[str]
    sentiment: Optional[str]
    raw_response: str


def build_extraction_prompt(transcript: str, source: str, video_title: str = "") -> str:
    """Build prompt for LLM stock pick extraction.

    Args:
        transcript: Full transcript text
        source: Channel/source name
        video_title: Optional video title

    Returns:
        Formatted prompt
    """
    # Truncate very long transcripts
    max_chars = 12000
    truncated = transcript[:max_chars]
    if len(transcript) > max_chars:
        truncated += f"\n\n[... transcript truncated, {len(transcript) - max_chars} chars remaining ...]"

    prompt = f"""You are a financial news extractor. Read this transcript from {source} and extract any stock picks, recommendations, or investment mentions.

Video: {video_title or "Unknown"}
Source: {source}

Transcript:
{truncated}

Extract the following as JSON:
{{
  "picks": [
    {{
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "action": "buy|sell|hold|watch",
      "target_price": "$220",
      "timeframe": "short-term|medium-term|long-term",
      "confidence": "high|medium|low",
      "reasoning": "Brief summary of why",
      "timestamp_in_video": "approximate time if mentioned"
    }}
  ],
  "market_commentary": "Any general market outlook or sector mentions",
  "sentiment": "bullish|bearish|neutral"
}}

Rules:
- Only include tickers EXPLICITLY mentioned as recommendations or picks
- "I like X" or "I'm buying X" counts as a pick
- "X is interesting" or "watch X" counts as watch
- General discussion without recommendation does NOT count
- If no specific picks found, return empty picks array
- Be precise — don't hallucinate tickers not in the transcript

Output STRICTLY as JSON. No markdown, no explanation outside JSON."""

    return prompt


def _extract_json_from_response(response: str) -> Optional[dict]:
    """Extract JSON dict from LLM response, handling markdown blocks."""
    cleaned = response.strip()

    # Remove markdown code blocks
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Try to find JSON object if there's extra text
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract JSON between first { and last }
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return None


def parse_extraction_response(
    response: str,
    source: str,
    extracted_at: str,
) -> Optional[ExtractionResult]:
    """Parse LLM response into ExtractionResult.

    Args:
        response: Raw LLM output
        source: Source channel/name
        extracted_at: ISO timestamp

    Returns:
        ExtractionResult or None if parsing fails
    """
    data = _extract_json_from_response(response)
    if data is None:
        print(f"[ERROR] Failed to parse extraction response")
        print(f"[ERROR] Response preview: {response[:500]}")
        return None

    picks = []
    for pick_data in data.get("picks", []):
        picks.append(StockPick(
            ticker=pick_data.get("ticker", "UNKNOWN").upper(),
            company_name=pick_data.get("company_name"),
            action=pick_data.get("action", "watch").lower(),
            target_price=pick_data.get("target_price"),
            timeframe=pick_data.get("timeframe"),
            confidence=pick_data.get("confidence"),
            reasoning=pick_data.get("reasoning"),
            timestamp_in_video=pick_data.get("timestamp_in_video"),
            source=source,
            extracted_at=extracted_at,
        ))

    return ExtractionResult(
        picks=picks,
        market_commentary=data.get("market_commentary"),
        sentiment=data.get("sentiment"),
        raw_response=response,
    )


def extract_picks_from_transcript(
    transcript: str,
    source: str,
    video_title: str = "",
    llm_caller: Optional[Callable[[str], str]] = None,
    extracted_at: Optional[str] = None,
) -> Optional[ExtractionResult]:
    """Extract stock picks from a transcript using LLM.

    Args:
        transcript: Full transcript text
        source: Source name (channel, newsletter, etc.)
        video_title: Optional title
        llm_caller: Optional custom LLM function
        extracted_at: Optional timestamp

    Returns:
        ExtractionResult or None
    """
    from datetime import datetime

    prompt = build_extraction_prompt(transcript, source, video_title)

    # Use default LLM caller from analyst module
    if llm_caller is None:
        from agents.analyst.llm_analyst import _default_llm_call
        llm_caller = _default_llm_call

    timestamp = extracted_at or datetime.now().isoformat()

    try:
        response = llm_caller(prompt)
        return parse_extraction_response(response, source, timestamp)
    except Exception as e:
        print(f"[ERROR] Pick extraction failed: {e}")
        return None


def picks_to_watchlist(picks: List[StockPick]) -> List[dict]:
    """Convert StockPick objects to watchlist entries.

    Args:
        picks: List of extracted picks

    Returns:
        List of dicts for watchlist.json
    """
    return [
        {
            "ticker": pick.ticker,
            "action": pick.action,
            "source": pick.source,
            "reasoning": pick.reasoning,
            "confidence": pick.confidence,
            "extracted_at": pick.extracted_at,
            "status": "active",
        }
        for pick in picks
    ]


if __name__ == "__main__":
    # Smoke test
    mock_transcript = """
    Today I want to talk about Apple. I think AAPL is a great buy at these levels.
    I'm also watching Microsoft, MSFT looks interesting but I'm not buying yet.
    The market overall looks bullish to me.
    """

    mock_response = '''{
        "picks": [
            {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "action": "buy",
                "target_price": "$200",
                "timeframe": "medium-term",
                "confidence": "high",
                "reasoning": "Great valuation at current levels",
                "timestamp_in_video": "2:30"
            },
            {
                "ticker": "MSFT",
                "company_name": "Microsoft",
                "action": "watch",
                "target_price": null,
                "timeframe": "short-term",
                "confidence": "medium",
                "reasoning": "Looks interesting but waiting",
                "timestamp_in_video": "5:15"
            }
        ],
        "market_commentary": "Market looks bullish overall",
        "sentiment": "bullish"
    }'''

    def mock_llm(prompt: str) -> str:
        return mock_response

    result = extract_picks_from_transcript(
        mock_transcript,
        source="Test Channel",
        llm_caller=mock_llm,
    )

    if result:
        print(f"Extracted {len(result.picks)} picks:")
        for pick in result.picks:
            print(f"  {pick.ticker}: {pick.action} ({pick.confidence})")
        print(f"Sentiment: {result.sentiment}")
