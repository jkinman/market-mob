"""News ingestion and distillation module for Market Mob."""

from .aggregator import NewsAggregator
from .distiller import NewsDistiller
from .correlator import WatchlistCorrelator

__all__ = ["NewsAggregator", "NewsDistiller", "WatchlistCorrelator"]
