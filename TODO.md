# Market Mob — Prototype Plan

## Current Status

**Working:**
- ✅ YouTube URL → video ID extraction
- ✅ Transcript download (22K chars tested)
- ✅ Regex ticker detection (basic, needs LLM)
- ✅ File output (transcripts + picks JSON)
- ✅ Project structure (ingestion/analysis/agents/output)

**Not Working / Missing:**
- ❌ LLM pick extraction (prompt built, not executed)
- ❌ Price data integration (yfinance not wired in)
- ❌ Analysis engine (no technical indicators)
- ❌ Daily report generation
- ❌ RSS channel monitoring (manual URL only)
- ❌ Obsidian output format

---

## Phase 1: Core Analysis Loop (This Week)

### 1.1 Wire up yfinance data fetch
- [ ] Build `analysis/technical/fetch_prices.py`
- [ ] Given a ticker, fetch 90-day historical data
- [ ] Compute RSI, MACD, 20/50-day moving averages
- [ ] Output: structured JSON with indicators

### 1.2 Build LLM analyst agent
- [ ] Connect to local LLM (Ollama) or API
- [ ] Prompt: "Given price data + indicators, generate analysis"
- [ ] Output: trend, support/resistance, prediction, confidence

### 1.3 End-to-end single-ticker test
- [ ] Input: AAPL (or any ticker)
- [ ] Fetch price data → compute indicators → LLM analysis
- [ ] Save report to `output/obsidian/YYYY-MM-DD--AAPL.md`

---

## Phase 2: Ingestion + Analysis Integration (Next Week)

### 2.1 LLM pick extraction from transcripts
- [ ] Execute LLM prompt on transcript
- [ ] Parse JSON output (ticker, action, reasoning)
- [ ] Validate tickers against yfinance (is it real?)

### 2.2 Auto-track extracted picks
- [ ] Add tickers to `config/watchlist.json`
- [ ] Trigger analysis for each new pick
- [ ] Generate combined report: pick + analysis

### 2.3 RSS channel monitor
- [ ] Poll YouTube RSS feeds hourly
- [ ] Detect new videos → trigger ingestion pipeline
- [ ] Deduplicate against `data/seen_videos.json`

---

## Phase 3: Daily Automation (Following Week)

### 3.1 Cron job setup
- [ ] Hourly: RSS monitor
- [ ] Daily 4pm PT (market close): analysis run
- [ ] Generate daily digest report

### 3.2 Obsidian integration
- [ ] Daily note: `obsidian-vault/finance/daily/YYYY-MM-DD.md`
- [ ] Format: picks, analysis, predictions, confidence
- [ ] Wikilink to `ideas/ai-stock-analyst-agent.md`

### 3.3 Telegram alerts
- [ ] New pick detected → instant alert
- [ ] Daily digest → morning briefing

---

## Phase 4: Intelligence Layer (Later)

### 4.1 Prediction tracking
- [ ] Store predictions with dates
- [ ] Compare to actual prices after 7/30 days
- [ ] Calculate accuracy score per source/advisor

### 4.2 Source trust ranking
- [ ] Track which advisors' picks perform best
- [ ] Weight recommendations by historical accuracy

### 4.3 Multi-source ingestion
- [ ] Newsletter RSS pipeline
- [ ] Twitter/X pipeline (if API accessible)

---

## Immediate Next Step

Joel — want me to start **1.1** (yfinance price fetch + indicators) now? That's the core engine everything else depends on.
