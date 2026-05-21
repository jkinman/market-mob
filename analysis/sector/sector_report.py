"""Sector-level markdown report generation."""

import os
from datetime import datetime
from typing import Optional

from analysis.sector.basket_analyzer import SectorAnalysis, StockScore


def _format_stock_table(stocks: list[StockScore]) -> str:
    """Format a list of StockScore objects as a markdown table."""
    lines = [
        "| Rank | Ticker | Price | 1D Change | RSI | Above SMA20 | Above SMA50 | MACD Bullish | Momentum | Risk |",
        "|------|--------|-------|-----------|-----|-------------|-------------|--------------|----------|------|",
    ]
    for s in stocks:
        lines.append(
            f"| {s.opportunity_rank} | {s.ticker} | ${s.price:.2f} | "
            f"{s.price_change_1d:+.2f}% | {s.rsi_14:.1f} | "
            f"{'Yes' if s.above_sma_20 else 'No'} | "
            f"{'Yes' if s.above_sma_50 else 'No'} | "
            f"{'Yes' if s.macd_bullish else 'No'} | "
            f"{s.momentum_score:.1f} | {s.risk_score:.1f} |"
        )
    return "\n".join(lines)


def _format_suspicious_moves(sector_analysis: SectorAnalysis) -> str:
    """Format suspicious moves section."""
    if not sector_analysis.suspicious_moves:
        return "No suspicious moves detected."

    lines = []
    for move in sector_analysis.suspicious_moves:
        lines.append(
            f"- **{move.ticker}**: {move.move_pct:+.2f}% {move.direction} "
            f"(volume {move.volume_vs_avg:.1f}x avg) — {move.flagged_reason}"
        )
    return "\n".join(lines)


def _format_options_summary(options_summary: Optional[dict]) -> str:
    """Format aggregated options summary section."""
    if options_summary is None:
        return "Options data not available."

    lines = [
        f"- **Tickers with Options Data**: {options_summary.get('tickers_with_data', 0)} / {options_summary.get('total_tickers', 0)}",
        f"- **Average Put/Call Ratio**: {options_summary.get('avg_pcr', 'N/A'):.2f}",
        f"- **Unusual Activity Count**: {options_summary.get('unusual_count', 0)}",
        f"- **Total Options Volume**: {options_summary.get('total_volume', 0):,}",
    ]
    by_ticker = options_summary.get('by_ticker', {})
    if by_ticker:
        lines.append("")
        lines.append("### By Ticker")
        for ticker, data in sorted(by_ticker.items()):
            flag = " ⚠️ Unusual" if data.get('unusual_activity') else ""
            lines.append(
                f"- **{ticker}**: Vol {data.get('total_volume', 0):,}, PCR {data.get('pcr_ratio', 0):.2f}{flag}"
            )
    return "\n".join(lines)


def generate_sector_report(
    sector_analysis: SectorAnalysis,
    source: str = "manual",
    options_summary: Optional[dict] = None,
) -> str:
    """Generate a markdown report for a sector analysis.

    Args:
        sector_analysis: SectorAnalysis dataclass
        source: Source of the analysis request
        options_summary: Optional dict with aggregated options metrics

    Returns:
        Markdown string
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_str = datetime.now().strftime("%Y-%m-%d")

    tickers_str = ", ".join(sector_analysis.tickers_analyzed)
    failed_str = ", ".join(sector_analysis.tickers_failed) if sector_analysis.tickers_failed else "None"

    top = sector_analysis.top_momentum
    worst = sector_analysis.worst_performer

    report = f"""---
date: {date_str}
sector: {sector_analysis.sector_name}
tickers: {tickers_str}
source: {source}
status: active
---

# {sector_analysis.sector_name.upper()} Sector Watchlist — {now}

## Sector Overview
- **Tickers Analyzed**: {len(sector_analysis.tickers_analyzed)}
- **Tickers Failed**: {failed_str}
- **Average RSI (14)**: {sector_analysis.avg_rsi:.2f}
- **% Above SMA 20**: {sector_analysis.pct_above_sma20:.1f}%
- **% Above SMA 50**: {sector_analysis.pct_above_sma50:.1f}%
- **% Bullish MACD**: {sector_analysis.pct_bullish_macd:.1f}%
- **Average 1-Day Change**: {sector_analysis.avg_price_change_1d:+.2f}%

## Leaders & Laggards
- **Top Momentum**: {top.ticker if top else "N/A"} (momentum score: {top.momentum_score if top else "N/A"})
- **Worst Performer**: {worst.ticker if worst else "N/A"} (momentum score: {worst.momentum_score if worst else "N/A"})

## Ranked Opportunities

{_format_stock_table(sector_analysis.ranked_stocks)}

## Suspicious Moves

{_format_suspicious_moves(sector_analysis)}

## Options Activity
{_format_options_summary(options_summary)}

## Sentiment & News
{sector_analysis.sentiment_placeholder}

## Notes
- Source: {source}
- Generated: {now}
- [[Sector Watchlist]]

---
*Not financial advice. AI-generated analysis.*
"""

    return report


def save_sector_report(
    sector_name: str,
    content: str,
    output_dir: str = "output/obsidian",
) -> str:
    """Save sector report to file.

    Returns:
        File path
    """
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{output_dir}/{date_str}--{sector_name.lower()}-sector.md"

    with open(filename, "w") as f:
        f.write(content)

    return filename


if __name__ == "__main__":
    # Smoke test
    dummy_scores = [
        StockScore(
            ticker="AAPL", price=150.0, price_change_1d=2.5,
            rsi_14=55.0, above_sma_20=True, above_sma_50=True,
            macd_bullish=True, momentum_score=85.0, risk_score=30.0,
            opportunity_rank=1,
        ),
        StockScore(
            ticker="MSFT", price=300.0, price_change_1d=-1.0,
            rsi_14=45.0, above_sma_20=True, above_sma_50=False,
            macd_bullish=False, momentum_score=60.0, risk_score=40.0,
            opportunity_rank=2,
        ),
    ]

    dummy_analysis = SectorAnalysis(
        sector_name="tech",
        tickers_analyzed=["AAPL", "MSFT"],
        avg_rsi=50.0,
        pct_above_sma20=50.0,
        pct_above_sma50=50.0,
        pct_bullish_macd=50.0,
        avg_price_change_1d=0.75,
        top_momentum=dummy_scores[0],
        worst_performer=dummy_scores[1],
        ranked_stocks=dummy_scores,
    )

    report = generate_sector_report(dummy_analysis)
    print(report)
