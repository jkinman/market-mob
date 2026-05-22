"""Tests for sector discovery module."""

import pytest

from analysis.sector.discovery import (
    SECTOR_BASKETS,
    get_sector_tickers,
    list_sectors,
    add_sector,
    remove_sector,
)


class TestSectorDiscovery:
    """Unit tests for sector discovery."""

    def test_sector_baskets_not_empty(self):
        """SECTOR_BASKETS should contain expected sectors."""
        expected_sectors = {
            "mining", "tech", "energy", "biotech",
            "semiconductors", "cannabis", "quantum",
        }
        assert set(SECTOR_BASKETS.keys()) == expected_sectors

    def test_mining_tickers(self):
        """Mining sector should have expected tickers."""
        tickers = get_sector_tickers("mining")
        assert tickers is not None
        assert "GOLD" in tickers
        assert "NEM" in tickers
        assert len(tickers) == 10

    def test_tech_tickers(self):
        """Tech sector should have expected tickers."""
        tickers = get_sector_tickers("tech")
        assert tickers is not None
        assert "AAPL" in tickers
        assert "NVDA" in tickers

    def test_case_insensitive_lookup(self):
        """Sector lookup should be case-insensitive."""
        assert get_sector_tickers("MINING") == get_sector_tickers("mining")
        assert get_sector_tickers("Tech") == get_sector_tickers("tech")

    def test_unknown_sector_returns_none(self):
        """Unknown sector should return None."""
        assert get_sector_tickers("aliens") is None

    def test_list_sectors(self):
        """list_sectors should return all keys."""
        sectors = list_sectors()
        assert isinstance(sectors, list)
        assert "mining" in sectors
        assert "cannabis" in sectors

    def test_add_sector(self):
        """add_sector should add a new sector."""
        add_sector("space", ["SPCE", "RKLB", "ASTS"])
        tickers = get_sector_tickers("space")
        assert tickers is not None
        assert "SPCE" in tickers
        assert "RKLB" in tickers
        # Clean up
        remove_sector("space")

    def test_add_sector_uppercases_tickers(self):
        """add_sector should normalize tickers to uppercase."""
        add_sector("test_sector", ["abc", "def"])
        tickers = get_sector_tickers("test_sector")
        assert tickers == ["ABC", "DEF"]
        remove_sector("test_sector")

    def test_remove_sector(self):
        """remove_sector should remove and return True."""
        add_sector("temp", ["TMP"])
        assert remove_sector("temp") is True
        assert get_sector_tickers("temp") is None

    def test_remove_unknown_sector(self):
        """remove_sector for unknown sector should return False."""
        assert remove_sector("nonexistent") is False
