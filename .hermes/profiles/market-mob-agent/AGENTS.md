# Market Mob Agent — Agent Guide

## Quick Start

```bash
# From the project root
cd /path/to/market-mob

# Copy env template
cp .hermes/profiles/market-mob-agent/.env.example .hermes/profiles/market-mob-agent/.env
# Edit .env with your XAI_API_KEY

# Run the agent
hermes -p .hermes/profiles/market-mob-agent chat

# Or use the wrapper
market-mob-agent chat -q "Analyze AAPL"
```

## What This Agent Does

Buffet Bot is a specialized stock analysis agent that:
- Runs Market Mob commands automatically
- Presents data, not opinions
- Flags risks before rewards
- Respects investor persona preferences
- Tracks prediction accuracy over time

## Commands

| Command | Description |
|---------|-------------|
| `hermes -p .hermes/profiles/market-mob-agent chat` | Interactive session |
| `market-mob-agent chat -q "Analyze TSLA"` | One-shot analysis |
| `market-mob-agent chat -q "Run alpha scan"` | Daily alpha scan |
| `market-mob-agent chat -q "Sector quantum"` | Sector analysis |

## Files

| File | Purpose |
|------|---------|
| `SOUL.md` | Personality and tone |
| `config.yaml` | Model, tools, display settings |
| `.env.example` | Required API keys template |
| `AGENTS.md` | This guide |

## Cron Jobs

The agent includes a daily alpha scan cron job. To activate:

```bash
hermes cron create "30 14 * * 1-5" --prompt "Run alpha scan" --workdir /path/to/market-mob
```

## Customization

- Edit `SOUL.md` to change personality
- Edit `config.yaml` to change model/provider
- Add skills to the `skills:` list in config.yaml
