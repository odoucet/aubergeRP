from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


class ConnectorTestChatRequest(BaseModel):
    """Request to test a connector with sample chat parameters."""
    message: str = Field(..., min_length=1, description="Sample message to send")
    temperature: float | None = Field(default=None, description="Sampling temperature")
    top_p: float | None = Field(default=None, description="Nucleus sampling parameter")
    presence_penalty: float | None = Field(default=None, description="Presence penalty")
    frequency_penalty: float | None = Field(default=None, description="Frequency penalty")
    extra_body: dict[str, Any] | None = Field(default=None, description="Extra parameters")


class TokenEvent(BaseModel):
    content: str


class ImageStartEvent(BaseModel):
    generation_id: str
    prompt: str


class ImageCompleteEvent(BaseModel):
    generation_id: str
    image_url: str


class ImageFailedEvent(BaseModel):
    generation_id: str
    detail: str


class DoneEvent(BaseModel):
    message_id: str
    full_content: str
    images: list[str] = Field(default_factory=list)


class ErrorEvent(BaseModel):
    detail: str
