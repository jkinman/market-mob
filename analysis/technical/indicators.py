"""Technical indicators for stock analysis.

Pure pandas/numpy implementations — no external TA library needed.
"""

import pandas as pd
import numpy as np


def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Compute Relative Strength Index (RSI).

    RSI = 100 - (100 / (1 + RS))
    where RS = average gain / average loss over period

    Args:
        prices: Series of closing prices
        period: Lookback period (default 14)

    Returns:
        Series of RSI values (0-100)
    """
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, pd.Series]:
    """Compute MACD (Moving Average Convergence Divergence).

    Returns:
        Dict with keys: macd_line, signal_line, histogram
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return {
        "macd_line": macd_line,
        "signal_line": signal_line,
        "histogram": histogram,
    }


def moving_average(prices: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average (SMA)."""
    return prices.rolling(window=period).mean()


def bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> dict[str, pd.Series]:
    """Compute Bollinger Bands.

    Returns:
        Dict with keys: middle (SMA), upper, lower
    """
    middle = moving_average(prices, period)
    std = prices.rolling(window=period).std()

    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    return {
        "middle": middle,
        "upper": upper,
        "lower": lower,
    }


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all indicators and append to DataFrame.

    Args:
        df: DataFrame with 'Close' column

    Returns:
        DataFrame with added indicator columns
    """
    if "Close" not in df.columns:
        raise ValueError("DataFrame must have 'Close' column")

    close = df["Close"]

    # RSI
    df["RSI_14"] = rsi(close)

    # MACD
    macd_vals = macd(close)
    df["MACD"] = macd_vals["macd_line"]
    df["MACD_Signal"] = macd_vals["signal_line"]
    df["MACD_Histogram"] = macd_vals["histogram"]

    # Moving Averages
    df["SMA_20"] = moving_average(close, 20)
    df["SMA_50"] = moving_average(close, 50)

    # Bollinger Bands
    bb = bollinger_bands(close)
    df["BB_Upper"] = bb["upper"]
    df["BB_Lower"] = bb["lower"]
    df["BB_Middle"] = bb["middle"]

    return df


def summarize_latest(df: pd.DataFrame) -> dict:
    """Get latest values of all indicators as a summary dict.

    Useful for building LLM prompts.
    """
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    return {
        "price": round(latest["Close"], 2),
        "price_change_1d": round(latest["Close"] - prev["Close"], 2),
        "rsi_14": round(latest.get("RSI_14", 0), 2),
        "macd": round(latest.get("MACD", 0), 4),
        "macd_signal": round(latest.get("MACD_Signal", 0), 4),
        "macd_histogram": round(latest.get("MACD_Histogram", 0), 4),
        "sma_20": round(latest.get("SMA_20", 0), 2),
        "sma_50": round(latest.get("SMA_50", 0), 2),
        "bb_upper": round(latest.get("BB_Upper", 0), 2),
        "bb_lower": round(latest.get("BB_Lower", 0), 2),
        "volume": int(latest.get("Volume", 0)),
    }


if __name__ == "__main__":
    # Smoke test with sample data
    import numpy as np

    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(60) * 2)
    df = pd.DataFrame({
        "Close": prices,
        "Volume": np.random.randint(1e6, 5e6, 60),
    }, index=pd.date_range("2024-01-01", periods=60))

    df = compute_all(df)
    print(df.tail())
    print("\nLatest summary:")
    print(summarize_latest(df))
