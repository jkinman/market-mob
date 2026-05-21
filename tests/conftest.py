"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def sample_price_data():
    """Return a small DataFrame-like dict for testing indicators."""
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    np.random.seed(42)
    
    # Generate realistic-looking price data
    base = 100
    prices = []
    for i in range(30):
        change = np.random.normal(0, 2)
        base += change
        prices.append(base)
    
    df = pd.DataFrame({
        "Open": [p - 1 for p in prices],
        "High": [p + 2 for p in prices],
        "Low": [p - 2 for p in prices],
        "Close": prices,
        "Volume": [1000000 + i * 1000 for i in range(30)],
    }, index=dates)
    
    return df
