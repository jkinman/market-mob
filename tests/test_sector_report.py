"""Tests for sector report generation module."""

from analysis.sector.basket_analyzer import SectorAnalysis, StockScore
from analysis.sector.sector_report import (
    generate_sector_report,
    save_sector_report,
    _format_stock_table,
    _format_suspicious_moves,
)


class TestFormatStockTable:
    """Unit tests for stock table formatting."""

    def test_format_stock_table_structure(self):
        """Table should contain headers and rows."""
        stocks = [
            StockScore(
                ticker="AAPL", price=150.0, price_change_1d=2.5,
                rsi_14=55.0, above_sma_20=True, above_sma_50=True,
                macd_bullish=True, momentum_score=85.0, risk_score=30.0,
                opportunity_rank=1,
            ),
        ]
        table = _format_stock_table(stocks)
        assert "| Rank |" in table
        assert "AAPL" in table
        assert "$150.00" in table
        assert "+2.50%" in table
        assert "Yes" in table

    def test_format_stock_table_empty(self):
        """Empty list should still produce headers."""
        table = _format_stock_table([])
        assert "| Rank |" in table
        assert "AAPL" not in table


class TestFormatSuspiciousMoves:
    """Unit tests for suspicious moves formatting."""

    def test_no_moves(self):
        """No moves should return friendly message."""
        analysis = SectorAnalysis(sector_name="test", tickers_analyzed=[])
        text = _format_suspicious_moves(analysis)
        assert "No suspicious moves" in text

    def test_with_moves(self):
        """Moves should be formatted as bullet list."""
        from analysis.technical.suspicious_moves import SuspiciousMove
        analysis = SectorAnalysis(
            sector_name="test",
            tickers_analyzed=["VOLA"],
            suspicious_moves=[
                SuspiciousMove(
                    ticker="VOLA", move_pct=15.0, direction="up",
                    volume_vs_avg=3.5, flagged_reason="Big move",
                ),
            ],
        )
        text = _format_suspicious_moves(analysis)
        assert "VOLA" in text
        assert "+15.00%" in text
        assert "3.5x avg" in text


class TestGenerateSectorReport:
    """Unit tests for report generation."""

    def _make_dummy_analysis(self) -> SectorAnalysis:
        """Helper to create a dummy SectorAnalysis."""
        scores = [
            StockScore(
                ticker="AAPL", price=150.0, price_change_1d=2.5,
                rsi_14=55.0, above_sma_20=True, above_sma_50=True,
                macd_bullish=True, momentum_score=85.0, risk_score=30.0,
                opportunity_rank=1,
            ),
            StockScore(
                ticker="MSFT", price=300.0, price_change_1d=-1.0,
                rsi_14=45.0, above_sma_20=True, above_sma_50=False,
                macd_bullish=False, momentum_score=60.0, risk_score=40.0,
                opportunity_rank=2,
            ),
        ]
        return SectorAnalysis(
            sector_name="tech",
            tickers_analyzed=["AAPL", "MSFT"],
            avg_rsi=50.0,
            pct_above_sma20=50.0,
            pct_above_sma50=50.0,
            pct_bullish_macd=50.0,
            avg_price_change_1d=0.75,
            top_momentum=scores[0],
            worst_performer=scores[1],
            ranked_stocks=scores,
        )

    def test_report_contains_sector_name(self):
        """Report should mention the sector name."""
        analysis = self._make_dummy_analysis()
        report = generate_sector_report(analysis)
        assert "TECH Sector Watchlist" in report

    def test_report_contains_metrics(self):
        """Report should include aggregated metrics."""
        analysis = self._make_dummy_analysis()
        report = generate_sector_report(analysis)
        assert "Average RSI" in report
        assert "% Above SMA 20" in report
        assert "% Above SMA 50" in report
        assert "% Bullish MACD" in report

    def test_report_contains_leader_laggard(self):
        """Report should mention top momentum and worst performer."""
        analysis = self._make_dummy_analysis()
        report = generate_sector_report(analysis)
        assert "Top Momentum" in report
        assert "AAPL" in report
        assert "Worst Performer" in report
        assert "MSFT" in report

    def test_report_contains_ranked_table(self):
        """Report should contain the ranked opportunities table."""
        analysis = self._make_dummy_analysis()
        report = generate_sector_report(analysis)
        assert "| Rank |" in report
        assert "AAPL" in report
        assert "MSFT" in report

    def test_report_contains_sentiment_placeholder(self):
        """Report should include the news/sentiment placeholder."""
        analysis = self._make_dummy_analysis()
        report = generate_sector_report(analysis)
        assert "News/sentiment integration pending" in report

    def test_report_contains_source(self):
        """Report should include source info."""
        analysis = self._make_dummy_analysis()
        report = generate_sector_report(analysis, source="manual")
        assert "Source: manual" in report


class TestSaveSectorReport:
    """Unit tests for saving reports."""

    def test_save_report_creates_file(self, tmp_path):
        """save_sector_report should create a file."""
        content = "# Test Report\n"
        output_dir = tmp_path / "reports"
        path = save_sector_report("mining", content, output_dir=str(output_dir))
        assert path.endswith("mining-sector.md")
        assert path.startswith(str(output_dir))
        with open(path) as f:
            assert f.read() == content
