"""Track and score prediction accuracy over time.

Stores predictions when made, then scores them against actual outcomes.
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, List

import yfinance as yf


@dataclass
class Prediction:
    """A single prediction record."""

    ticker: str
    predicted_at: str  # ISO timestamp
    prediction_7d: str  # e.g. "up 5%"
    prediction_30d: str  # e.g. "up 10%"
    confidence: str  # high/medium/low
    source: str  # analyst name, youtube channel, etc.
    price_at_prediction: float

    # Filled in later when scoring
    actual_7d: Optional[float] = None
    actual_30d: Optional[float] = None
    scored_7d_at: Optional[str] = None
    scored_30d_at: Optional[str] = None
    accuracy_7d: Optional[str] = None  # correct/directionally_correct/wrong
    accuracy_30d: Optional[str] = None


class AccuracyTracker:
    """Tracks prediction accuracy over time."""

    def __init__(self, storage_path: str = "data/predictions.json"):
        self.storage_path = storage_path
        self.predictions: List[Prediction] = []
        self._load()

    def _load(self) -> None:
        """Load predictions from disk."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self.predictions = [Prediction(**p) for p in data]
            except (json.JSONDecodeError, IOError):
                self.predictions = []

    def _save(self) -> None:
        """Save predictions to disk."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump([asdict(p) for p in self.predictions], f, indent=2)

    def record_prediction(
        self,
        ticker: str,
        prediction_7d: str,
        prediction_30d: str,
        confidence: str,
        source: str,
        price_at_prediction: float,
    ) -> Prediction:
        """Record a new prediction.

        Returns:
            The created Prediction object
        """
        pred = Prediction(
            ticker=ticker,
            predicted_at=datetime.now().isoformat(),
            prediction_7d=prediction_7d,
            prediction_30d=prediction_30d,
            confidence=confidence,
            source=source,
            price_at_prediction=price_at_prediction,
        )
        self.predictions.append(pred)
        self._save()
        return pred

    def _get_price_on_date(self, ticker: str, date: datetime) -> Optional[float]:
        """Get closing price for ticker on a specific date."""
        try:
            stock = yf.Ticker(ticker)
            # Get a few days around the target to handle weekends/holidays
            start = (date - timedelta(days=3)).strftime("%Y-%m-%d")
            end = (date + timedelta(days=1)).strftime("%Y-%m-%d")
            hist = stock.history(start=start, end=end)

            if hist.empty:
                return None

            # Find closest date
            target_str = date.strftime("%Y-%m-%d")
            for idx in hist.index:
                if idx.strftime("%Y-%m-%d") == target_str:
                    return float(hist.loc[idx, "Close"])

            # Fallback: return last available
            return float(hist["Close"].iloc[-1])

        except Exception as e:
            print(f"[ERROR] Failed to fetch price for {ticker} on {date}: {e}")
            return None

    def _parse_prediction(self, prediction_str: str) -> tuple[str, float]:
        """Parse prediction string into direction and magnitude.

        Returns:
            (direction, percent) where direction is "up", "down", or "flat"
        """
        import re

        pred_lower = prediction_str.lower().strip()

        if "flat" in pred_lower or "neutral" in pred_lower or "sideways" in pred_lower:
            return ("flat", 0.0)

        # Extract number and direction
        match = re.search(r'(up|down)\s*(\d+(?:\.\d+)?)', pred_lower)
        if match:
            direction = match.group(1)
            percent = float(match.group(2))
            return (direction, percent)

        # Just direction, no number
        if "up" in pred_lower:
            return ("up", 1.0)  # Default 1%
        if "down" in pred_lower:
            return ("down", 1.0)

        return ("flat", 0.0)

    def _score_prediction(
        self,
        predicted: str,
        price_at_prediction: float,
        price_actual: float,
    ) -> str:
        """Score a single prediction.

        Returns:
            "correct" | "directionally_correct" | "wrong"
        """
        if price_actual is None or price_at_prediction is None:
            return "wrong"

        direction, _ = self._parse_prediction(predicted)
        actual_change = (price_actual - price_at_prediction) / price_at_prediction

        if direction == "flat":
            # Within 2% is "flat"
            if abs(actual_change) <= 0.02:
                return "correct"
            return "wrong"

        predicted_up = direction == "up"
        actual_up = actual_change > 0.02  # More than 2% up
        actual_down = actual_change < -0.02  # More than 2% down

        if predicted_up and actual_up:
            return "correct"
        if not predicted_up and actual_down:
            return "correct"

        # Directionally correct but magnitude wrong
        if predicted_up and actual_change > 0:
            return "directionally_correct"
        if not predicted_up and actual_change < 0:
            return "directionally_correct"

        return "wrong"

    def score_pending_predictions(self) -> dict:
        """Score all predictions that are due for scoring.

        Returns:
            Summary dict with counts
        """
        now = datetime.now()
        scored_count = {"7d": 0, "30d": 0}

        for pred in self.predictions:
            predicted_at = datetime.fromisoformat(pred.predicted_at)

            # Score 7-day prediction
            if pred.accuracy_7d is None:
                target_date = predicted_at + timedelta(days=7)
                if now >= target_date:
                    price = self._get_price_on_date(pred.ticker, target_date)
                    if price is not None:
                        pred.actual_7d = price
                        pred.accuracy_7d = self._score_prediction(
                            pred.prediction_7d,
                            pred.price_at_prediction,
                            price,
                        )
                        pred.scored_7d_at = now.isoformat()
                        scored_count["7d"] += 1

            # Score 30-day prediction
            if pred.accuracy_30d is None:
                target_date = predicted_at + timedelta(days=30)
                if now >= target_date:
                    price = self._get_price_on_date(pred.ticker, target_date)
                    if price is not None:
                        pred.actual_30d = price
                        pred.accuracy_30d = self._score_prediction(
                            pred.prediction_30d,
                            pred.price_at_prediction,
                            price,
                        )
                        pred.scored_30d_at = now.isoformat()
                        scored_count["30d"] += 1

        if scored_count["7d"] > 0 or scored_count["30d"] > 0:
            self._save()

        return scored_count

    def get_accuracy_stats(self) -> dict:
        """Get overall accuracy statistics.

        Returns:
            Dict with accuracy breakdowns
        """
        stats = {
            "total_predictions": len(self.predictions),
            "scored_7d": 0,
            "scored_30d": 0,
            "accuracy_7d": {"correct": 0, "directionally_correct": 0, "wrong": 0},
            "accuracy_30d": {"correct": 0, "directionally_correct": 0, "wrong": 0},
            "by_confidence": {
                "high": {"correct": 0, "total": 0},
                "medium": {"correct": 0, "total": 0},
                "low": {"correct": 0, "total": 0},
            },
            "by_source": {},
        }

        for pred in self.predictions:
            if pred.accuracy_7d:
                stats["scored_7d"] += 1
                stats["accuracy_7d"][pred.accuracy_7d] += 1

                conf = pred.confidence or "medium"
                stats["by_confidence"][conf]["total"] += 1
                if pred.accuracy_7d == "correct":
                    stats["by_confidence"][conf]["correct"] += 1

                src = pred.source or "unknown"
                if src not in stats["by_source"]:
                    stats["by_source"][src] = {"correct": 0, "total": 0}
                stats["by_source"][src]["total"] += 1
                if pred.accuracy_7d == "correct":
                    stats["by_source"][src]["correct"] += 1

            if pred.accuracy_30d:
                stats["scored_30d"] += 1
                stats["accuracy_30d"][pred.accuracy_30d] += 1

        # Calculate percentages
        for timeframe in ["7d", "30d"]:
            total = stats[f"scored_{timeframe}"]
            if total > 0:
                correct = stats[f"accuracy_{timeframe}"]["correct"]
                stats[f"accuracy_{timeframe}"]["pct_correct"] = round(correct / total * 100, 1)

        return stats


if __name__ == "__main__":
    tracker = AccuracyTracker()

    # Score any pending predictions
    scored = tracker.score_pending_predictions()
    print(f"Scored: {scored}")

    # Show stats
    stats = tracker.get_accuracy_stats()
    print(f"\nAccuracy Stats:")
    print(json.dumps(stats, indent=2))
