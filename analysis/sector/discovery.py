"""Sector discovery module — maps sector names to ticker baskets."""

from typing import Optional

# Hardcoded sector baskets (top tickers by market cap / relevance)
SECTOR_BASKETS: dict[str, list[str]] = {
    "mining": [
        "GOLD", "NEM", "FNV", "WPM", "AEM",
        "KL", "NGD", "AGI", "PAAS", "SSRM",
    ],
    "tech": [
        "AAPL", "MSFT", "GOOGL", "META", "NVDA",
        "AMD", "CRM", "ADBE", "INTC", "ORCL",
    ],
    "energy": [
        "XOM", "CVX", "COP", "EOG", "MPC",
        "PSX", "VLO", "OXY", "DVN", "MRO",
    ],
    "biotech": [
        "BIIB", "GILD", "AMGN", "REGN", "VRTX",
        "MRNA", "BNTX", "SGEN", "ALNY", "INCY",
    ],
    "semiconductors": [
        "NVDA", "AMD", "INTC", "QCOM", "AVGO",
        "MU", "LRCX", "KLAC", "AMAT", "TSM",
    ],
    "cannabis": [
        "CGC", "TLRY", "ACB", "CRON", "SNDL",
        "GTBIF", "TCNNF", "CURLF", "VRNOF", "MSOS",
    ],
}


def get_sector_tickers(sector_name: str) -> Optional[list[str]]:
    """Return ticker list for a given sector name (case-insensitive).

    Args:
        sector_name: Sector name (e.g., "mining", "Tech")

    Returns:
        List of tickers or None if sector not found
    """
    return SECTOR_BASKETS.get(sector_name.lower())


def list_sectors() -> list[str]:
    """Return all available sector names."""
    return list(SECTOR_BASKETS.keys())


def add_sector(name: str, tickers: list[str]) -> None:
    """Add or overwrite a sector basket.

    Args:
        name: Sector name
        tickers: List of ticker symbols
    """
    SECTOR_BASKETS[name.lower()] = [t.upper() for t in tickers]


def remove_sector(name: str) -> bool:
    """Remove a sector basket.

    Returns:
        True if removed, False if not found
    """
    key = name.lower()
    if key in SECTOR_BASKETS:
        del SECTOR_BASKETS[key]
        return True
    return False


if __name__ == "__main__":
    print("Available sectors:")
    for sector in list_sectors():
        tickers = get_sector_tickers(sector) or []
        print(f"  {sector}: {', '.join(tickers)}")
