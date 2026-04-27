"""SQLModel table definitions for aubergeRP.

These are the canonical on-disk representations.  The Pydantic *models*
(CharacterCard, Conversation, …) remain unchanged and are still used for
business logic — service classes convert between the two.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Field, SQLModel


class CharacterRow(SQLModel, table=True):
    """One row per character card."""

    __tablename__ = "characters"

    id: str = Field(primary_key=True)
    has_avatar: bool = False
    spec: str = "chara_card_v2"
    spec_version: str = "2.0"
    # CharacterData serialised as JSON
    data_json: str = Field(default="{}")
    created_at: datetime
    updated_at: datetime

    def get_data(self) -> dict[str, Any]:
        return json.loads(self.data_json)  # type: ignore[no-any-return]


class ConversationRow(SQLModel, table=True):
    """One row per conversation (without its messages)."""

    __tablename__ = "conversations"

    id: str = Field(primary_key=True)
    character_id: str
    character_name: str
    title: str
    owner: str = ""
    created_at: datetime
    updated_at: datetime


class MessageRow(SQLModel, table=True):
    """One row per chat message."""

    __tablename__ = "messages"

    id: str = Field(primary_key=True)
    conversation_id: str = Field(index=True)
    role: str
    content: str
    # list[str] serialised as JSON
    images_json: str = Field(default="[]")
    timestamp: datetime

    def get_images(self) -> list[str]:
        return json.loads(self.images_json)  # type: ignore[no-any-return]

    @staticmethod
    def images_to_json(images: list[str]) -> str:
        return json.dumps(images)


class SchemaMigration(SQLModel, table=True):
    """Tracks which migrations have been applied."""

    __tablename__ = "schema_migrations"

    version: int = Field(primary_key=True)
    description: str = ""
    applied_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
