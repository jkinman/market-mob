"""News distiller — use LLM to extract market-moving signals from raw articles."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from .aggregator import RawArticle


@dataclass
class DistilledInsight:
    """A single distilled insight from the news stream."""

    category: str  # "breaking", "emerging", "prediction", "earnings", "macro", "commodity"
    headline: str  # One-line summary
    detail: str  # 2-3 sentences of context
    tickers: list[str] = field(default_factory=list)
    sentiment: str = "neutral"  # "bullish", "bearish", "neutral"
    urgency: int = 1  # 1-5, 5 = market-moving NOW
    sources: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)


class NewsDistiller:
    """Distill raw articles into actionable market insights using LLM."""

    def __init__(self, llm_provider: Optional[str] = None):
        self.llm_provider = llm_provider or os.getenv("LLM_PROVIDER", "openai")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.x.ai/v1")
        self.model = os.getenv("OPENAI_MODEL", "grok-3-beta")

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with the given prompt."""
        import requests
        from dotenv import load_dotenv
        import os

        # Load env from project root (cwd-agnostic)
        # distiller.py is at: market-mob/ingestion/news/distiller.py
        # .env.local is at: market-mob/.env.local
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_path = os.path.join(project_dir, ".env.local")
        load_dotenv(env_path)

        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.x.ai/v1")
        model = os.getenv("OPENAI_MODEL", "grok-3-beta")

        if not api_key:
            print(f"[ERROR] No OPENAI_API_KEY found. Tried: {env_path}")
            return "[]"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a financial news analyst. Extract only market-moving signals. Be concise and factual."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            return "[]"

    def _build_prompt(self, articles: list[RawArticle]) -> str:
        """Build the distillation prompt from raw articles."""
        # Take top 30 most recent articles to stay within token limits
        recent = articles[:30]

        articles_text = "\n\n".join([
            f"SOURCE: {a.source}\nTITLE: {a.title}\nSUMMARY: {a.summary}\nTICKERS: {', '.join(a.tickers)}"
            for a in recent
        ])

        prompt = f"""You are a senior financial analyst at a hedge fund. Read these news articles and extract the MOST INTERESTING and NON-OBVIOUS market signals.

Your job is NOT to summarize headlines. Your job is to find the titbits, the undercurrents, the stories-behind-the-stories that most retail investors miss.

Return a JSON array of insights. Each insight must have:
- category: one of ["breaking", "emerging", "prediction", "earnings", "macro", "commodity", "policy", "industry", "contrarian"]
- headline: punchy one-liner (max 12 words)
- detail: 3-4 sentences with SPECIFIC numbers, names, and context. What makes this interesting? Why should a trader care?
- tickers: array of mentioned stock tickers (if any)
- sentiment: "bullish", "bearish", or "neutral"
- urgency: 1-5 (5 = market-moving NOW, 1 = background context)
- themes: array of themes (e.g., ["semiconductors", "china_stimulus", "uranium", "biotech_ma", "ai_power"])

CATEGORIES EXPLAINED:
- "breaking" = News that would move markets TODAY (earnings surprises, M&A, policy shocks)
- "emerging" = Narratives building momentum but not mainstream yet (new technology, shifting supply chains)
- "prediction" = Specific forecasts from institutions with numbers and timelines
- "industry" = Sector-specific intel (mining, tech, biotech, energy) with WHY it matters
- "contrarian" = Signals that go against consensus (retail selling while institutions buying, etc.)
- "macro" = Fed, inflation, GDP, employment — but ONLY if there's a NEW angle
- "commodity" = Gold, oil, copper, uranium, lithium — with supply/demand specifics
- "policy" = Tariffs, regulations, stimulus, sanctions — with impact analysis

WHAT MAKES AN INSIGHT GOOD:
✓ Specific numbers: "Copper inventories at LME lowest since 2005" 
✓ Specific names: "BlackRock filed for spot XRP ETF"
✓ Causal chains: "Japan's yen intervention → forced selling of US Treasuries → yields spike"
✓ Under-the-radar: "Small-cap biotech M&A up 300% YoY but nobody's talking about it"
✓ Contrarian: "Hedge funds most short semiconductor stocks since 2022"

WHAT MAKES AN INSIGHT BAD:
✗ Generic: "Markets are up today"
✗ Vague: "Tech stocks look interesting"
✗ Obvious: "Fed might cut rates someday"
✗ No numbers, no names, no specifics

ARTICLES:
{articles_text}

Return ONLY valid JSON array. No markdown, no explanations, no preamble."""

        return prompt

    def distill(self, articles: list[RawArticle]) -> list[DistilledInsight]:
        """Distill raw articles into actionable insights."""
        if not articles:
            return []

        prompt = self._build_prompt(articles)
        response = self._call_llm(prompt)

        # Parse JSON response
        try:
            # Handle markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            data = json.loads(response)
            insights = []
            for item in data:
                insight = DistilledInsight(
                    category=item.get("category", "emerging"),
                    headline=item.get("headline", ""),
                    detail=item.get("detail", ""),
                    tickers=item.get("tickers", []),
                    sentiment=item.get("sentiment", "neutral"),
                    urgency=item.get("urgency", 1),
                    sources=item.get("sources", []),
                    themes=item.get("themes", []),
                )
                insights.append(insight)

            # Sort by urgency (highest first)
            insights.sort(key=lambda x: x.urgency, reverse=True)
            return insights

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse LLM response as JSON: {e}")
            print(f"Response preview: {response[:500]}")
            return []

    def distill_batch(self, articles: list[RawArticle], batch_size: int = 30) -> list[DistilledInsight]:
        """Distill in batches to handle large article sets."""
        all_insights = []
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            insights = self.distill(batch)
            all_insights.extend(insights)

        # Re-sort by urgency
        all_insights.sort(key=lambda x: x.urgency, reverse=True)
        return all_insights


if __name__ == "__main__":
    # Smoke test
    from .aggregator import NewsAggregator

    agg = NewsAggregator()
    articles = agg.fetch_all(max_per_feed=2, max_newsapi=5)
    articles = agg.enrich_with_tickers(articles)

    distiller = NewsDistiller()
    insights = distiller.distill(articles)

    print(f"\nDistilled {len(insights)} insights from {len(articles)} articles:\n")
    for i in insights[:10]:
        print(f"[{i.category.upper()}] Urgency: {i.urgency}/5 | Sentiment: {i.sentiment}")
        print(f"  {i.headline}")
        print(f"  {i.detail}")
        if i.tickers:
            print(f"  Tickers: {', '.join(i.tickers)}")
        print()
