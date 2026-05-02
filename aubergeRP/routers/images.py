from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import get_config
from ..scheduler import cleanup_images
from .admin import get_admin_token

router = APIRouter(prefix="/images", tags=["images"])

# Only allow alphanumeric characters, hyphens, and underscores in path components
_SAFE_COMPONENT_RE = re.compile(r"^[\w\-]+$")


def _safe_component(value: str) -> bool:
    """Return True if *value* is safe to use as a path component."""
    return bool(_SAFE_COMPONENT_RE.match(value))


@router.get("/{session_token}/{image_id}")
def get_image(session_token: str, image_id: str) -> FileResponse:
    config = get_config()
    if not _safe_component(session_token) or not _safe_component(image_id):
        raise HTTPException(status_code=404, detail="Image not found")
    images_root = (Path(config.app.data_dir) / "images").resolve()
    # image_id may or may not include extension; normalise to bare stem + .png
    stem = image_id[:-4] if image_id.lower().endswith(".png") else image_id
    image_path = (images_root / session_token / f"{stem}.png").resolve()
    # Guard against path-traversal: the resolved path must stay under images_root
    if not image_path.is_relative_to(images_root):
        raise HTTPException(status_code=404, detail="Image not found")
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
