from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    images: list[str] = Field(default_factory=list)
    timestamp: datetime


class Conversation(BaseModel):
    id: str
    character_id: str
    character_name: str
    title: str
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ConversationSummary(BaseModel):
    id: str
    character_id: str
    character_name: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationCreate(BaseModel):
    character_id: str
