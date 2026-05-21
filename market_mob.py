#!/usr/bin/env python3
"""Market Mob — Main orchestrator.

Wires together:
1. Ingestion (YouTube transcript → pick extraction)
2. Analysis (price data → indicators → LLM analysis)
3. Output (markdown report → Obsidian vault)
"""

import json
import os
from datetime import datetime
from typing import Optional, List

from analysis.technical.fetch_prices import fetch_prices
from analysis.technical.indicators import compute_all, summarize_latest
from agents.analyst.llm_analyst import analyze_stock, AnalysisResult
from agents.pick_extractor.llm_extractor import (
    extract_picks_from_transcript,
    picks_to_watchlist,
    StockPick,
)
from output.obsidian.report_formatter import format_daily_report, save_report
from ingestion.youtube import extract_video_id
from ingestion.youtube import pipeline as youtube_pipeline
from analysis.accuracy_tracker import AccuracyTracker
from analysis.sector.discovery import get_sector_tickers, list_sectors
from analysis.sector.basket_analyzer import analyze_sector
from analysis.sector.sector_report import generate_sector_report, save_sector_report


def load_sources_config(path: str = "config/sources.json") -> dict:
    """Load trusted sources configuration."""
    with open(path, "r") as f:
        return json.load(f)


def load_watchlist(path: str = "config/watchlist.json") -> List[dict]:
    """Load active watchlist."""
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def save_watchlist(watchlist: List[dict], path: str = "config/watchlist.json") -> None:
    """Save watchlist to disk."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(watchlist, f, indent=2)


def analyze_ticker(ticker: str, source: str = "manual") -> Optional[str]:
    """Analyze a single ticker end-to-end.

    Args:
        ticker: Stock symbol
        source: Where the pick came from

    Returns:
        Path to saved report, or None if analysis fails
    """
    print(f"[MARKET_MOB] Analyzing {ticker}...")

    # Step 1: Fetch prices
    price_data = fetch_prices(ticker, period="90d")
    if price_data is None:
        print(f"[ERROR] Failed to fetch prices for {ticker}")
        return None

    # Step 2: Compute indicators
    df = compute_all(price_data.df)
    indicators_summary = summarize_latest(df)

    # Step 3: LLM analysis
    analysis = analyze_stock(ticker, {}, indicators_summary)
    if analysis is None:
        print(f"[ERROR] LLM analysis failed for {ticker}")
        return None

    # Step 4: Record prediction via accuracy tracker
    tracker = AccuracyTracker()
    tracker.record_prediction(
        ticker=ticker,
        prediction_7d=analysis.prediction_7d,
        prediction_30d=analysis.prediction_30d,
        confidence=analysis.confidence,
        source=source,
        price_at_prediction=indicators_summary.get("price", 0.0),
    )

    # Step 5: Format and save report
    report = format_daily_report(ticker, {}, indicators_summary, analysis, source=source)
    filepath = save_report(ticker, report)

    print(f"[MARKET_MOB] Report saved: {filepath}")
    return filepath


def process_youtube_video(video_url: str, source_name: str) -> List[str]:
    """Process a YouTube video: extract picks → analyze each → generate reports.

    Args:
        video_url: YouTube URL
        source_name: Channel/source name

    Returns:
        List of saved report file paths
    """
    print(f"[MARKET_MOB] Processing video: {video_url}")

    # Step 1: Fetch transcript
    video_id = extract_video_id(video_url)
    if not video_id:
        print(f"[ERROR] Could not extract video ID from {video_url}")
        return []

    # Reuse existing pipeline for transcript
    pipeline_result = youtube_pipeline.run_pipeline(video_url, channel_name=source_name)
    if "error" in pipeline_result:
        print(f"[ERROR] Pipeline failed: {pipeline_result['error']}")
        return []

    transcript = pipeline_result.get("transcript", "")
    if not transcript:
        print(f"[ERROR] No transcript available")
        return []

    # Step 2: Extract picks with LLM
    extraction = extract_picks_from_transcript(transcript, source=source_name)
    if extraction is None or not extraction.picks:
        print(f"[MARKET_MOB] No picks found in video")
        return []

    print(f"[MARKET_MOB] Found {len(extraction.picks)} picks: {[p.ticker for p in extraction.picks]}")

    # Step 3: Add picks to watchlist
    watchlist = load_watchlist()
    new_entries = picks_to_watchlist(extraction.picks)
    watchlist.extend(new_entries)
    save_watchlist(watchlist)
    print(f"[MARKET_MOB] Added {len(new_entries)} entries to watchlist")

    # Step 4: Analyze each pick
    reports = []
    for pick in extraction.picks:
        filepath = analyze_ticker(pick.ticker, source=source_name)
        if filepath:
            reports.append(filepath)

    return reports


def run_sector_analysis(sector_name: str) -> Optional[str]:
    """Analyze an entire sector end-to-end.

    Args:
        sector_name: Sector name (e.g., "mining", "tech", "energy")

    Returns:
        Path to saved report, or None if analysis fails
    """
    print(f"[MARKET_MOB] Analyzing sector: {sector_name}")

    # Step 1: Resolve sector to tickers
    tickers = get_sector_tickers(sector_name)
    if tickers is None:
        available = list_sectors()
        print(f"[ERROR] Unknown sector '{sector_name}'. Available: {available}")
        return None

    print(f"[MARKET_MOB] Sector '{sector_name}' -> {len(tickers)} tickers: {tickers}")

    # Step 2: Analyze basket
    sector_analysis = analyze_sector(sector_name, tickers)
    if not sector_analysis.tickers_analyzed:
        print(f"[ERROR] No tickers could be analyzed for sector {sector_name}")
        return None

    # Step 3: Generate and save report
    report = generate_sector_report(sector_analysis, source="sector-command")
    filepath = save_sector_report(sector_name, report)

    print(f"[MARKET_MOB] Sector report saved: {filepath}")
    return filepath


def run_daily_analysis(tickers: Optional[List[str]] = None) -> List[str]:
    """Run daily analysis on watchlist or provided tickers.

    Args:
        tickers: Optional list of tickers to analyze (defaults to watchlist)

    Returns:
        List of saved report file paths
    """
    if tickers is None:
        watchlist = load_watchlist()
        tickers = list(set([entry["ticker"] for entry in watchlist if entry.get("status") == "active"]))

    if not tickers:
        print("[MARKET_MOB] No tickers to analyze")
        return []

    print(f"[MARKET_MOB] Running daily analysis for {len(tickers)} tickers: {tickers}")

    # Score any pending predictions before generating new reports
    tracker = AccuracyTracker()
    scored = tracker.score_pending_predictions()
    if scored["7d"] > 0 or scored["30d"] > 0:
        print(f"[MARKET_MOB] Scored {scored['7d']} 7-day and {scored['30d']} 30-day predictions")

    reports = []
    for ticker in tickers:
        filepath = analyze_ticker(ticker, source="watchlist")
        if filepath:
            reports.append(filepath)

    print(f"[MARKET_MOB] Generated {len(reports)} reports")
    return reports


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python market_mob.py analyze <TICKER>     # Analyze single ticker")
        print("  python market_mob.py sector <SECTOR>      # Analyze sector (mining, tech, energy, etc.)")
        print("  python market_mob.py daily                # Analyze watchlist")
        print("  python market_mob.py youtube <URL>        # Process YouTube video")
        sys.exit(1)

    command = sys.argv[1]

    if command == "analyze" and len(sys.argv) >= 3:
        ticker = sys.argv[2].upper()
        analyze_ticker(ticker)

    elif command == "sector" and len(sys.argv) >= 3:
        sector = sys.argv[2].lower()
        run_sector_analysis(sector)

    elif command == "daily":
        run_daily_analysis()

    elif command == "youtube" and len(sys.argv) >= 3:
        url = sys.argv[2]
        # Default source — in production, look up from config
        process_youtube_video(url, source_name="Unknown")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
