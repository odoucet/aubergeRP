from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import get_config

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{session_token}/{image_id}")
def get_image(session_token: str, image_id: str):
    config = get_config()
    image_path = Path(config.app.data_dir) / "images" / session_token / f"{image_id}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(image_path), media_type="image/png")
