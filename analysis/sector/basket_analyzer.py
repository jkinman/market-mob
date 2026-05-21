"""Basket analyzer — analyze a basket of stocks and return aggregated metrics."""

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import numpy as np

from analysis.technical.fetch_prices import PriceData, fetch_multi
from analysis.technical.indicators import compute_all, summarize_latest
from analysis.technical.suspicious_moves import detect_suspicious_move, SuspiciousMove


@dataclass
class StockScore:
    """Container for individual stock scoring within a sector."""

    ticker: str
    price: float
    price_change_1d: float
    rsi_14: float
    above_sma_20: bool
    above_sma_50: bool
    macd_bullish: bool  # MACD > Signal
    momentum_score: float  # composite 0-100
    risk_score: float  # composite 0-100 (higher = more risky)
    opportunity_rank: int = 0  # 1 = best opportunity


@dataclass
class SectorAnalysis:
    """Container for aggregated sector analysis results."""

    sector_name: str
    tickers_analyzed: list[str]
    tickers_failed: list[str] = field(default_factory=list)

    # Aggregated metrics
    avg_rsi: float = 0.0
    pct_above_sma20: float = 0.0
    pct_above_sma50: float = 0.0
    pct_bullish_macd: float = 0.0
    avg_price_change_1d: float = 0.0

    # Leaders / laggards
    top_momentum: Optional[StockScore] = None
    worst_performer: Optional[StockScore] = None

    # Suspicious moves
    suspicious_moves: list[SuspiciousMove] = field(default_factory=list)

    # Ranked list (best opportunity first)
    ranked_stocks: list[StockScore] = field(default_factory=list)

    # News / sentiment placeholder
    sentiment_placeholder: str = "News/sentiment integration pending"


def _score_stock(summary: dict, ticker: str) -> StockScore:
    """Calculate opportunity and risk scores for a single stock.

    Scoring logic (opportunity):
      - RSI 40-60 = neutral (best opportunity zone), extremes penalized
      - Above SMA20 / SMA50 = bullish, adds points
      - MACD bullish = adds points
      - Positive 1d change = adds points

    Risk scoring:
      - High RSI (>70) or low RSI (<30) = elevated risk
      - Large 1d move = elevated risk
      - Below both SMAs = elevated risk
    """
    rsi = summary.get("rsi_14", 50.0)
    price = summary.get("price", 0.0)
    change_1d = summary.get("price_change_1d", 0.0)
    sma20 = summary.get("sma_20", price)
    sma50 = summary.get("sma_50", price)
    macd = summary.get("macd", 0.0)
    macd_signal = summary.get("macd_signal", 0.0)

    above_sma20 = price > sma20
    above_sma50 = price > sma50
    macd_bullish = macd > macd_signal

    # Opportunity score (0-100)
    momentum_score = 50.0  # baseline

    # RSI contribution: best near 50, penalize extremes
    rsi_dist = abs(rsi - 50)
    momentum_score += (25 - rsi_dist * 0.5)  # max +25 at RSI=50

    # Trend contribution
    if above_sma20:
        momentum_score += 10
    if above_sma50:
        momentum_score += 10
    if macd_bullish:
        momentum_score += 10

    # Recent momentum contribution
    if change_1d > 0:
        momentum_score += min(change_1d * 2, 10)
    else:
        momentum_score += max(change_1d * 2, -10)

    momentum_score = max(0.0, min(100.0, momentum_score))

    # Risk score (0-100, higher = more risky)
    risk_score = 30.0  # baseline

    if rsi > 70 or rsi < 30:
        risk_score += 20
    if abs(change_1d) > 5:
        risk_score += 20
    if not above_sma20 and not above_sma50:
        risk_score += 15
    if price < sma50 * 0.9:
        risk_score += 15

    risk_score = max(0.0, min(100.0, risk_score))

    return StockScore(
        ticker=ticker,
        price=round(price, 2),
        price_change_1d=round(change_1d, 2),
        rsi_14=round(rsi, 2),
        above_sma_20=above_sma20,
        above_sma_50=above_sma50,
        macd_bullish=macd_bullish,
        momentum_score=round(momentum_score, 2),
        risk_score=round(risk_score, 2),
    )


def analyze_sector(
    sector_name: str,
    tickers: list[str],
    period: str = "90d",
    suspicious_threshold: float = 10.0,
) -> SectorAnalysis:
    """Analyze a basket of stocks for a sector.

    Args:
        sector_name: Name of the sector
        tickers: List of ticker symbols
        period: Price history period
        suspicious_threshold: % move threshold for suspicious move flagging

    Returns:
        SectorAnalysis dataclass with aggregated metrics and rankings
    """
    # Fetch prices
    price_data = fetch_multi(tickers, period=period)

    scores: list[StockScore] = []
    failed: list[str] = []
    suspicious_moves: list[SuspiciousMove] = []

    for ticker, pdata in price_data.items():
        if pdata is None or pdata.df.empty or len(pdata.df) < 2:
            failed.append(ticker)
            continue

        # Compute indicators
        df = compute_all(pdata.df.copy())
        summary = summarize_latest(df)

        # Score stock
        score = _score_stock(summary, ticker)
        scores.append(score)

        # Check suspicious moves
        move = detect_suspicious_move(pdata, threshold_pct=suspicious_threshold)
        if move:
            suspicious_moves.append(move)

    if not scores:
        return SectorAnalysis(
            sector_name=sector_name,
            tickers_analyzed=[],
            tickers_failed=failed,
        )

    # Aggregated metrics
    avg_rsi = float(np.mean([s.rsi_14 for s in scores]))
    pct_above_sma20 = sum(1 for s in scores if s.above_sma_20) / len(scores) * 100
    pct_above_sma50 = sum(1 for s in scores if s.above_sma_50) / len(scores) * 100
    pct_bullish_macd = sum(1 for s in scores if s.macd_bullish) / len(scores) * 100
    avg_price_change_1d = float(np.mean([s.price_change_1d for s in scores]))

    # Rank by opportunity (momentum_score descending, then risk_score ascending)
    scores.sort(key=lambda s: (s.momentum_score, -s.risk_score), reverse=True)
    for i, s in enumerate(scores, start=1):
        s.opportunity_rank = i

    top_momentum = scores[0]
    worst_performer = min(scores, key=lambda s: s.momentum_score)

    return SectorAnalysis(
        sector_name=sector_name,
        tickers_analyzed=[s.ticker for s in scores],
        tickers_failed=failed,
        avg_rsi=round(avg_rsi, 2),
        pct_above_sma20=round(pct_above_sma20, 2),
        pct_above_sma50=round(pct_above_sma50, 2),
        pct_bullish_macd=round(pct_bullish_macd, 2),
        avg_price_change_1d=round(avg_price_change_1d, 2),
        top_momentum=top_momentum,
        worst_performer=worst_performer,
        suspicious_moves=suspicious_moves,
        ranked_stocks=scores,
        sentiment_placeholder="News/sentiment integration pending",
    )


if __name__ == "__main__":
    # Smoke test
    import numpy as np

    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    prices = 100 + np.cumsum(np.random.randn(30) * 2)
    df = pd.DataFrame({
        "Open": [p - 1 for p in prices],
        "High": [p + 2 for p in prices],
        "Low": [p - 2 for p in prices],
        "Close": prices,
        "Volume": np.random.randint(1e6, 5e6, 30),
    }, index=dates)

    pdata = PriceData(ticker="FAKE", df=df, period="30d", interval="1d")
    summary = summarize_latest(compute_all(df))
    score = _score_stock(summary, "FAKE")
    print(score)
