# Market Mob

An AI-powered stock analysis agent that watches financial YouTube channels, extracts stock picks, runs technical analysis, and generates daily markdown reports to your Obsidian vault.

Think of it as a research assistant that never sleeps — it monitors your favorite financial creators, fetches price data, computes indicators, asks an LLM for analysis, and writes everything to your vault in a format you can read and refine.

---

## Vision

**The problem:** There are thousands of financial YouTube channels, newsletters, and Twitter accounts. Keeping up is a full-time job. Most retail investors either miss good calls or act on bad ones without doing their own analysis.

**The solution:** Market Mob automates the grunt work. It watches channels you trust, extracts ticker mentions, pulls 90 days of price data, runs RSI/MACD/Bollinger analysis, and generates a structured daily report with an LLM-generated prediction. You wake up to a fresh note in your vault. You decide what to act on.

**Long-term:** A swarm of specialized agents — pick extractors, technical analysts, sentiment readers, risk assessors — collaborating to surface high-signal investment ideas from the noise.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MARKET MOB                                     │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   YouTube    │───▶│   Pick       │───▶│   Analysis   │               │
│  │   Ingestion  │    │   Extractor  │    │   Engine     │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│         │                   │                   │                        │
│         ▼                   ▼                   ▼                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   RSS        │    │   LLM        │    │   Technical  │               │
│  │   Monitor    │    │   (Grok)     │    │   Indicators │               │
│  │   (hourly)   │    │              │    │   (RSI/MACD) │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│         │                   │                   │                        │
│         └───────────────────┴───────────────────┘                        │
│                             │                                            │
│                             ▼                                            │
│                    ┌─────────────────┐                                   │
│                    │  LLM Analyst    │                                   │
│                    │  (Prediction)   │                                   │
│                    └─────────────────┘                                   │
│                             │                                            │
│                             ▼                                            │
│                    ┌─────────────────┐                                   │
│                    │  Obsidian       │                                   │
│                    │  Report         │                                   │
│                    └─────────────────┘                                   │
│                             │                                            │
│                             ▼                                            │
│                    ┌─────────────────┐                                   │
│                    │  Accuracy       │                                   │
│                    │  Tracker        │                                   │
│                    │  (7d/30d)       │                                   │
│                    └─────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
YouTube Video → Transcript → LLM Extractor → Stock Picks
                                                   │
                                                   ▼
Watchlist ──────────────────────────────▶ Price Fetch (yfinance)
                                                   │
                                                   ▼
                                    Technical Indicators (RSI/MACD/SMA/BB)
                                                   │
                                                   ▼
                                    LLM Analyst (Grok) → Prediction
                                                   │
                                                   ▼
                                    Markdown Report → Obsidian Vault
                                                   │
                                                   ▼
                                    Accuracy Tracker (scores after 7/30 days)
```

---

## Project Structure

```
market-mob/
├── agents/
│   ├── analyst/
│   │   └── llm_analyst.py          # Prompt builder + LLM caller + parser
│   └── pick_extractor/
│       └── llm_extractor.py        # Transcript → stock picks
├── analysis/
│   ├── technical/
│   │   ├── fetch_prices.py         # yfinance wrapper
│   │   └── indicators.py           # RSI, MACD, SMA, Bollinger Bands
│   └── accuracy_tracker.py         # Prediction scoring
├── ingestion/
│   └── youtube/
│       ├── extract_video_id.py     # URL parser
│       ├── fetch_transcript.py     # youtube-transcript-api
│       ├── pipeline.py             # Single video processing
│       └── rss_monitor.py          # Channel polling
├── output/
│   └── obsidian/
│       └── report_formatter.py     # Markdown generation
├── config/
│   ├── sources.json                # YouTube channels
│   └── watchlist.json              # Tracked tickers
├── scripts/
│   ├── daily_analysis.sh           # Daily cron wrapper
│   └── hourly_youtube_check.sh     # YouTube monitor wrapper
├── tests/                          # 81 tests, all passing
├── market_mob.py                   # CLI entry point
├── .env.example                    # Template (committed)
├── .env.local                      # Real keys (gitignored)
└── requirements.txt
```

---

## Development Phases

### Phase 1: Core Analysis Loop ✅ DONE
- Fetch prices from Yahoo Finance
- Compute technical indicators
- Call LLM for structured analysis
- Generate markdown report

### Phase 2: Ingestion Integration ✅ DONE
- YouTube transcript extraction
- LLM-based pick extraction
- RSS channel monitoring
- Auto-trigger analysis on new picks

### Phase 3: Automation ✅ DONE
- Daily cron job (market close + 1hr)
- Hourly YouTube monitor
- Watchlist persistence
- Report output to Obsidian

### Phase 4: Intelligence ✅ DONE
- Wire accuracy tracker into main flow
- Prediction scoring (7-day, 30-day)
- Accuracy stats in reports
- Self-monitoring dashboard

### Phase 5: Scale (Future)
- Multiple ingestion sources (newsletters, Twitter/X)
- Multi-model consensus (Grok + GPT + Claude)
- Backtesting framework
- Web dashboard
- Telegram alerts for high-confidence picks

---

## What Works

| Feature | Status | Notes |
|---------|--------|-------|
| Price fetching | ✅ | yfinance, 90-day history, no API key |
| Technical indicators | ✅ | RSI, MACD, SMA 20/50, Bollinger Bands |
| LLM analysis | ✅ | Grok via xAI API, structured JSON output |
| Report generation | ✅ | Markdown with frontmatter, saves to vault |
| YouTube transcript | ✅ | youtube-transcript-api, works on public videos |
| Pick extraction | ✅ | LLM extracts tickers from transcript |
| RSS monitoring | ✅ | Hourly poll, tracks seen videos |
| Watchlist | ✅ | JSON persistence, auto-adds new picks |
| Cron jobs | ✅ | Daily analysis + hourly YouTube check |
| Accuracy tracker | ✅ | Auto-records predictions, scores vs actual prices |
| Tests | ✅ | 81/81 passing |

## What Doesn't Work / Limitations

| Issue | Impact | Workaround |
|-------|--------|------------|
| Kimi K2.6 API not accessible | Can't use Kimi as LLM | Using xAI/Grok instead |
| YouTube RSS needs channel ID | Can't use @handle directly | RSS monitor resolves @handle → ID |
| Transcripts only on public videos | Private/unlisted videos fail | Only monitor public channels |
| yfinance rate limits | Occasional fetch failures | Retry logic + caching |
| LLM predictions are speculative | Not financial advice | Clearly labeled as AI-generated |
| No backtesting | Can't validate strategy historically | Track accuracy going forward |

---

## Setup

### 1. Clone & Install

```bash
git clone git@github.com:jkinman/market-mob.git
cd market-mob
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env.local
# Edit .env.local with your keys
```

### 3. Add YouTube Channels

Edit `config/sources.json`:

```json
{
  "channels": [
    {
      "name": "Financial Education",
      "url": "https://www.youtube.com/@FinancialEducation"
    }
  ]
}
```

### 4. Run

```bash
# Analyze a single ticker
python market_mob.py analyze AAPL

# Process a YouTube video
python market_mob.py video "https://youtu.be/VIDEO_ID"

# Run daily analysis on watchlist
python market_mob.py daily

# Check YouTube channels for new videos
python market_mob.py youtube
```

---

## Customization

### Change LLM Provider

Edit `.env.local`:

```bash
# xAI / Grok (default)
LLM_PROVIDER=openai
OPENAI_API_KEY=your_xai_key
OPENAI_BASE_URL=https://api.x.ai/v1
OPENAI_MODEL=grok-3-beta

# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Ollama (local)
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Add Custom Indicators

Edit `analysis/technical/indicators.py`:

```python
def stochastic_oscillator(df: pd.DataFrame, k_period: int = 14, d_period: int = 3):
    """Add Stochastic Oscillator to dataframe."""
    lowest_low = df["Low"].rolling(window=k_period).min()
    highest_high = df["High"].rolling(window=k_period).max()
    df["stoch_k"] = 100 * (df["Close"] - lowest_low) / (highest_high - lowest_low)
    df["stoch_d"] = df["stoch_k"].rolling(window=d_period).mean()
    return df
```

### Change Report Format

Edit `output/obsidian/report_formatter.py`:

```python
def format_daily_report(ticker, price_summary, indicators, analysis, report_date):
    # Customize markdown template here
    return f"""# {ticker} Analysis

## Your Custom Section
..."""
```

### Adjust Cron Schedule

```bash
# Edit cron jobs
hermes cronjob list
hermes cronjob update <job_id> --schedule "0 10 * * 1-5"  # 10 AM instead
```

---

## Testing

```bash
# Run all tests
pytest

# Run specific module
pytest tests/test_indicators.py -v

# Run with coverage
pytest --cov=analysis --cov=agents
```

---

## Key Metrics

- **81 tests** — all passing
- **14 prototype tasks** — complete
- **2 cron jobs** — active (daily + hourly)
- **0 external API keys required** for core functionality (yfinance is free)
- **~2s** — end-to-end analysis for single ticker (with LLM)

---

## Roadmap

| Priority | Task | Status |
|----------|------|--------|
| P0 | Wire accuracy tracker into main flow | ✅ Done |
| P0 | Real end-to-end test with live data | ✅ Done |
| P1 | Telegram alerts for high-confidence picks | Pending |
| P1 | Multi-source ingestion (newsletters, RSS) | Pending |
| P2 | Backtesting framework | Future |
| P2 | Web dashboard | Future |
| P2 | Multi-model consensus | Future |

---

## Disclaimer

This is an experimental tool for research and education. AI-generated stock predictions are not financial advice. Always do your own research. The accuracy tracker exists precisely because we want to measure how wrong (or right) the LLM is — not because it's infallible.

---

Built with minimal Python, pytest, and a lot of mocking. No frameworks until we need them.

## Domain Glossary

See [CONTEXT.md](https://github.com/jkinman/market-mob/blob/main/CONTEXT.md) for the shared domain language used across this project.

---

## Using Market Mob with Hermes Agent / OpenClaw

Market Mob is designed to be **discoverable and operable by AI agents**. If you're reading this as an agent, here's how to use it.

### Quick Agent Commands

```bash
# Navigate to project
cd ~/.hermes/workspace/market-mob

# Source environment (required for LLM access)
export $(grep -v '^#' .env.local | xargs)

# Analyze a single stock
python market_mob.py analyze AAPL

# Analyze a sector basket
python market_mob.py sector tech
python market_mob.py sector mining
python market_mob.py sector energy

# Run alpha scan (volatile stocks + suspicious moves)
python market_mob.py alpha

# Run market overview (macro sweep of watchlist)
python market_mob.py overview

# Process a YouTube video for stock picks
python market_mob.py youtube "https://youtu.be/VIDEO_ID"

# Run daily watchlist analysis
python market_mob.py daily

# Display investor persona
python market_mob.py persona
```

### Agent Discovery Protocol

When operating on behalf of a user, follow this flow:

**1. Check Environment**
```bash
# Verify .env.local exists and has LLM keys
ls .env.local
cat .env.local | grep -E "(LLM_PROVIDER|OPENAI_API_KEY)"

# Verify tests pass
python -m pytest tests/ -q
```

**2. Load Persona (if exists)**
```bash
cat config/persona.json 2>/dev/null || echo "No persona configured"
```
If persona exists, respect risk tolerance, avoid sectors, and mention current positions in analysis.

**3. Check Watchlist**
```bash
cat config/watchlist.json
```

**4. Run Appropriate Analysis**

| User Says | Command |
|---|---|
| "Analyze Tesla" | `python market_mob.py analyze TSLA` |
| "What's hot in quantum?" | `python market_mob.py sector tech` (or add quantum sector) |
| "Any suspicious moves today?" | `python market_mob.py alpha` |
| "Run my daily briefing" | `python market_mob.py overview` |
| "Check this video" | `python market_mob.py youtube "URL"` |

**5. Read Generated Reports**

Reports are saved to `output/obsidian/`:
```bash
ls -lt output/obsidian/ | head -10
cat output/obsidian/2026-05-21--aapl.md
```

**6. Update Watchlist (if needed)**

The user can paste a watchlist from Yahoo Finance, brokerages, etc. Parse tickers and write to `config/watchlist.json`:
```json
[
  {"ticker": "AAPL", "source": "manual", "status": "active", "added": "2026-05-21"},
  {"ticker": "TSLA", "source": "manual", "status": "active", "added": "2026-05-21"}
]
```

### Key Files for Agents

| File | Purpose |
|---|---|
| `market_mob.py` | CLI entry point — all commands go through here |
| `config/persona.json` | Investor profile (risk, positions, preferences) |
| `config/watchlist.json` | Active tickers to track |
| `config/sources.json` | YouTube channels to monitor |
| `.env.local` | API keys (never commit, gitignored) |
| `output/obsidian/` | Generated reports (markdown with frontmatter) |
| `analysis/sector/discovery.py` | Sector baskets (add new sectors here) |
| `agents/analyst/llm_analyst.py` | LLM prompts (modify for different analysis styles) |

### Extending Market Mob

**Add a new sector:**
```python
# analysis/sector/discovery.py
SECTOR_BASKETS["renewable"] = ["ENPH", "SEDG", "FSLR", "NXT", "NOVA", "RUN", "SPWR", "ARRY", "MAXN", "SHLS"]
```

**Add a new indicator:**
```python
# analysis/technical/indicators.py
def atr(df: pd.DataFrame, period: int = 14):
    """Average True Range — volatility indicator."""
    high_low = df["High"] - df["Low"]
    high_close = abs(df["High"] - df["Close"].shift())
    low_close = abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=period).mean()
    return df
```

**Add a new LLM provider:**
```python
# agents/analyst/llm_analyst.py
# Add to _call_llm() function
elif provider == "anthropic":
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    # ... implement call
```

### Safety Rules for Agents

1. **Never commit `.env.local`** — it contains live API keys
2. **Never expose tokens** in chat output or logs
3. **Respect persona risk tolerance** — don't recommend aggressive trades to conservative investors
4. **Always label** AI-generated analysis as "not financial advice"
5. **Test before claiming** — run `pytest tests/` after any code changes
6. **Commit after each task** — `git add -A && git commit -m "..."`

### Troubleshooting for Agents

| Symptom | Cause | Fix |
|---|---|---|
| `Connection refused` on localhost:11434 | Defaulting to Ollama, not configured | Export vars from `.env.local` first |
| `No tickers to analyze` | Watchlist empty | Check `config/watchlist.json` |
| LLM returns garbage | Prompt too long or model confused | Check token count, simplify prompt |
| yfinance fetch fails | Rate limit or invalid ticker | Retry, check ticker symbol |
| Tests fail after changes | Breaking change to dataclass or function | Check type signatures match |

---

*This guide is written for AI agents operating in Hermes, OpenClaw, or similar agent frameworks. If you're a human reading this — hi, the agents are doing their job.* 🦑
