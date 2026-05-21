# Market Mob — Domain Glossary

## Core Concepts

### Alpha

**Definition:** Actionable trading signals derived from technical analysis, unusual options activity, or suspicious price movements.
**Used in:** `market_mob.py alpha`, alpha scan reports, LLM analyst prompts
**Not to be confused with:** Overview (macro market summary, not actionable signals)

### Basket

**Definition:** A collection of stocks grouped by sector, theme, or custom criteria. Analyzed as a unit for relative strength and sector trends.
**Used in:** `analysis/sector/basket_analyzer.py`, sector reports
**Not to be confused with:** Watchlist (user-curated list of individual tickers)

### Deep Module

**Definition:** A module with a small interface hiding complex implementation. High leverage for callers, high locality for maintainers.
**Used in:** Architecture discussions, `/improve-codebase-architecture` skill
**Not to be confused with:** Shallow module (interface nearly as complex as implementation)

### Opportunity Setup

**Definition:** A stock meeting criteria for potential entry: breakout above resistance, momentum continuation, or mean reversion signal.
**Used in:** Alpha scan reports, sector reports
**Not to be confused with:** Suspicious move (already happened, may be overextended)

### Overview

**Definition:** Macro market summary across the watchlist. Breadth, trend direction, sector leadership. Not actionable — situational awareness.
**Used in:** `market_mob.py overview`, overview reports
**Not to be confused with:** Alpha (actionable signals)

### Persona

**Definition:** Investor profile injected into LLM prompts. Risk tolerance, positions, preferred sectors, time horizon.
**Used in:** `config/persona.json`, `agents/persona/`, all LLM analyst prompts
**Not to be confused with:** Skill persona (Buffet Bot personality framework)

### Pick Extractor

**Definition:** LLM agent that reads a YouTube transcript and extracts stock picks with confidence scores.
**Used in:** `agents/pick_extractor/`, YouTube ingestion pipeline
**Not to be confused with:** Analyst (the agent that analyzes price data, not transcripts)

### PriceData

**Definition:** Standardized dataclass for OHLCV price history. 90-day default. Shared across all analysis modules.
**Used in:** `analysis/technical/fetch_prices.py`, indicators, reports
**Fields:** ticker, dates, opens, highs, lows, closes, volumes

### Seam

**Definition:** Where an interface lives; a place behaviour can be altered without editing in place.
**Used in:** Architecture discussions, test design
**Not to be confused with:** Boundary (vague term, use seam instead)

### Sentiment

**Definition:** Market mood derived from social media, news, or mock data. Bullish/bearish/neutral score.
**Used in:** `analysis/sentiment/`, single-ticker reports, sector reports
**Not to be confused with:** Technical indicators (price-based, not mood-based)

### Suspicious Move

**Definition:** A stock price moving 10-50% with no identifiable catalyst. Flagged for investigation, not automatic action.
**Used in:** `analysis/technical/suspicious_move.py`, alpha scan, sector reports
**Not to be confused with:** Volatile (any large move, with or without catalyst)

### TER (Token Efficiency Ratio)

**Definition:** Output value divided by tokens consumed. Core metric for AI efficiency.
**Used in:** All agent conversations, skill design, caveman mode
**Formula:** `TER = Value Delivered / Tokens Consumed`

### Tracer Bullet

**Definition:** A thin vertical slice that cuts through all layers end-to-end. One test + one implementation.
**Used in:** TDD workflow, issue breakdown (`to-issues` skill)
**Not to be confused with:** Horizontal slice (one layer across all features)

### Vertical Slice

**Definition:** An end-to-end feature slice that includes all layers (data, logic, UI, tests). Independently demoable.
**Used in:** Issue creation, TDD, project planning
**Not to be confused with:** Horizontal slice (e.g., "build all DB schema first")

### Volatile

**Definition:** Any stock with large price movement or high volume. Broader category than suspicious move.
**Used in:** Alpha scan, technical analysis
**Not to be confused with:** Suspicious move (specifically no-catalyst moves)

## Module Vocabulary

| Term | Meaning |
|---|---|
| `fetch_prices` | Yahoo Finance data ingestion wrapper |
| `indicators` | RSI, MACD, SMA, Bollinger Bands calculations |
| `llm_analyst` | Prompt builder + LLM caller for stock analysis |
| `llm_extractor` | Transcript → stock picks with confidence |
| `accuracy_tracker` | Records predictions, scores them 7/30 days later |
| `rss_monitor` | Hourly poll of YouTube RSS feeds |
| `sector_report` | Formats basket analysis into markdown |
| `report_formatter` | Single-ticker markdown report generator |
| `options_tracker` | Options volume, OI, PCR ratio analysis |
| `sentiment_scraper` | X/Twitter sentiment (mock + xurl + web backends) |
| `persona_loader` | Reads `config/persona.json`, injects into prompts |

## Report Types

| Report | Command | Content |
|---|---|---|
| Single-ticker | `analyze <TICKER>` | Price, indicators, LLM analysis, options, sentiment |
| Sector | `sector <NAME>` | Basket ranking, suspicious moves, options aggregate |
| Alpha | `alpha` | Volatile stocks, suspicious moves, contrarian signals, options flow |
| Overview | `overview` | Macro market sweep, breadth, sector leadership |

## External Services

| Service | Used For | Fallback |
|---|---|---|
| yfinance | Price data, options chains | None (required) |
| xAI (Grok) | LLM analysis, pick extraction | Ollama (local) |
| xurl | X/Twitter sentiment | Web scraping → Mock |
| YouTube RSS | New video detection | Manual URL input |
