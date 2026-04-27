from __future__ import annotations

from fastapi import APIRouter, Query

from ..services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/")
def get_statistics(
    days: int = Query(default=14, ge=1, le=90),
    top: int = Query(default=15, ge=1, le=100),
) -> dict[str, object]:
    from ..config import get_config

    config = get_config()
    service = StatisticsService(data_dir=config.app.data_dir)
    return service.get_dashboard_data(days=days, top=top)
