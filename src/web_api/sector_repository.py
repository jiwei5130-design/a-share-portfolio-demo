"""Thread-safe access to the read-only P6 sector service."""

from functools import lru_cache

from src.sector_intelligence import SectorIntelligenceService


@lru_cache(maxsize=1)
def get_sector_service() -> SectorIntelligenceService:
    return SectorIntelligenceService()
