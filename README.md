# Market Mob

AI-powered stock analysis agent with multi-source ingestion pipelines.

## Overview

Market Mob is an autonomous financial analyst that:
- Monitors multiple sources for stock tips and recommendations (YouTube, newsletters, social media)
- Analyzes historical and current price data
- Generates daily reports with predictions and actionable insights
- Tracks prediction accuracy over time for compounding intelligence

## Architecture

```
ingestion/          # Pipeline factory — add new sources here
  youtube/          # YouTube transcript ingestion
  rss/              # Newsletter/blog ingestion (future)
  twitter/          # Social media ingestion (future)
  
analysis/           # Core stock analysis engine
  technical/        # Technical indicators (RSI, MACD, etc.)
  fundamental/      # Fundamental analysis (future)
  sentiment/        # News/sentiment analysis (future)
  
agents/             # LLM agents
  pick_extractor/   # Extract stock picks from transcripts
  analyst/          # Generate analysis and predictions
  
output/             # Daily reports
  obsidian/         # Markdown notes for vault
  email/            # HTML email digests (future)
  
config/
  channels.json     # Trusted sources
  watchlist.json    # Active picks to track
```
