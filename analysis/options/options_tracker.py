"""Options activity tracking — volume, PCR ratio, unusual activity detection.

Uses yfinance to fetch options chain data and aggregate call/put volume
and open interest. Flags unusual activity based on configurable thresholds.
"""

import yfinance as yf

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class OptionsActivity:
    """Container for aggregated options activity data."""

    ticker: str
    call_volume: int
    put_volume: int
    call_oi: int
    put_oi: int
    pcr_ratio: float
    total_volume: int
    unusual_activity: bool
    largest_expiry: str
    notes: str = ""


def _aggregate_chain(calls: pd.DataFrame, puts: pd.DataFrame) -> dict:
    """Aggregate volume and open interest from a single expiry chain."""
    call_volume = int(calls.get("volume", pd.Series(dtype=int)).fillna(0).sum())
    put_volume = int(puts.get("volume", pd.Series(dtype=int)).fillna(0).sum())
    call_oi = int(calls.get("openInterest", pd.Series(dtype=int)).fillna(0).sum())
    put_oi = int(puts.get("openInterest", pd.Series(dtype=int)).fillna(0).sum())
    return {
        "call_volume": call_volume,
        "put_volume": put_volume,
        "call_oi": call_oi,
        "put_oi": put_oi,
    }


def fetch_options_activity(ticker: str) -> Optional[OptionsActivity]:
    """Fetch options chain for a ticker and aggregate activity metrics.

    Args:
        ticker: Stock symbol

    Returns:
        OptionsActivity dataclass or None if no options data available
    """
    ticker = ticker.upper()

    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        if not expirations:
            return None
    except Exception:
        return None

    total_call_volume = 0
    total_put_volume = 0
    total_call_oi = 0
    total_put_oi = 0
    largest_expiry = expirations[0]
    max_total_volume = 0

    for expiry in expirations:
        try:
            chain = stock.option_chain(expiry)
            agg = _aggregate_chain(chain.calls, chain.puts)
            total_call_volume += agg["call_volume"]
            total_put_volume += agg["put_volume"]
            total_call_oi += agg["call_oi"]
            total_put_oi += agg["put_oi"]

            expiry_total = agg["call_volume"] + agg["put_volume"]
            if expiry_total > max_total_volume:
                max_total_volume = expiry_total
                largest_expiry = expiry
        except Exception:
            continue

    total_volume = total_call_volume + total_put_volume
    if total_volume == 0:
        return None

    pcr_ratio = round(total_put_volume / total_call_volume, 4) if total_call_volume > 0 else 0.0

    return OptionsActivity(
        ticker=ticker,
        call_volume=total_call_volume,
        put_volume=total_put_volume,
        call_oi=total_call_oi,
        put_oi=total_put_oi,
        pcr_ratio=pcr_ratio,
        total_volume=total_volume,
        unusual_activity=False,  # computed separately
        largest_expiry=largest_expiry,
        notes="",
    )


def is_unusual_activity(
    activity: OptionsActivity,
    volume_threshold: float = 2.0,
    baseline_volume: Optional[int] = None,
) -> bool:
    """Determine if options activity is unusual.

    Args:
        activity: OptionsActivity dataclass
        volume_threshold: Multiplier above baseline to flag as unusual
        baseline_volume: Optional baseline volume to compare against.
            If None, a simple heuristic is used (see notes).

    Returns:
        True if activity is flagged as unusual
    """
    if baseline_volume is not None and baseline_volume > 0:
        return activity.total_volume > volume_threshold * baseline_volume

    # Simple heuristic: flag if total volume is very high relative to OI
    # or if PCR ratio is extreme (>2.0 or <0.3)
    total_oi = activity.call_oi + activity.put_oi
    if total_oi > 0 and activity.total_volume > volume_threshold * total_oi:
        return True
    if activity.pcr_ratio > 2.0 or activity.pcr_ratio < 0.3:
        return True

    return False


def fetch_options_batch(tickers: list[str]) -> dict[str, Optional[OptionsActivity]]:
    """Fetch options activity for multiple tickers.

    Args:
        tickers: List of stock symbols

    Returns:
        Dict mapping ticker -> OptionsActivity or None
    """
    results: dict[str, Optional[OptionsActivity]] = {}
    for ticker in tickers:
        activity = fetch_options_activity(ticker)
        if activity is not None:
            activity.unusual_activity = is_unusual_activity(activity)
        results[ticker.upper()] = activity
    return results
