"""Suspicious move detector for unusual price movements without catalysts.

Flags stocks with large daily moves (default >=10%) that lack an obvious
news catalyst.  News checking is currently a placeholder; real integration
will be added later.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from analysis.technical.fetch_prices import PriceData


@dataclass
class SuspiciousMove:
    """Container for a flagged suspicious price move."""

    ticker: str
    move_pct: float
    direction: str  # "up" or "down"
    volume_vs_avg: float
    flagged_reason: str
    has_news_catalyst: Optional[bool] = None


def calculate_daily_change(price_data: PriceData) -> float:
    """Calculate the latest daily percentage change.

    Args:
        price_data: PriceData object with historical prices

    Returns:
        Percentage change from previous close to latest close
    """
    df = price_data.df
    if len(df) < 2:
        return 0.0

    prev_close = float(df["Close"].iloc[-2])
    latest_close = float(df["Close"].iloc[-1])

    if prev_close == 0:
        return 0.0

    return ((latest_close - prev_close) / prev_close) * 100


def volume_vs_average(price_data: PriceData, lookback: int = 20) -> float:
    """Compare latest volume to the average over a lookback period.

    Args:
        price_data: PriceData object with historical prices
        lookback: Number of periods to average (default 20)

    Returns:
        Ratio of latest volume to average volume (1.0 = average)
    """
    df = price_data.df
    if "Volume" not in df.columns or len(df) < 2:
        return 1.0

    avg_volume = float(df["Volume"].iloc[-lookback:].mean())
    latest_volume = float(df["Volume"].iloc[-1])

    if avg_volume == 0:
        return 1.0

    return latest_volume / avg_volume


def check_news_catalyst(ticker: str) -> Optional[bool]:
    """Placeholder for news catalyst check.

    Returns None to indicate "unknown / not checked yet".
    Real news integration will be added in a future iteration.
    """
    return None


def detect_suspicious_move(
    price_data: PriceData,
    threshold_pct: float = 10.0,
) -> Optional[SuspiciousMove]:
    """Detect if a stock had a suspicious price move.

    Args:
        price_data: PriceData object with historical prices
        threshold_pct: Minimum absolute % change to flag (default 10%)

    Returns:
        SuspiciousMove if move exceeds threshold, else None
    """
    move_pct = calculate_daily_change(price_data)

    if abs(move_pct) < threshold_pct:
        return None

    direction = "up" if move_pct > 0 else "down"
    vol_ratio = volume_vs_average(price_data)

    reason = f"{abs(move_pct):.1f}% move {direction} with no confirmed news catalyst"

    return SuspiciousMove(
        ticker=price_data.ticker,
        move_pct=round(move_pct, 2),
        direction=direction,
        volume_vs_avg=round(vol_ratio, 2),
        flagged_reason=reason,
        has_news_catalyst=check_news_catalyst(price_data.ticker),
    )


def scan_tickers(
    ticker_data: dict[str, Optional[PriceData]],
    threshold_pct: float = 10.0,
) -> list[SuspiciousMove]:
    """Scan multiple tickers for suspicious moves.

    Args:
        ticker_data: Dict mapping ticker -> PriceData or None
        threshold_pct: Minimum absolute % change to flag

    Returns:
        List of SuspiciousMove objects for flagged tickers
    """
    results: list[SuspiciousMove] = []

    for ticker, data in ticker_data.items():
        if data is None or data.df.empty or len(data.df) < 2:
            continue

        move = detect_suspicious_move(data, threshold_pct)
        if move:
            results.append(move)

    # Sort by absolute move size descending
    results.sort(key=lambda m: abs(m.move_pct), reverse=True)
    return results


if __name__ == "__main__":
    # Quick smoke test
    import numpy as np

    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    prices = [100.0, 101.0, 102.0, 103.0, 115.0]  # 11.6% move on last day
    df = pd.DataFrame({
        "Open": [p - 1 for p in prices],
        "High": [p + 1 for p in prices],
        "Low": [p - 1 for p in prices],
        "Close": prices,
        "Volume": [1_000_000, 1_100_000, 1_050_000, 1_200_000, 3_000_000],
    }, index=dates)

    pdata = PriceData(ticker="CDLX", df=df, period="5d", interval="1d")
    result = detect_suspicious_move(pdata, threshold_pct=10.0)
    if result:
        print(f"Flagged: {result.ticker} {result.move_pct}% {result.direction}")
        print(f"  Volume vs avg: {result.volume_vs_avg}x")
        print(f"  Reason: {result.flagged_reason}")
    else:
        print("No suspicious moves detected.")
