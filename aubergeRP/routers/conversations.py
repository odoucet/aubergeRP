from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..models.conversation import Conversation, ConversationCreate, ConversationSummary
from ..services.character_service import CharacterNotFoundError, CharacterService
from ..services.conversation_service import ConversationNotFoundError, ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_service() -> ConversationService:
    from ..config import get_config
    config = get_config()
    char_svc = CharacterService(data_dir=config.app.data_dir)
    return ConversationService(data_dir=config.app.data_dir, character_service=char_svc)


def _not_found(conversation_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")


@router.get("/")
def list_conversations(
    character_id: Optional[str] = None,
    service: ConversationService = Depends(get_conversation_service),
):
    return service.list_conversations(character_id)


@router.post("/", status_code=201)
def create_conversation(
    body: ConversationCreate,
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        return service.create_conversation(body.character_id)
    except CharacterNotFoundError:
        raise HTTPException(status_code=404, detail=f"Character '{body.character_id}' not found")


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        return service.get_conversation(conversation_id)
    except ConversationNotFoundError:
        raise _not_found(conversation_id)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        service.delete_conversation(conversation_id)
    except ConversationNotFoundError:
        raise _not_found(conversation_id)
