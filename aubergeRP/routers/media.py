from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models.media import MediaItem
from ..services.media_service import MediaNotFoundError, MediaService

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/", response_model=list[MediaItem])
def list_media() -> list[MediaItem]:
    from ..config import get_config

    config = get_config()
    service = MediaService(data_dir=config.app.data_dir)
    rows = service.list_media()
    return [MediaItem.model_validate(row, from_attributes=True) for row in rows]


@router.delete("/{media_id}", status_code=204)
def delete_media(media_id: str) -> None:
    from ..config import get_config

    config = get_config()
    service = MediaService(data_dir=config.app.data_dir)
    try:
        service.delete_media(media_id)
    except MediaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
