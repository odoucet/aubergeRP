"""Prompt management API.

GET  /prompts/         — list all prompts with metadata and current content
GET  /prompts/{key}    — get a single prompt
PUT  /prompts/{key}    — save custom content (admin required)
DELETE /prompts/{key}  — reset to built-in default (admin required)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.prompt_service import (
    PROMPT_DEFAULTS,
    PROMPT_META,
    get_prompt,
    list_prompts,
    reset_prompt,
    save_prompt,
)
from .admin import get_admin_token

router = APIRouter(prefix="/prompts", tags=["prompts"])

_ALL_KEYS = set(PROMPT_META.keys())


class PromptUpdate(BaseModel):
    content: str


@router.get("/")
def get_all_prompts() -> list[dict[str, object]]:
    return list_prompts()


@router.get("/{key}")
def get_one_prompt(key: str) -> dict[str, object]:
    if key not in _ALL_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key!r}")
    meta = PROMPT_META[key]
    content = get_prompt(key)
    default_text = PROMPT_DEFAULTS.get(key, "")
    return {
        "key": key,
        "label": meta["label"],
        "description": meta["description"],
        "content": content,
        "default": default_text,
        "has_reset": key in PROMPT_DEFAULTS,
    }


@router.put("/{key}")
def update_prompt(
    key: str,
    body: PromptUpdate,
    admin_token: str = Depends(get_admin_token),
) -> dict[str, object]:
    if key not in _ALL_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key!r}")
    try:
        save_prompt(key, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"key": key, "content": body.content}


@router.delete("/{key}")
def reset_prompt_endpoint(
    key: str,
    admin_token: str = Depends(get_admin_token),
) -> dict[str, object]:
    if key not in _ALL_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key!r}")
    if key not in PROMPT_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Prompt {key!r} has no built-in default to reset to.")
    try:
        content = reset_prompt(key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"key": key, "content": content}
