#!/usr/bin/env python3
"""Extract stock picks from transcript text using LLM prompting."""

import json
import os

# Simple extraction without LLM first — regex-based ticker detection
import re


def extract_tickers_regex(text: str) -> list[str]:
    """Extract potential stock tickers using regex.
    
    Looks for:
    - $TICKER format ($AAPL)
    - Explicit mentions like "ticker: AAPL" or "symbol: AAPL"
    - Common action words near tickers: "buy AAPL", "sell TSLA"
    - 2-5 letter ALL CAPS words (avoids single-letter false positives)
    """
    tickers = set()
    
    # $TICKER format
    dollar_tickers = re.findall(r'\$([A-Z]{1,5})\b', text)
    tickers.update(dollar_tickers)
    
    # "ticker ABC" or "symbol ABC" or "stock ABC"
    explicit = re.findall(r'(?:ticker|symbol|stock)\s+([A-Z]{1,5})\b', text, re.IGNORECASE)
    tickers.update(explicit)
    
    # Common action words near tickers: "buy AAPL", "sell TSLA"
    action_nearby = re.findall(r'(?:buy|sell|long|short|add)\s+([A-Z]{1,5})\b', text, re.IGNORECASE)
    tickers.update(action_nearby)
    
    # ETF mentions: "the QQQ", "buy SPY"
    etf_mentions = re.findall(r'\b(QQQ|SPY|VOO|VTI|ARKK|XSW|XLF|XLK|XLE)\b', text, re.IGNORECASE)
    tickers.update([t.upper() for t in etf_mentions])
    
    # Filter: require at least 2 chars, exclude common words
    common_words = {'A', 'I', 'AN', 'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WAY', 'WHO', 'BOY', 'DID', 'EYE', 'SHE', 'USE', 'HER', 'SAW', 'TOO', 'ANY', 'SAY', 'MAN', 'TRY', 'ASK', 'END', 'WHY', 'LET', 'PUT', 'SAY', 'SHE', 'TRY', 'WAY', 'OWN', 'SAY', 'TOO', 'OLD', 'TELL', 'VERY', 'WHEN', 'MUCH', 'WOULD', 'THERE', 'THEIR', 'WHAT', 'SAID', 'EACH', 'WHICH', 'WILL', 'ABOUT', 'IF', 'UP', 'OUT', 'MANY', 'THEN', 'THEM', 'THESE', 'SO', 'SOME', 'HER', 'WOULD', 'MAKE', 'LIKE', 'INTO', 'HIM', 'TIME', 'HAS', 'BEEN', 'MORE', 'VERY', 'WHAT', 'KNOW', 'JUST', 'FIRST', 'ALSO', 'AFTER', 'BACK', 'OTHER', 'MANY', 'THAN', 'ONLY', 'THOSE', 'COME', 'DAY', 'MOST', 'US', 'GOOD', 'WAY', 'EVEN', 'WELL', 'THROUGH', 'HERE', 'THINK', 'WHERE', 'BEING', 'EVERY', 'GREAT', 'MIGHT', 'STILL', 'WHILE', 'RIGHT', 'TOO', 'BACK', 'ONLY', 'KNOW', 'TAKE', 'YEAR', 'GOOD', 'SOME', 'COME', 'MAKE', 'WELL', 'WORK', 'LIFE', 'EVEN', 'MORE', 'WANT', 'HERE', 'LOOK', 'DOWN', 'MOST', 'LONG', 'LAST', 'FIND', 'GIVE', 'DOES', 'MADE', 'PART', 'OVER', 'SUCH', 'TAKE', 'THAN', 'THEM', 'WELL', 'WERE', 'SAID', 'EACH', 'WHICH', 'THEIR', 'TIME', 'WILL', 'ABOUT', 'IF', 'UP', 'OUT', 'MANY', 'THEN', 'THEM', 'THESE', 'SO', 'SOME', 'HER', 'WOULD', 'MAKE', 'LIKE', 'INTO', 'HIM', 'TIME', 'HAS', 'BEEN', 'MORE', 'VERY', 'WHAT', 'KNOW', 'JUST', 'FIRST', 'ALSO', 'AFTER', 'BACK', 'OTHER', 'MANY', 'THAN', 'ONLY', 'THOSE', 'COME', 'DAY', 'MOST', 'US', 'GOOD', 'WAY', 'EVEN', 'WELL', 'THROUGH', 'HERE', 'THINK', 'WHERE', 'BEING', 'EVERY', 'GREAT', 'MIGHT', 'STILL', 'WHILE', 'RIGHT', 'TOO', 'BACK', 'ONLY', 'KNOW', 'TAKE', 'YEAR', 'GOOD', 'SOME', 'COME', 'MAKE', 'WELL', 'WORK', 'LIFE', 'EVEN', 'MORE', 'WANT', 'HERE', 'LOOK', 'DOWN', 'MOST', 'LONG', 'LAST', 'FIND', 'GIVE', 'DOES', 'MADE', 'PART', 'OVER', 'SUCH', 'TAKE', 'THAN', 'THEM', 'WELL', 'WERE', 'CHART', 'VIDEO', 'RUN'}
    
    filtered = [t for t in tickers if len(t) >= 2 and t.upper() not in common_words]
    return sorted(filtered)


def build_llm_prompt(transcript: str, video_title: str = "", channel_name: str = "") -> str:
    """Build a structured prompt for LLM stock pick extraction."""
    prompt = f"""You are a financial news extractor. Read this YouTube video transcript and extract any stock picks, recommendations, or investment mentions.

Video: {video_title or "Unknown"}
Channel: {channel_name or "Unknown"}

Transcript:
{transcript[:8000]}

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

If no specific picks are found, return empty picks array. Be precise — only include tickers explicitly mentioned as recommendations, not just discussed."""
    
    return prompt


def extract_picks_llm(transcript: str, video_title: str = "", channel_name: str = "") -> dict:
    """Extract stock picks using LLM.
    
    For now, returns the prompt and expected format.
    In production, this calls an LLM API.
    """
    prompt = build_llm_prompt(transcript, video_title, channel_name)
    
    # TODO: Call LLM here
    # For POC, return regex results + prompt for manual inspection
    tickers = extract_tickers_regex(transcript)
    
    return {
        "detected_tickers_regex": tickers,
        "llm_prompt": prompt,
        "note": "LLM integration pending — run prompt manually or connect to local LLM"
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_picks.py <transcript_file>")
        sys.exit(1)
    
    with open(sys.argv[1], 'r') as f:
        transcript = f.read()
    
    result = extract_picks_llm(transcript)
    print(json.dumps(result, indent=2))
