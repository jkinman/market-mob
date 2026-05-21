"""Tests for accuracy tracker."""

import json
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from analysis.accuracy_tracker import (
    AccuracyTracker,
    Prediction,
)


class TestParsePrediction:
    """Tests for prediction string parsing."""

    def test_parse_up_percent(self):
        """Should parse 'up 5%'."""
        tracker = AccuracyTracker(storage_path="/dev/null")
        direction, pct = tracker._parse_prediction("up 5%")
        assert direction == "up"
        assert pct == 5.0

    def test_parse_down_percent(self):
        """Should parse 'down 10%'."""
        tracker = AccuracyTracker(storage_path="/dev/null")
        direction, pct = tracker._parse_prediction("down 10%")
        assert direction == "down"
        assert pct == 10.0

    def test_parse_flat(self):
        """Should parse flat."""
        tracker = AccuracyTracker(storage_path="/dev/null")
        direction, pct = tracker._parse_prediction("flat")
        assert direction == "flat"
        assert pct == 0.0

    def test_parse_direction_only(self):
        """Should handle direction without number."""
        tracker = AccuracyTracker(storage_path="/dev/null")
        direction, pct = tracker._parse_prediction("up")
        assert direction == "up"
        assert pct == 1.0


class TestScorePrediction:
    """Tests for prediction scoring."""

    def test_correct_up(self):
        """Should score correct for up prediction when price rises."""
        tracker = AccuracyTracker(storage_path="/dev/null")
        result = tracker._score_prediction("up 5%", 100.0, 110.0)
        assert result == "correct"

    def test_correct_down(self):
        """Should score correct for down prediction when price falls."""
        tracker = AccuracyTracker(storage_path="/dev/null")
        result = tracker._score_prediction("down 5%", 100.0, 90.0)
        assert result == "correct"

    def test_directionally_correct(self):
        """Should score directionally correct when direction matches but magnitude off."""
        tracker = AccuracyTracker(storage_path="/dev/null")
        result = tracker._score_prediction("up 20%", 100.0, 101.0)
        assert result == "directionally_correct"

    def test_wrong(self):
        """Should score wrong when direction is opposite."""
        tracker = AccuracyTracker(storage_path="/dev/null")
        result = tracker._score_prediction("up 5%", 100.0, 90.0)
        assert result == "wrong"

    def test_flat_correct(self):
        """Should score flat correct when price barely moves."""
        tracker = AccuracyTracker(storage_path="/dev/null")
        result = tracker._score_prediction("flat", 100.0, 101.0)
        assert result == "correct"

    def test_flat_wrong(self):
        """Should score flat wrong when price moves significantly."""
        tracker = AccuracyTracker(storage_path="/dev/null")
        result = tracker._score_prediction("flat", 100.0, 110.0)
        assert result == "wrong"


class TestAccuracyTracker:
    """Tests for tracker functionality."""

    def test_record_prediction(self, tmp_path):
        """Should record and save prediction."""
        path = str(tmp_path / "predictions.json")
        tracker = AccuracyTracker(storage_path=path)

        pred = tracker.record_prediction(
            ticker="AAPL",
            prediction_7d="up 5%",
            prediction_30d="up 10%",
            confidence="high",
            source="test",
            price_at_prediction=150.0,
        )

        assert pred.ticker == "AAPL"
        assert pred.confidence == "high"
        assert os.path.exists(path)

    def test_load_existing(self, tmp_path):
        """Should load existing predictions."""
        path = str(tmp_path / "predictions.json")
        data = [{
            "ticker": "TSLA",
            "predicted_at": datetime.now().isoformat(),
            "prediction_7d": "up 5%",
            "prediction_30d": "up 10%",
            "confidence": "medium",
            "source": "test",
            "price_at_prediction": 200.0,
        }]
        with open(path, "w") as f:
            json.dump(data, f)

        tracker = AccuracyTracker(storage_path=path)
        assert len(tracker.predictions) == 1
        assert tracker.predictions[0].ticker == "TSLA"

    @patch("analysis.accuracy_tracker.yf.Ticker")
    def test_score_pending(self, mock_ticker_class, tmp_path):
        """Should score predictions that are due."""
        path = str(tmp_path / "predictions.json")
        tracker = AccuracyTracker(storage_path=path)

        # Record old prediction (8 days ago)
        old_date = (datetime.now() - timedelta(days=8)).isoformat()
        tracker.predictions.append(Prediction(
            ticker="AAPL",
            predicted_at=old_date,
            prediction_7d="up 5%",
            prediction_30d="up 10%",
            confidence="high",
            source="test",
            price_at_prediction=100.0,
        ))
        tracker._save()

        # Mock price fetch — return a proper DataFrame-like object
        import pandas as pd
        target_date = datetime.now() - timedelta(days=1)
        dates = pd.date_range(target_date - timedelta(days=2), target_date + timedelta(days=1))
        mock_hist = pd.DataFrame({
            "Close": [100.0, 105.0, 110.0, 108.0]
        }, index=dates)

        mock_stock = MagicMock()
        mock_stock.history.return_value = mock_hist
        mock_ticker_class.return_value = mock_stock

        scored = tracker.score_pending_predictions()
        assert scored["7d"] == 1

    def test_get_stats_empty(self, tmp_path):
        """Should handle empty predictions."""
        path = str(tmp_path / "predictions.json")
        tracker = AccuracyTracker(storage_path=path)

        stats = tracker.get_accuracy_stats()
        assert stats["total_predictions"] == 0
        assert stats["scored_7d"] == 0

    def test_get_stats_with_data(self, tmp_path):
        """Should calculate accuracy stats."""
        path = str(tmp_path / "predictions.json")
        tracker = AccuracyTracker(storage_path=path)

        tracker.predictions = [
            Prediction(
                ticker="AAPL",
                predicted_at=datetime.now().isoformat(),
                prediction_7d="up 5%",
                prediction_30d="up 10%",
                confidence="high",
                source="test",
                price_at_prediction=100.0,
                accuracy_7d="correct",
            ),
            Prediction(
                ticker="TSLA",
                predicted_at=datetime.now().isoformat(),
                prediction_7d="down 5%",
                prediction_30d="down 10%",
                confidence="medium",
                source="test",
                price_at_prediction=200.0,
                accuracy_7d="wrong",
            ),
        ]

        stats = tracker.get_accuracy_stats()
        assert stats["total_predictions"] == 2
        assert stats["scored_7d"] == 2
        assert stats["accuracy_7d"]["correct"] == 1
        assert stats["accuracy_7d"]["wrong"] == 1
        assert stats["accuracy_7d"]["pct_correct"] == 50.0
