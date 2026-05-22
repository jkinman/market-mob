"""Alert Scanner — check all alerts against live prices and trigger notifications."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from analysis.technical.fetch_prices import fetch_prices
from analysis.technical.indicators import compute_all, summarize_latest
from alerts.alert_manager import AlertManager, Alert, AlertType, AlertStatus
from config.loader import get_config


class AlertScanner:
    """Scan all active alerts against live prices and report triggers."""

    def __init__(self):
        self.mgr = AlertManager()
        self.cfg = get_config()

    def scan_all(self) -> tuple[list[Alert], dict[str, float]]:
        """Check all active alerts. Returns (triggered_alerts, current_prices)."""
        active = self.mgr.get_active()
        if not active:
            return [], {}

        # Get unique tickers
        tickers = list(set(a.ticker.upper() for a in active))

        # Fetch prices
        prices = {}
        for ticker in tickers:
            try:
                pd = fetch_prices(ticker, period="5d")
                if pd and not pd.df.empty:
                    prices[ticker] = float(pd.df["Close"].iloc[-1])
            except Exception as e:
                print(f"[WARN] Could not fetch price for {ticker}: {e}")

        # Check alerts
        triggered = []
        for ticker in tickers:
            price = prices.get(ticker)
            if price is None:
                continue
            hits = self.mgr.check_alerts(ticker, price)
            triggered.extend(hits)

        return triggered, prices

    def format_triggered(self, triggered: list[Alert], prices: dict[str, float]) -> str:
        """Format triggered alerts for delivery."""
        if not triggered:
            return ""

        lines = [
            "🔥 ALERTS TRIGGERED",
            "",
            f"Scan time: {datetime.now().strftime('%Y-%m-%d %H:%M %Z')}",
            "",
        ]

        for alert in triggered:
            price = prices.get(alert.ticker.upper(), 0)
            lines.append(self.mgr.format_alert(alert, price))
            lines.append("")

        return "\n".join(lines)

    def format_status(self, prices: dict[str, float]) -> str:
        """Format all active alerts with current status."""
        return self.mgr.format_all_active(prices)

    def run(self, output_format: str = "triggered") -> str:
        """Run the scan and return formatted output.

        Args:
            output_format: "triggered" (only fired), "status" (all active), "both"
        """
        triggered, prices = self.scan_all()

        if output_format == "triggered":
            return self.format_triggered(triggered, prices)
        elif output_format == "status":
            return self.format_status(prices)
        else:
            status = self.format_status(prices)
            fired = self.format_triggered(triggered, prices)
            if fired:
                return fired + "\n" + "=" * 50 + "\n\n" + status
            return status


def seed_alerts_from_analysis() -> None:
    """Seed alerts based on the exit strategy analysis we did earlier."""
    mgr = AlertManager()

    # Clear existing
    for alert in mgr.get_all():
        mgr.remove_alert(alert.id)

    # NVDA — trim 50% at $235
    mgr.add_alert(
        "NVDA", AlertType.PRICE_TARGET, 235.0,
        shares=2, action="trim",
        message="Trim 50% at upper BB",
        notes="RSI 57, MACD flat. Take profits before momentum fades."
    )
    # NVDA — stop at $193
    mgr.add_alert(
        "NVDA", AlertType.STOP_LOSS, 193.0,
        shares=4, action="sell",
        message="Hard stop at lower BB",
        notes="Break below lower Bollinger = trend reversal. Exit full position."
    )

    # TSLA — trim 50% at $455
    mgr.add_alert(
        "TSLA", AlertType.PRICE_TARGET, 455.0,
        shares=0.5, action="trim",
        message="Trim half at upper BB",
        notes="Up 31% from cost. Don't give back gains."
    )
    # TSLA — full exit at $387
    mgr.add_alert(
        "TSLA", AlertType.STOP_LOSS, 387.0,
        shares=1, action="sell",
        message="Full exit below SMA50",
        notes="Momentum name. SMA50 break = trend change."
    )

    # XOM — hold, no trim target. Stop at $142
    mgr.add_alert(
        "XOM", AlertType.STOP_LOSS, 142.0,
        shares=10, action="sell",
        message="Stop at lower BB",
        notes="Energy dividend play. Only exit on major breakdown."
    )

    # MSTR — stop at $150
    mgr.add_alert(
        "MSTR", AlertType.STOP_LOSS, 150.0,
        shares=10, action="sell",
        message="Hard stop at SMA50",
        notes="Bitcoin proxy. If BTC breaks down, MSTR accelerates lower."
    )
    # MSTR — reclaim $176 = hold signal (no action, just notify)
    mgr.add_alert(
        "MSTR", AlertType.PRICE_TARGET, 176.0,
        action="notify",
        message="Reclaimed SMA20 — trend intact",
        notes="If hits this, cancel stop and raise to breakeven $185."
    )

    # GBTC — stop at $55
    mgr.add_alert(
        "GBTC", AlertType.STOP_LOSS, 55.0,
        shares=35, action="sell",
        message="Hard stop — dead position until BTC moves",
        notes="Consider tax-loss harvesting if stopped."
    )

    # HURA — hold for uranium cycle
    mgr.add_alert(
        "HURA", AlertType.STOP_LOSS, 2.08,
        shares=3, action="sell",
        message="Stop at lower BB",
        notes="Long-term commodity play. Only exit on structural breakdown."
    )

    # SHOP — already queued for sale, but add alert anyway
    mgr.add_alert(
        "SHOP", AlertType.STOP_LOSS, 88.0,
        shares=2, action="sell",
        message="Lower BB breakdown",
        notes="You already queued the sale. This is backup."
    )

    # WATCHLIST BUY SIGNALS
    # RGTI — wait for pullback to $18
    mgr.add_alert(
        "RGTI", AlertType.BUY_SIGNAL, 18.0,
        action="buy",
        message="Wait for pullback to SMA20",
        notes="Currently extended at $22. RSI 63. Don't chase."
    )

    # IONQ — wait for pullback to $49.60
    mgr.add_alert(
        "IONQ", AlertType.BUY_SIGNAL, 49.60,
        action="buy",
        message="Wait for pullback to SMA20",
        notes="Extended at $58.89. RSI 65. Patience."
    )

    # QBTS — wait for pullback to $20.90
    mgr.add_alert(
        "QBTS", AlertType.BUY_SIGNAL, 20.90,
        action="buy",
        message="Wait for pullback to SMA20",
        notes="Extended at $25.74. RSI 64. Wait."
    )

    print(f"[AlertScanner] Seeded {len(mgr.get_active())} alerts")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        seed_alerts_from_analysis()
    else:
        scanner = AlertScanner()
        print(scanner.run(output_format="both"))
