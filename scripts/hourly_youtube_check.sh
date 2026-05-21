#!/bin/bash
# Market Mob — Hourly YouTube Monitor
# Checks configured channels for new videos

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="/usr/bin/python3"
LOG_FILE="$PROJECT_DIR/logs/youtube_monitor_$(date +%Y-%m-%d).log"

mkdir -p "$PROJECT_DIR/logs"

cd "$PROJECT_DIR"
{
    echo "=== YouTube Monitor ==="
    echo "Started: $(date)"
    echo ""

    $VENV_PYTHON -m ingestion.youtube.rss_monitor

    echo ""
    echo "Finished: $(date)"
} >> "$LOG_FILE" 2>&1
