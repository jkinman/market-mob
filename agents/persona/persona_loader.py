"""Investor persona loader and formatter.

Provides a structured way to load, validate, and format investor preferences
for injection into LLM prompts and report generation.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Position:
    """A single portfolio position."""

    ticker: str
    shares: float
    avg_cost: float


@dataclass
class Persona:
    """Investor persona — risk appetite, preferences, and current holdings."""

    name: str = "Default Investor"
    risk_tolerance: str = "moderate"  # conservative / moderate / aggressive
    time_horizon: str = "medium"  # short / medium / long
    preferred_sectors: list[str] = field(default_factory=list)
    avoid_sectors: list[str] = field(default_factory=list)
    current_positions: list[Position] = field(default_factory=list)
    max_position_size_pct: float = 10.0
    min_liquidity: float = 5.0
    notes: str = ""


def load_persona(path: str = "config/persona.json") -> Optional[Persona]:
    """Load investor persona from JSON config.

    Args:
        path: Path to persona JSON file.

    Returns:
        Persona dataclass or None if file does not exist or is invalid.
    """
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    positions = []
    for pos in data.get("current_positions", []):
        try:
            positions.append(
                Position(
                    ticker=pos.get("ticker", ""),
                    shares=float(pos.get("shares", 0)),
                    avg_cost=float(pos.get("avg_cost", 0.0)),
                )
            )
        except (ValueError, TypeError):
            continue

    return Persona(
        name=data.get("name", "Default Investor"),
        risk_tolerance=data.get("risk_tolerance", "moderate"),
        time_horizon=data.get("time_horizon", "medium"),
        preferred_sectors=data.get("preferred_sectors", []),
        avoid_sectors=data.get("avoid_sectors", []),
        current_positions=positions,
        max_position_size_pct=float(data.get("max_position_size_pct", 10.0)),
        min_liquidity=float(data.get("min_liquidity", 5.0)),
        notes=data.get("notes", ""),
    )


def format_persona_for_prompt(persona: Optional[Persona]) -> str:
    """Format persona context as a string snippet for LLM prompt injection.

    Args:
        persona: Investor persona (may be None).

    Returns:
        Formatted persona context string, or empty string if None.
    """
    if persona is None:
        return ""

    lines = [
        f"### Investor Profile",
        f"- Name: {persona.name}",
        f"- Risk Tolerance: {persona.risk_tolerance}",
        f"- Time Horizon: {persona.time_horizon}",
    ]

    if persona.preferred_sectors:
        lines.append(f"- Preferred Sectors: {', '.join(persona.preferred_sectors)}")
    if persona.avoid_sectors:
        lines.append(f"- Avoid Sectors: {', '.join(persona.avoid_sectors)}")

    lines.append(f"- Max Position Size: {persona.max_position_size_pct}% of portfolio")
    lines.append(f"- Min Liquidity: ${persona.min_liquidity}M avg daily volume")

    if persona.notes:
        lines.append(f"- Notes: {persona.notes}")

    return "\n".join(lines)


def get_position_for_ticker(persona: Optional[Persona], ticker: str) -> Optional[dict]:
    """Look up a specific position by ticker.

    Args:
        persona: Investor persona (may be None).
        ticker: Stock symbol to look up.

    Returns:
        Position dict with keys 'ticker', 'shares', 'avg_cost' or None.
    """
    if persona is None:
        return None

    for pos in persona.current_positions:
        if pos.ticker.upper() == ticker.upper():
            return {"ticker": pos.ticker, "shares": pos.shares, "avg_cost": pos.avg_cost}

    return None


def format_position_context(persona: Optional[Persona], ticker: str) -> str:
    """Format a position-specific context line for prompt injection.

    Args:
        persona: Investor persona (may be None).
        ticker: Stock symbol being analyzed.

    Returns:
        A sentence describing the position, or empty string if no position.
    """
    pos = get_position_for_ticker(persona, ticker)
    if pos is None:
        return ""

    return (
        f"User holds {pos['shares']} shares of {pos['ticker']} "
        f"at an average cost of ${pos['avg_cost']:.2f}."
    )
