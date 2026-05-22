"""Alert Manager — price targets, stop losses, buy signals, trailing stops."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from config.loader import get_config


class AlertType(Enum):
    PRICE_TARGET = "price_target"      # Sell when price >= target
    STOP_LOSS = "stop_loss"            # Sell when price <= stop
    BUY_SIGNAL = "buy_signal"          # Buy when price <= entry
    TRAILING_STOP = "trailing_stop"    # Stop moves up with price


class AlertStatus(Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class Alert:
    id: str
    ticker: str
    alert_type: AlertType
    price: float
    shares: Optional[float] = None       # How many shares to act on
    action: str = "notify"               # notify, trim, sell, buy
    message: str = ""                     # Custom message
    created_at: str = ""
    triggered_at: Optional[str] = None
    status: AlertStatus = AlertStatus.ACTIVE
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticker": self.ticker.upper(),
            "alert_type": self.alert_type.value,
            "price": self.price,
            "shares": self.shares,
            "action": self.action,
            "message": self.message,
            "created_at": self.created_at or datetime.now().isoformat(),
            "triggered_at": self.triggered_at,
            "status": self.status.value,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Alert":
        return cls(
            id=d["id"],
            ticker=d["ticker"],
            alert_type=AlertType(d["alert_type"]),
            price=d["price"],
            shares=d.get("shares"),
            action=d.get("action", "notify"),
            message=d.get("message", ""),
            created_at=d.get("created_at", ""),
            triggered_at=d.get("triggered_at"),
            status=AlertStatus(d.get("status", "active")),
            notes=d.get("notes", ""),
        )


class AlertManager:
    """Manage price alerts and trading signals."""

    def __init__(self):
        self.cfg = get_config()
        self._alerts: list[Alert] = []
        self._load()

    def _load(self) -> None:
        """Load alerts from config."""
        raw = self.cfg.get("alerts", [])
        if isinstance(raw, list):
            self._alerts = [Alert.from_dict(a) for a in raw]
        elif isinstance(raw, dict):
            # Flatten all alert types
            all_raw = []
            for category in ["price_targets", "stop_losses", "buy_signals", "trailing_stops"]:
                all_raw.extend(raw.get(category, []))
            self._alerts = [Alert.from_dict(a) for a in all_raw]

    def _save(self) -> None:
        """Save alerts to config."""
        alerts_dict = {
            "price_targets": [],
            "stop_losses": [],
            "buy_signals": [],
            "trailing_stops": [],
        }
        for alert in self._alerts:
            key = alert.alert_type.value + "s"
            if key in alerts_dict:
                alerts_dict[key].append(alert.to_dict())
            else:
                alerts_dict["price_targets"].append(alert.to_dict())
        self.cfg.set("alerts", alerts_dict)

    def add_alert(
        self,
        ticker: str,
        alert_type: AlertType,
        price: float,
        shares: Optional[float] = None,
        action: str = "notify",
        message: str = "",
        notes: str = "",
    ) -> Alert:
        """Add a new alert."""
        alert = Alert(
            id=f"{ticker.upper()}_{alert_type.value}_{int(price * 100)}",
            ticker=ticker,
            alert_type=alert_type,
            price=price,
            shares=shares,
            action=action,
            message=message,
            created_at=datetime.now().isoformat(),
            status=AlertStatus.ACTIVE,
            notes=notes,
        )
        self._alerts.append(alert)
        self._save()
        return alert

    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert by ID."""
        for i, alert in enumerate(self._alerts):
            if alert.id == alert_id:
                self._alerts.pop(i)
                self._save()
                return True
        return False

    def get_active(self, ticker: Optional[str] = None) -> list[Alert]:
        """Get active alerts, optionally filtered by ticker."""
        active = [a for a in self._alerts if a.status == AlertStatus.ACTIVE]
        if ticker:
            active = [a for a in active if a.ticker.upper() == ticker.upper()]
        return active

    def get_all(self) -> list[Alert]:
        """Get all alerts."""
        return self._alerts

    def check_alerts(self, ticker: str, current_price: float) -> list[Alert]:
        """Check which alerts are triggered for a ticker at current price."""
        triggered = []
        for alert in self._alerts:
            if alert.status != AlertStatus.ACTIVE:
                continue
            if alert.ticker.upper() != ticker.upper():
                continue

            if alert.alert_type == AlertType.PRICE_TARGET and current_price >= alert.price:
                triggered.append(alert)
            elif alert.alert_type == AlertType.STOP_LOSS and current_price <= alert.price:
                triggered.append(alert)
            elif alert.alert_type == AlertType.BUY_SIGNAL and current_price <= alert.price:
                triggered.append(alert)
            elif alert.alert_type == AlertType.TRAILING_STOP:
                # Trailing stop logic: if price drops X% from peak since alert creation
                # For now, treat as hard stop at the price level
                if current_price <= alert.price:
                    triggered.append(alert)

        # Mark triggered
        for alert in triggered:
            alert.status = AlertStatus.TRIGGERED
            alert.triggered_at = datetime.now().isoformat()

        if triggered:
            self._save()

        return triggered

    def format_alert(self, alert: Alert, current_price: float) -> str:
        """Format a single alert for display."""
        emoji = {
            AlertType.PRICE_TARGET: "🎯",
            AlertType.STOP_LOSS: "🛑",
            AlertType.BUY_SIGNAL: "💰",
            AlertType.TRAILING_STOP: "📉",
        }.get(alert.alert_type, "📢")

        action_emoji = {
            "notify": "🔔",
            "trim": "✂️",
            "sell": "💸",
            "buy": "🛒",
        }.get(alert.action, "🔔")

        pct = ((current_price - alert.price) / alert.price) * 100
        pct_str = f"({pct:+.1f}%)" if alert.alert_type != AlertType.BUY_SIGNAL else f"({abs(pct):.1f}% away)"

        lines = [
            f"{emoji} {action_emoji} **{alert.ticker}** — {alert.alert_type.value.replace('_', ' ').title()}",
            f"   Target: ${alert.price:.2f} | Current: ${current_price:.2f} {pct_str}",
        ]
        if alert.shares:
            lines.append(f"   Shares: {alert.shares}")
        if alert.message:
            lines.append(f"   Note: {alert.message}")
        if alert.notes:
            lines.append(f"   Strategy: {alert.notes}")
        lines.append(f"   Status: {alert.status.value}")
        return "\n".join(lines)

    def format_all_active(self, prices: dict[str, float]) -> str:
        """Format all active alerts with current prices."""
        lines = ["🚨 ACTIVE ALERTS", ""]

        by_type: dict[AlertType, list[Alert]] = {t: [] for t in AlertType}
        for alert in self._alerts:
            if alert.status == AlertStatus.ACTIVE:
                by_type[alert.alert_type].append(alert)

        for alert_type, alerts in by_type.items():
            if not alerts:
                continue
            lines.append(f"\n{alert_type.value.replace('_', ' ').title()}s:")
            for alert in alerts:
                price = prices.get(alert.ticker.upper(), 0)
                lines.append(self.format_alert(alert, price))
                lines.append("")

        if len(lines) == 2:
            lines.append("No active alerts.")

        return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    mgr = AlertManager()
    mgr.add_alert("NVDA", AlertType.PRICE_TARGET, 235.0, shares=2, action="trim", message="Trim 50% at upper BB", notes="RSI was 57, MACD flat. Take profits before momentum fades.")
    mgr.add_alert("TSLA", AlertType.PRICE_TARGET, 455.0, shares=0.5, action="trim", message="Trim half at upper BB")
    mgr.add_alert("MSTR", AlertType.STOP_LOSS, 150.0, shares=10, action="sell", message="Hard stop at SMA50")
    mgr.add_alert("SHOP", AlertType.STOP_LOSS, 88.0, shares=2, action="sell", message="Lower BB breakdown")
    mgr.add_alert("RGTI", AlertType.BUY_SIGNAL, 18.0, action="buy", message="Wait for pullback to SMA20")

    print(mgr.format_all_active({"NVDA": 219.51, "TSLA": 417.85, "MSTR": 164.85, "SHOP": 104.86, "RGTI": 22.04}))
