from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse

from ..models.character import CharacterData
from ..services.character_service import (
    CharacterImportError,
    CharacterNotFoundError,
    CharacterService,
)

router = APIRouter(prefix="/characters", tags=["characters"])


def get_character_service() -> CharacterService:
    from ..config import get_config
    config = get_config()
    return CharacterService(data_dir=config.app.data_dir)


def _not_found(character_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Character '{character_id}' not found")


# Fixed routes BEFORE parameterised ones to avoid shadowing
@router.post("/import", status_code=201)
async def import_character(
    file: UploadFile = File(...),
    service: CharacterService = Depends(get_character_service),
):
    content = await file.read()
    filename = file.filename or ""
    try:
        if filename.lower().endswith(".png"):
            card = service.import_character_png(content)
        else:
            card = service.import_character_json(content, filename)
    except CharacterImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return card


@router.get("/")
def list_characters(service: CharacterService = Depends(get_character_service)):
    return service.list_characters()


@router.post("/", status_code=201)
def create_character(
    data: CharacterData,
    service: CharacterService = Depends(get_character_service),
):
    return service.create_character(data)


@router.get("/{character_id}")
def get_character(
    character_id: str,
    service: CharacterService = Depends(get_character_service),
):
    try:
        return service.get_character(character_id)
    except CharacterNotFoundError:
        raise _not_found(character_id)


@router.put("/{character_id}")
def update_character(
    character_id: str,
    data: CharacterData,
    service: CharacterService = Depends(get_character_service),
):
    try:
        return service.update_character(character_id, data)
    except CharacterNotFoundError:
        raise _not_found(character_id)


@router.delete("/{character_id}", status_code=204)
def delete_character(
    character_id: str,
    service: CharacterService = Depends(get_character_service),
):
    try:
        service.delete_character(character_id)
    except CharacterNotFoundError:
        raise _not_found(character_id)


@router.get("/{character_id}/avatar")
def get_avatar(
    character_id: str,
    service: CharacterService = Depends(get_character_service),
):
    try:
        service.get_character(character_id)
    except CharacterNotFoundError:
        raise _not_found(character_id)
    path = service.get_avatar_path(character_id)
    if path is None:
        raise HTTPException(status_code=404, detail="No avatar set for this character")
    return FileResponse(path)


@router.post("/{character_id}/avatar")
async def upload_avatar(
    character_id: str,
    file: UploadFile = File(...),
    service: CharacterService = Depends(get_character_service),
):
    try:
        service.get_character(character_id)
    except CharacterNotFoundError:
        raise _not_found(character_id)
    content = await file.read()
    service.save_avatar(character_id, content)
    return {"avatar_url": f"/api/characters/{character_id}/avatar"}


@router.get("/{character_id}/export/json")
def export_json(
    character_id: str,
    service: CharacterService = Depends(get_character_service),
):
    try:
        data = service.export_character_json(character_id)
    except CharacterNotFoundError:
        raise _not_found(character_id)
    name = data.get("data", {}).get("name", "character")
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}.json"'},
    )


@router.get("/{character_id}/export/png")
def export_png(
    character_id: str,
    service: CharacterService = Depends(get_character_service),
):
    try:
        content = service.export_character_png(character_id)
    except CharacterNotFoundError:
        raise _not_found(character_id)
    except (CharacterImportError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return Response(
        content=content,
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="character.png"'},
    )


@router.post("/{character_id}/duplicate", status_code=201)
def duplicate_character(
    character_id: str,
    service: CharacterService = Depends(get_character_service),
):
    try:
        return service.duplicate_character(character_id)
    except CharacterNotFoundError:
        raise _not_found(character_id)
