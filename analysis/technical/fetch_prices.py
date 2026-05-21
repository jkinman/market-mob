"""Fetch historical stock price data via yfinance."""

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import yfinance as yf


@dataclass
class PriceData:
    """Container for fetched price data with metadata."""

    ticker: str
    df: pd.DataFrame
    period: str
    interval: str

    @property
    def latest_close(self) -> float:
        return float(self.df["Close"].iloc[-1])

    @property
    def latest_volume(self) -> int:
        return int(self.df["Volume"].iloc[-1])

    @property
    def days_of_data(self) -> int:
        return len(self.df)


def fetch_prices(
    ticker: str,
    period: str = "90d",
    interval: str = "1d",
) -> Optional[PriceData]:
    """Fetch historical price data for a ticker.

    Args:
        ticker: Stock symbol (e.g., "AAPL")
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

    Returns:
        PriceData object or None if fetch fails
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)

        if df.empty:
            print(f"[ERROR] No data returned for {ticker}")
            return None

        # Clean column names (yfinance sometimes has spaces)
        df.columns = [c.replace(" ", "").capitalize() for c in df.columns]

        return PriceData(
            ticker=ticker.upper(),
            df=df,
            period=period,
            interval=interval,
        )

    except Exception as e:
        print(f"[ERROR] Failed to fetch prices for {ticker}: {e}")
        return None


def fetch_multi(tickers: list[str], period: str = "90d") -> dict[str, Optional[PriceData]]:
    """Fetch prices for multiple tickers.

    Returns:
        Dict mapping ticker -> PriceData or None
    """
    return {t: fetch_prices(t, period) for t in tickers}


if __name__ == "__main__":
    # Quick smoke test
    data = fetch_prices("AAPL", period="5d")
    if data:
        print(f"{data.ticker}: ${data.latest_close:.2f} ({data.days_of_data} days)")
        print(data.df.tail())
