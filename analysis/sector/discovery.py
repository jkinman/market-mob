"""Sector discovery module — reads from central config."""

from __future__ import annotations

from typing import Optional

from config.loader import get_config


def get_sector_tickers(sector_name: str) -> Optional[list[str]]:
    """Return ticker list for a given sector name (case-insensitive).

    Args:
        sector_name: Sector name (e.g., "mining", "Tech")

    Returns:
        List of tickers or None if sector not found
    """
    cfg = get_config()
    sector = cfg.get_sector(sector_name.lower())
    if sector:
        return sector.tickers
    return None


def list_sectors() -> list[str]:
    """Return all available sector names."""
    return get_config().list_sectors()


def add_sector(name: str, tickers: list[str], description: str = "") -> None:
    """Add or overwrite a sector basket in config.

    Args:
        name: Sector name
        tickers: List of ticker symbols
        description: Optional description
    """
    get_config().add_sector(name, tickers, description)


def remove_sector(name: str) -> bool:
    """Remove a sector basket from config.

    Returns:
        True if removed, False if not found
    """
    return get_config().remove_sector(name)


if __name__ == "__main__":
    print("Available sectors:")
    for sector in list_sectors():
        tickers = get_sector_tickers(sector) or []
        print(f"  {sector}: {', '.join(tickers)}")
