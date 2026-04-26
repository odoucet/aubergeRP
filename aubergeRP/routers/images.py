from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import get_config

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{session_token}/{image_id}")
def get_image(session_token: str, image_id: str):
    config = get_config()
    # image_id may or may not include extension; normalise to bare stem + .png
    stem = image_id[:-4] if image_id.lower().endswith(".png") else image_id
    image_path = Path(config.app.data_dir) / "images" / session_token / f"{stem}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(image_path), media_type="image/png")
