from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..constants import SESSION_TOKEN
from ..models.chat import ChatMessageRequest
from ..services.chat_service import ChatService
from ..services.character_service import CharacterService
from ..services.conversation_service import ConversationService
from ..connectors.manager import ConnectorManager

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service() -> ChatService:
    from ..config import get_config
    config = get_config()
    data_dir = config.app.data_dir
    char_svc = CharacterService(data_dir=data_dir)
    conv_svc = ConversationService(data_dir=data_dir, character_service=char_svc)
    manager = ConnectorManager(data_dir=data_dir, config=config)
    images_dir = Path(data_dir) / "images" / SESSION_TOKEN
    return ChatService(
        conversation_service=conv_svc,
        character_service=char_svc,
        connector_manager=manager,
        images_dir=images_dir,
    )


@router.post("/{conversation_id}/message")
async def chat(
    conversation_id: str,
    body: ChatMessageRequest,
    service: ChatService = Depends(get_chat_service),
):
    async def event_generator():
        async for event in service.stream_chat(conversation_id, body.content):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
