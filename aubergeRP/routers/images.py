from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import get_config
from ..scheduler import cleanup_images
from .admin import get_admin_token

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{session_token}/{image_id}")
def get_image(session_token: str, image_id: str) -> FileResponse:
    config = get_config()
    # image_id may or may not include extension; normalise to bare stem + .png
    stem = image_id[:-4] if image_id.lower().endswith(".png") else image_id
    image_path = Path(config.app.data_dir) / "images" / session_token / f"{stem}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(image_path), media_type="image/png")


class CleanupRequest(BaseModel):
    older_than_days: int = Field(default=30, ge=1)


class CleanupResponse(BaseModel):
    deleted: int


@router.post("/cleanup", response_model=CleanupResponse)
def cleanup_old_images(
    body: CleanupRequest,
    admin_token: str = Depends(get_admin_token),
) -> CleanupResponse:
    """Delete images older than *older_than_days* days from the data directory."""
    config = get_config()
    deleted = cleanup_images(config.app.data_dir, body.older_than_days)
    return CleanupResponse(deleted=deleted)
