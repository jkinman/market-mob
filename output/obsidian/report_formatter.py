"""Format analysis results as Obsidian markdown notes."""

from datetime import datetime
from typing import Optional

from agents.analyst.llm_analyst import AnalysisResult
from agents.persona.persona_loader import Persona, format_persona_for_prompt, get_position_for_ticker
from analysis.accuracy_tracker import AccuracyTracker


def format_accuracy_section() -> str:
    """Generate an accuracy stats markdown section.

    Returns:
        Markdown string with overall accuracy % and breakdown.
    """
    tracker = AccuracyTracker()
    stats = tracker.get_accuracy_stats()

    if stats["total_predictions"] == 0:
        return """## Prediction Accuracy

No predictions recorded yet.
"""

    lines = [
        "## Prediction Accuracy",
        "",
        f"- **Total Predictions**: {stats['total_predictions']}",
        f"- **7-Day Scored**: {stats['scored_7d']}",
        f"- **30-Day Scored**: {stats['scored_30d']}",
    ]

    for timeframe in ["7d", "30d"]:
        total = stats[f"scored_{timeframe}"]
        if total > 0:
            pct = stats[f"accuracy_{timeframe}"].get("pct_correct", 0.0)
            correct = stats[f"accuracy_{timeframe}"]["correct"]
            directional = stats[f"accuracy_{timeframe}"]["directionally_correct"]
            wrong = stats[f"accuracy_{timeframe}"]["wrong"]
            lines.append(f"- **{timeframe} Accuracy**: {pct}% correct ({correct} correct, {directional} directionally correct, {wrong} wrong)")

    lines.append("")
    return "\n".join(lines)


def format_daily_report(
    ticker: str,
    price_summary: dict,
    indicators_summary: dict,
    analysis: AnalysisResult,
    source: str = "manual",
    persona: Optional[Persona] = None,
) -> str:
    """Format a single-stock analysis as an Obsidian markdown note.

    Args:
        ticker: Stock symbol
        price_summary: Price data summary
        indicators_summary: Indicator values
        analysis: LLM analysis result
        source: Where the pick came from (youtube, manual, etc.)
        persona: Optional investor persona for report context

    Returns:
        Markdown string
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    persona_section = ""
    if persona is not None:
        persona_lines = ["## Investor Profile", ""]
        persona_lines.append(f"- **Name:** {persona.name}")
        persona_lines.append(f"- **Risk Tolerance:** {persona.risk_tolerance}")
        persona_lines.append(f"- **Time Horizon:** {persona.time_horizon}")
        if persona.preferred_sectors:
            persona_lines.append(f"- **Preferred Sectors:** {', '.join(persona.preferred_sectors)}")
        if persona.avoid_sectors:
            persona_lines.append(f"- **Avoid Sectors:** {', '.join(persona.avoid_sectors)}")
        persona_lines.append(f"- **Max Position Size:** {persona.max_position_size_pct}%")
        persona_lines.append(f"- **Min Liquidity:** ${persona.min_liquidity}M")
        if persona.notes:
            persona_lines.append(f"- **Notes:** {persona.notes}")

        pos = get_position_for_ticker(persona, ticker)
        if pos is not None:
            persona_lines.append("")
            persona_lines.append(f"### Current Position in {ticker}")
            persona_lines.append(f"- **Shares:** {pos['shares']}")
            persona_lines.append(f"- **Avg Cost:** ${pos['avg_cost']:.2f}")

        persona_section = "\n".join(persona_lines) + "\n\n"

    report = f"""---
date: {datetime.now().strftime("%Y-%m-%d")}
ticker: {ticker}
source: {source}
status: active
---

# {ticker} Analysis — {now}

{persona_section}## Price Data
- **Current Price**: ${indicators_summary['price']}
- **1-Day Change**: ${indicators_summary['price_change_1d']}
- **Volume**: {indicators_summary['volume']:,}

## Technical Indicators
| Indicator | Value |
|-----------|-------|
| RSI (14) | {indicators_summary['rsi_14']} |
| MACD | {indicators_summary['macd']} |
| MACD Signal | {indicators_summary['macd_signal']} |
| MACD Histogram | {indicators_summary['macd_histogram']} |
| SMA 20 | {indicators_summary['sma_20']} |
| SMA 50 | {indicators_summary['sma_50']} |
| Bollinger Upper | {indicators_summary['bb_upper']} |
| Bollinger Lower | {indicators_summary['bb_lower']} |

## LLM Analysis
- **Trend**: {analysis.trend}
- **Support Level**: ${analysis.support_level}
- **Resistance Level**: ${analysis.resistance_level}
- **7-Day Prediction**: {analysis.prediction_7d}
- **30-Day Prediction**: {analysis.prediction_30d}
- **Confidence**: {analysis.confidence}
- **Risk Level**: {analysis.risk_level}

### Reasoning
{analysis.reasoning}

## Notes
- Source: {source}
- Generated: {now}
- [[Stock Watchlist]]

{format_accuracy_section()}---
*Not financial advice. AI-generated analysis.*
"""

    return report


def save_report(ticker: str, content: str, output_dir: str = "output/obsidian") -> str:
    """Save report to file.

    Returns:
        File path
    """
    import os

    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{output_dir}/{date_str}--{ticker.lower()}.md"

    with open(filename, "w") as f:
        f.write(content)

    return filename


if __name__ == "__main__":
    # Smoke test
    from agents.analyst.llm_analyst import AnalysisResult

    dummy = AnalysisResult(
        ticker="AAPL",
        trend="bullish",
        support_level=140.0,
        resistance_level=160.0,
        prediction_7d="up 3%",
        prediction_30d="up 8%",
        confidence="medium",
        risk_level="medium",
        reasoning="Strong momentum above SMAs.",
        raw_response="",
    )

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

    report = format_daily_report("AAPL", {}, indicators, dummy)
    print(report)
