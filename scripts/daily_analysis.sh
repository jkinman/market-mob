#!/bin/bash
# Market Mob — Daily Analysis Cron Script
# Runs at market close + 1 hour (5:30 PM ET / 2:30 PM PT)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="/usr/bin/python3"
LOG_FILE="$PROJECT_DIR/logs/daily_$(date +%Y-%m-%d).log"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Run analysis
cd "$PROJECT_DIR"
{
    echo "=== Market Mob Daily Analysis ==="
    echo "Started: $(date)"
    echo "Working directory: $(pwd)"
    echo ""

    $VENV_PYTHON market_mob.py daily

    echo ""
    echo "Finished: $(date)"
} >> "$LOG_FILE" 2>&1

echo "Daily analysis complete. Log: $LOG_FILE"
