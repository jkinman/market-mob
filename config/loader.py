"""Central config loader — single source of truth for Market Mob."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_mob.json")


@dataclass
class SectorConfig:
    tickers: list[str]
    description: str


@dataclass
class WatchlistEntry:
    ticker: str
    added_date: str
    source: str
    status: str
    notes: str


@dataclass
class PortfolioHolding:
    ticker: str
    shares: float
    avg_cost: float
    account: str


@dataclass
class PersonaConfig:
    name: str
    risk_tolerance: str
    time_horizon: str
    preferred_sectors: list[str]
    avoid_sectors: list[str]
    max_position_size_pct: float
    min_liquidity: float
    notes: str


@dataclass
class NewsSource:
    name: str
    url: str
    enabled: bool


@dataclass
class NewsConfig:
    rss_feeds: list[NewsSource]
    newsapi_key: str
    newsapi_enabled: bool


@dataclass
class SettingsConfig:
    timezone: str
    market_open: str
    market_close: str
    daily_briefing_time: str
    mob_intel_enabled: bool
    mob_intel_schedule: str
    output_dir: str
    data_dir: str


class MarketMobConfig:
    """Central configuration — everything reads from here."""

    _instance: Optional["MarketMobConfig"] = None
    _data: dict[str, Any]

    def __new__(cls) -> "MarketMobConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """Load config from disk."""
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def save(self) -> None:
        """Persist config to disk."""
        with open(CONFIG_PATH, "w") as f:
            json.dump(self._data, f, indent=2)

    def reload(self) -> None:
        """Reload from disk."""
        self._load()

    # ── Sectors ───────────────────────────────────────────────

    @property
    def sectors(self) -> dict[str, SectorConfig]:
        return {
            name: SectorConfig(tickers=s["tickers"], description=s.get("description", ""))
            for name, s in self._data.get("sectors", {}).items()
        }

    def get_sector(self, name: str) -> Optional[SectorConfig]:
        s = self._data.get("sectors", {}).get(name.lower())
        if s:
            return SectorConfig(tickers=s["tickers"], description=s.get("description", ""))
        return None

    def add_sector(self, name: str, tickers: list[str], description: str = "") -> None:
        self._data.setdefault("sectors", {})[name.lower()] = {
            "tickers": [t.upper() for t in tickers],
            "description": description,
        }
        self.save()

    def remove_sector(self, name: str) -> bool:
        key = name.lower()
        if key in self._data.get("sectors", {}):
            del self._data["sectors"][key]
            self.save()
            return True
        return False

    def list_sectors(self) -> list[str]:
        return list(self._data.get("sectors", {}).keys())

    # ── Watchlist ─────────────────────────────────────────────

    @property
    def watchlist(self) -> list[WatchlistEntry]:
        return [
            WatchlistEntry(
                ticker=w["ticker"],
                added_date=w.get("added_date", ""),
                source=w.get("source", ""),
                status=w.get("status", "active"),
                notes=w.get("notes", ""),
            )
            for w in self._data.get("watchlist", [])
        ]

    def add_to_watchlist(self, ticker: str, source: str = "manual", notes: str = "") -> None:
        from datetime import datetime
        entries = self._data.setdefault("watchlist", [])
        # Prevent duplicates
        if not any(e["ticker"] == ticker.upper() for e in entries):
            entries.append({
                "ticker": ticker.upper(),
                "added_date": datetime.now().strftime("%Y-%m-%d"),
                "source": source,
                "status": "active",
                "notes": notes,
            })
            self.save()

    def remove_from_watchlist(self, ticker: str) -> bool:
        entries = self._data.get("watchlist", [])
        for i, e in enumerate(entries):
            if e["ticker"] == ticker.upper():
                del entries[i]
                self.save()
                return True
        return False

    def get_active_watchlist_tickers(self) -> list[str]:
        return [
            w["ticker"]
            for w in self._data.get("watchlist", [])
            if w.get("status") == "active"
        ]

    # ── Portfolio ─────────────────────────────────────────────

    @property
    def portfolio(self) -> list[PortfolioHolding]:
        return [
            PortfolioHolding(
                ticker=p["ticker"],
                shares=p.get("shares", 0),
                avg_cost=p.get("avg_cost", 0.0),
                account=p.get("account", ""),
            )
            for p in self._data.get("portfolio", {}).get("holdings", [])
        ]

    def add_holding(self, ticker: str, shares: float, avg_cost: float, account: str = "TFSA") -> None:
        holdings = self._data.setdefault("portfolio", {}).setdefault("holdings", [])
        for h in holdings:
            if h["ticker"] == ticker.upper():
                h["shares"] = shares
                h["avg_cost"] = avg_cost
                h["account"] = account
                self.save()
                return
        holdings.append({
            "ticker": ticker.upper(),
            "shares": shares,
            "avg_cost": avg_cost,
            "account": account,
        })
        self.save()

    def remove_holding(self, ticker: str) -> bool:
        holdings = self._data.get("portfolio", {}).get("holdings", [])
        for i, h in enumerate(holdings):
            if h["ticker"] == ticker.upper():
                del holdings[i]
                self.save()
                return True
        return False

    def get_portfolio_tickers(self) -> list[str]:
        return [p["ticker"] for p in self._data.get("portfolio", {}).get("holdings", [])]

    # ── Persona ───────────────────────────────────────────────

    @property
    def persona(self) -> Optional[PersonaConfig]:
        p = self._data.get("persona")
        if not p:
            return None
        return PersonaConfig(
            name=p.get("name", "Default"),
            risk_tolerance=p.get("risk_tolerance", "moderate"),
            time_horizon=p.get("time_horizon", "medium"),
            preferred_sectors=p.get("preferred_sectors", []),
            avoid_sectors=p.get("avoid_sectors", []),
            max_position_size_pct=p.get("max_position_size_pct", 10.0),
            min_liquidity=p.get("min_liquidity", 5.0),
            notes=p.get("notes", ""),
        )

    # ── News Sources ──────────────────────────────────────────

    @property
    def news(self) -> NewsConfig:
        n = self._data.get("news_sources", {})
        return NewsConfig(
            rss_feeds=[
                NewsSource(name=f["name"], url=f["url"], enabled=f.get("enabled", True))
                for f in n.get("rss_feeds", [])
            ],
            newsapi_key=n.get("newsapi_key", ""),
            newsapi_enabled=n.get("newsapi_enabled", False),
        )

    # ── Settings ──────────────────────────────────────────────

    @property
    def settings(self) -> SettingsConfig:
        s = self._data.get("settings", {})
        return SettingsConfig(
            timezone=s.get("timezone", "America/Vancouver"),
            market_open=s.get("market_open", "06:30"),
            market_close=s.get("market_close", "13:00"),
            daily_briefing_time=s.get("daily_briefing_time", "07:00"),
            mob_intel_enabled=s.get("mob_intel_enabled", True),
            mob_intel_schedule=s.get("mob_intel_schedule", "0 7 * * *"),
            output_dir=s.get("output_dir", "output/obsidian"),
            data_dir=s.get("data_dir", "data"),
        )

    # ── Raw Access ────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Dot-notation access: config.get('persona.name')"""
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
                if val is None:
                    return default
            else:
                return default
        return val

    def set(self, key: str, value: Any) -> None:
        """Dot-notation set: config.set('persona.name', 'Joel')"""
        keys = key.split(".")
        target = self._data
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value
        self.save()


# Singleton accessor
_config: Optional[MarketMobConfig] = None


def get_config() -> MarketMobConfig:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = MarketMobConfig()
    return _config


def reload_config() -> MarketMobConfig:
    """Force reload from disk."""
    global _config
    _config = MarketMobConfig()
    _config.reload()
    return _config


if __name__ == "__main__":
    cfg = get_config()
    print("Sectors:", cfg.list_sectors())
    print("Watchlist:", cfg.get_active_watchlist_tickers())
    print("Portfolio:", cfg.get_portfolio_tickers())
    print("Persona:", cfg.persona.name if cfg.persona else "None")
    print("News feeds:", len(cfg.news.rss_feeds))
