"""Tests for suspicious move detector module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analysis.technical.fetch_prices import PriceData
from analysis.technical.suspicious_moves import (
    calculate_daily_change,
    volume_vs_average,
    check_news_catalyst,
    detect_suspicious_move,
    scan_tickers,
    SuspiciousMove,
)


class TestCalculateDailyChange:
    """Tests for daily change calculation."""

    def test_normal_change(self):
        """Test basic daily % change calculation."""
        df = pd.DataFrame({
            "Close": [100.0, 110.0],
            "Volume": [1_000_000, 1_200_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = calculate_daily_change(pdata)
        assert result == 10.0

    def test_negative_change(self):
        """Test negative daily % change."""
        df = pd.DataFrame({
            "Close": [100.0, 90.0],
            "Volume": [1_000_000, 1_200_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = calculate_daily_change(pdata)
        assert result == -10.0

    def test_no_change(self):
        """Test zero change."""
        df = pd.DataFrame({
            "Close": [100.0, 100.0],
            "Volume": [1_000_000, 1_000_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = calculate_daily_change(pdata)
        assert result == 0.0

    def test_insufficient_data(self):
        """Test with only one row returns 0.0."""
        df = pd.DataFrame({
            "Close": [100.0],
            "Volume": [1_000_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="1d", interval="1d")

        result = calculate_daily_change(pdata)
        assert result == 0.0

    def test_zero_previous_close(self):
        """Test division by zero protection."""
        df = pd.DataFrame({
            "Close": [0.0, 100.0],
            "Volume": [1_000_000, 1_200_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = calculate_daily_change(pdata)
        assert result == 0.0


class TestVolumeVsAverage:
    """Tests for volume comparison."""

    def test_normal_volume(self):
        """Test volume ratio calculation."""
        df = pd.DataFrame({
            "Close": [100.0] * 5,
            "Volume": [1_000_000, 1_000_000, 1_000_000, 1_000_000, 2_000_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="5d", interval="1d")

        result = volume_vs_average(pdata, lookback=4)
        # avg of last 4 = 1.25M, latest = 2M -> 2/1.25 = 1.6
        assert result == 1.6

    def test_default_lookback(self):
        """Test default 20-period lookback."""
        volumes = [1_000_000] * 19 + [2_000_000]
        df = pd.DataFrame({
            "Close": [100.0] * 20,
            "Volume": volumes,
        })
        pdata = PriceData(ticker="TEST", df=df, period="20d", interval="1d")

        result = volume_vs_average(pdata)
        avg = sum(volumes) / len(volumes)
        expected = volumes[-1] / avg
        assert result == pytest.approx(expected, rel=1e-6)

    def test_missing_volume_column(self):
        """Test missing Volume column returns 1.0."""
        df = pd.DataFrame({
            "Close": [100.0, 110.0],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = volume_vs_average(pdata)
        assert result == 1.0

    def test_zero_average_volume(self):
        """Test zero average volume returns 1.0."""
        df = pd.DataFrame({
            "Close": [100.0, 110.0],
            "Volume": [0, 0],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = volume_vs_average(pdata)
        assert result == 1.0


class TestCheckNewsCatalyst:
    """Tests for news catalyst placeholder."""

    def test_returns_none(self):
        """Placeholder should always return None."""
        assert check_news_catalyst("AAPL") is None
        assert check_news_catalyst("CDLX") is None


class TestDetectSuspiciousMove:
    """Tests for single-ticker detection."""

    def test_flag_large_up_move(self):
        """Test flagging a large upward move."""
        df = pd.DataFrame({
            "Close": [100.0, 115.0],
            "Volume": [1_000_000, 3_000_000],
        })
        pdata = PriceData(ticker="CDLX", df=df, period="2d", interval="1d")

        result = detect_suspicious_move(pdata, threshold_pct=10.0)

        assert result is not None
        assert result.ticker == "CDLX"
        assert result.move_pct == 15.0
        assert result.direction == "up"
        # avg of [1M, 3M] = 2M, latest = 3M -> 3/2 = 1.5
        assert result.volume_vs_avg == 1.5
        assert "15.0% move up" in result.flagged_reason
        assert result.has_news_catalyst is None

    def test_flag_large_down_move(self):
        """Test flagging a large downward move."""
        df = pd.DataFrame({
            "Close": [100.0, 85.0],
            "Volume": [1_000_000, 500_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = detect_suspicious_move(pdata, threshold_pct=10.0)

        assert result is not None
        assert result.move_pct == -15.0
        assert result.direction == "down"
        assert "15.0% move down" in result.flagged_reason

    def test_no_flag_below_threshold(self):
        """Test move below threshold is not flagged."""
        df = pd.DataFrame({
            "Close": [100.0, 105.0],
            "Volume": [1_000_000, 1_200_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = detect_suspicious_move(pdata, threshold_pct=10.0)
        assert result is None

    def test_exact_threshold(self):
        """Test move exactly at threshold is flagged."""
        df = pd.DataFrame({
            "Close": [100.0, 110.0],
            "Volume": [1_000_000, 1_000_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = detect_suspicious_move(pdata, threshold_pct=10.0)
        assert result is not None
        assert result.move_pct == 10.0

    def test_custom_threshold(self):
        """Test custom threshold works."""
        df = pd.DataFrame({
            "Close": [100.0, 105.0],
            "Volume": [1_000_000, 1_200_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = detect_suspicious_move(pdata, threshold_pct=5.0)
        assert result is not None
        assert result.move_pct == 5.0

    def test_empty_dataframe(self):
        """Test empty DataFrame returns None."""
        df = pd.DataFrame()
        pdata = PriceData(ticker="TEST", df=df, period="0d", interval="1d")

        result = detect_suspicious_move(pdata, threshold_pct=10.0)
        # calculate_daily_change will return 0.0 for empty df (len < 2)
        assert result is None

    def test_insufficient_rows(self):
        """Test single-row DataFrame returns None."""
        df = pd.DataFrame({
            "Close": [100.0],
            "Volume": [1_000_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="1d", interval="1d")

        result = detect_suspicious_move(pdata, threshold_pct=10.0)
        assert result is None

    def test_returns_suspicious_move_dataclass(self):
        """Test return type is SuspiciousMove dataclass."""
        df = pd.DataFrame({
            "Close": [100.0, 120.0],
            "Volume": [1_000_000, 2_000_000],
        })
        pdata = PriceData(ticker="TEST", df=df, period="2d", interval="1d")

        result = detect_suspicious_move(pdata, threshold_pct=10.0)
        assert isinstance(result, SuspiciousMove)


class TestScanTickers:
    """Tests for multi-ticker scanning."""

    def test_scan_multiple_tickers(self):
        """Test scanning multiple tickers returns flagged ones."""
        df_flagged = pd.DataFrame({
            "Close": [100.0, 115.0],
            "Volume": [1_000_000, 2_000_000],
        })
        df_normal = pd.DataFrame({
            "Close": [100.0, 101.0],
            "Volume": [1_000_000, 1_100_000],
        })
        df_down = pd.DataFrame({
            "Close": [100.0, 80.0],
            "Volume": [1_000_000, 1_500_000],
        })

        data = {
            "FLAG": PriceData(ticker="FLAG", df=df_flagged, period="2d", interval="1d"),
            "NORM": PriceData(ticker="NORM", df=df_normal, period="2d", interval="1d"),
            "DROP": PriceData(ticker="DROP", df=df_down, period="2d", interval="1d"),
        }

        results = scan_tickers(data, threshold_pct=10.0)

        assert len(results) == 2
        tickers = [r.ticker for r in results]
        assert "FLAG" in tickers
        assert "DROP" in tickers
        assert "NORM" not in tickers

    def test_scan_skips_none(self):
        """Test None values are skipped."""
        df_flagged = pd.DataFrame({
            "Close": [100.0, 115.0],
            "Volume": [1_000_000, 2_000_000],
        })

        data = {
            "FLAG": PriceData(ticker="FLAG", df=df_flagged, period="2d", interval="1d"),
            "NONE": None,
        }

        results = scan_tickers(data, threshold_pct=10.0)
        assert len(results) == 1
        assert results[0].ticker == "FLAG"

    def test_scan_skips_empty_df(self):
        """Test empty DataFrames are skipped."""
        df_flagged = pd.DataFrame({
            "Close": [100.0, 115.0],
            "Volume": [1_000_000, 2_000_000],
        })
        df_empty = pd.DataFrame()

        data = {
            "FLAG": PriceData(ticker="FLAG", df=df_flagged, period="2d", interval="1d"),
            "EMPTY": PriceData(ticker="EMPTY", df=df_empty, period="0d", interval="1d"),
        }

        results = scan_tickers(data, threshold_pct=10.0)
        assert len(results) == 1
        assert results[0].ticker == "FLAG"

    def test_scan_sorts_by_move_size(self):
        """Test results are sorted by absolute move size descending."""
        df_small = pd.DataFrame({
            "Close": [100.0, 111.0],
            "Volume": [1_000_000, 1_000_000],
        })
        df_large = pd.DataFrame({
            "Close": [100.0, 150.0],
            "Volume": [1_000_000, 1_000_000],
        })
        df_medium = pd.DataFrame({
            "Close": [100.0, 130.0],
            "Volume": [1_000_000, 1_000_000],
        })

        data = {
            "SMALL": PriceData(ticker="SMALL", df=df_small, period="2d", interval="1d"),
            "LARGE": PriceData(ticker="LARGE", df=df_large, period="2d", interval="1d"),
            "MED": PriceData(ticker="MED", df=df_medium, period="2d", interval="1d"),
        }

        results = scan_tickers(data, threshold_pct=10.0)

        assert len(results) == 3
        assert results[0].ticker == "LARGE"
        assert results[1].ticker == "MED"
        assert results[2].ticker == "SMALL"
        assert results[0].move_pct == 50.0
        assert results[1].move_pct == 30.0
        assert results[2].move_pct == 11.0

    def test_scan_no_flags(self):
        """Test empty result when no tickers meet threshold."""
        df_normal = pd.DataFrame({
            "Close": [100.0, 101.0],
            "Volume": [1_000_000, 1_100_000],
        })

        data = {
            "NORM1": PriceData(ticker="NORM1", df=df_normal, period="2d", interval="1d"),
            "NORM2": PriceData(ticker="NORM2", df=df_normal, period="2d", interval="1d"),
        }

        results = scan_tickers(data, threshold_pct=10.0)
        assert results == []

    def test_scan_single_row_df_skipped(self):
        """Test single-row DataFrames are skipped."""
        df_single = pd.DataFrame({
            "Close": [100.0],
            "Volume": [1_000_000],
        })

        data = {
            "SINGLE": PriceData(ticker="SINGLE", df=df_single, period="1d", interval="1d"),
        }

        results = scan_tickers(data, threshold_pct=10.0)
        assert results == []

    def test_scan_uses_default_threshold(self):
        """Test default threshold of 10%."""
        df = pd.DataFrame({
            "Close": [100.0, 110.0],
            "Volume": [1_000_000, 1_000_000],
        })

        data = {
            "EDGE": PriceData(ticker="EDGE", df=df, period="2d", interval="1d"),
        }

        results = scan_tickers(data)
        assert len(results) == 1
        assert results[0].move_pct == 10.0


class TestSuspiciousMoveDataclass:
    """Tests for the SuspiciousMove dataclass."""

    def test_dataclass_fields(self):
        """Test dataclass has expected fields."""
        move = SuspiciousMove(
            ticker="TEST",
            move_pct=15.5,
            direction="up",
            volume_vs_avg=2.5,
            flagged_reason="Test reason",
            has_news_catalyst=None,
        )
        assert move.ticker == "TEST"
        assert move.move_pct == 15.5
        assert move.direction == "up"
        assert move.volume_vs_avg == 2.5
        assert move.flagged_reason == "Test reason"
        assert move.has_news_catalyst is None

    def test_dataclass_defaults(self):
        """Test has_news_catalyst defaults to None."""
        move = SuspiciousMove(
            ticker="TEST",
            move_pct=15.5,
            direction="up",
            volume_vs_avg=2.5,
            flagged_reason="Test reason",
        )
        assert move.has_news_catalyst is None
