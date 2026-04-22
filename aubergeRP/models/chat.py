from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


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
