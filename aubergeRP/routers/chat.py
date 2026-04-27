from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse

from ..event_bus import EventBus, get_event_bus
from ..models.chat import ChatMessageRequest
from ..services.chat_service import ChatService
from ..services.character_service import CharacterService
from ..services.conversation_service import ConversationService
from ..connectors.manager import ConnectorManager

router = APIRouter(prefix="/chat", tags=["chat"])

_KEEPALIVE_TIMEOUT = 30.0  # seconds between SSE keepalive comments


def get_session_token(x_session_token: str = Header(default="")) -> str:
    return x_session_token


def get_chat_service(
    session_token: str = Depends(get_session_token),
) -> ChatService:
    from ..config import get_config
    config = get_config()
    data_dir = config.app.data_dir
    char_svc = CharacterService(data_dir=data_dir)
    conv_svc = ConversationService(data_dir=data_dir, character_service=char_svc)
    manager = ConnectorManager(data_dir=data_dir, config=config)
    images_dir = Path(data_dir) / "images" / (session_token or "anonymous")
    return ChatService(
        conversation_service=conv_svc,
        character_service=char_svc,
        connector_manager=manager,
        images_dir=images_dir,
        session_token=session_token or "anonymous",
    )


@router.post("/{conversation_id}/message")
async def chat(
    conversation_id: str,
    body: ChatMessageRequest,
    session_token: str = Depends(get_session_token),
    service: ChatService = Depends(get_chat_service),
    bus: EventBus = Depends(get_event_bus),
):
    async def event_generator():
        async for event in service.stream_chat(conversation_id, body.content):
            await bus.publish(session_token, conversation_id, event)
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{conversation_id}/events")
async def chat_events(
    conversation_id: str,
    session_token: str = "",
    bus: EventBus = Depends(get_event_bus),
):
    """Long-lived SSE endpoint for multi-browser event delivery.

    Other browser tabs sharing the same session token subscribe here and
    receive every event published during chat, without having to be the tab
    that sent the message.  The connection is kept open with periodic
    keepalive comments so that EventSource auto-reconnect is not triggered.

    The session token is passed as the ``session_token`` query parameter
    (instead of a header) because the browser ``EventSource`` API does not
    support custom request headers.
    """
    q = bus.subscribe(session_token, conversation_id)

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=_KEEPALIVE_TIMEOUT)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            bus.unsubscribe(session_token, conversation_id, q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
