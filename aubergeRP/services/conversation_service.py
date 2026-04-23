from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..models.conversation import Conversation, ConversationSummary, Message
from ..services.character_service import CharacterService
from ..utils.file_storage import read_json, write_json

_MACRO_RE = re.compile(r"\{\{(\w+)\}\}")


class ConversationNotFoundError(KeyError):
    pass


def resolve_macros(text: str, char_name: str, user_name: str = "User", **extra: str) -> str:
    mapping: dict[str, str] = {"char": char_name, "user": user_name, **extra}
    return _MACRO_RE.sub(lambda m: mapping.get(m.group(1), m.group(0)), text)


class ConversationService:
    def __init__(
        self,
        data_dir: "Path | str",
        character_service: CharacterService,
    ) -> None:
        self._convs_dir = Path(data_dir) / "conversations"
        self._character_service = character_service

    def _conv_path(self, conversation_id: str) -> Path:
        return self._convs_dir / f"{conversation_id}.json"

    def _load(self, conversation_id: str) -> Conversation:
        path = self._conv_path(conversation_id)
        if not path.exists():
            raise ConversationNotFoundError(f"Conversation '{conversation_id}' not found")
        return Conversation(**read_json(path))

    def _save(self, conv: Conversation) -> None:
        self._convs_dir.mkdir(parents=True, exist_ok=True)
        write_json(self._conv_path(conv.id), conv.model_dump(mode="json"))

    @staticmethod
    def _summary(conv: Conversation) -> ConversationSummary:
        return ConversationSummary(
            id=conv.id,
            character_id=conv.character_id,
            character_name=conv.character_name,
            title=conv.title,
            message_count=len(conv.messages),
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    def create_conversation(
        self, character_id: str, user_name: str = "User"
    ) -> Conversation:
        char = self._character_service.get_character(character_id)
        now = datetime.now(timezone.utc)
        messages: list[Message] = []
        if char.data.first_mes:
            content = resolve_macros(char.data.first_mes, char.data.name, user_name)
            messages.append(Message(
                id=str(uuid.uuid4()),
                role="assistant",
                content=content,
                timestamp=now,
            ))
        conv = Conversation(
            id=str(uuid.uuid4()),
            character_id=character_id,
            character_name=char.data.name,
            title=char.data.name,
            messages=messages,
            created_at=now,
            updated_at=now,
        )
        self._save(conv)
        return conv

    def get_conversation(self, conversation_id: str) -> Conversation:
        return self._load(conversation_id)

    def list_conversations(
        self, character_id: "Optional[str]" = None
    ) -> list[ConversationSummary]:
        if not self._convs_dir.exists():
            return []
        result = []
        for path in sorted(self._convs_dir.glob("*.json")):
            try:
                conv = Conversation(**read_json(path))
                if character_id is None or conv.character_id == character_id:
                    result.append(self._summary(conv))
            except Exception:
                pass
        return result

    def delete_conversation(self, conversation_id: str) -> None:
        self._load(conversation_id)
        self._conv_path(conversation_id).unlink()

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        images: "Optional[list[str]]" = None,
    ) -> Message:
        conv = self._load(conversation_id)
        now = datetime.now(timezone.utc)
        msg = Message(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            images=images or [],
            timestamp=now,
        )
        self._save(conv.model_copy(update={
            "messages": conv.messages + [msg],
            "updated_at": now,
        }))
        return msg
