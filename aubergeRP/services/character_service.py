from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models.character import CharacterCard, CharacterData, CharacterSummary
from ..utils.file_storage import read_json, write_json
from ..utils.png_metadata import read_png_metadata, write_png_metadata


class CharacterNotFoundError(KeyError):
    pass


class CharacterImportError(ValueError):
    pass


_EMPTY_AUBERGE_EXT: dict[str, Any] = {"image_prompt_prefix": "", "negative_prompt": ""}


def _ensure_auberge_ext(extensions: dict[str, Any]) -> None:
    extensions.setdefault("aubergeRP", dict(_EMPTY_AUBERGE_EXT))


def _upgrade_v1_to_v2(v1: dict[str, Any]) -> dict[str, Any]:
    v1_fields = [
        "name", "description", "personality", "first_mes", "mes_example",
        "scenario", "system_prompt", "post_history_instructions",
        "creator", "creator_notes", "character_version", "tags", "extensions",
    ]
    data: dict[str, Any] = {k: v1[k] for k in v1_fields if k in v1}
    return {"spec": "chara_card_v2", "spec_version": "2.0", "data": data}


def _normalize_to_v2(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("spec") == "chara_card_v2" and "data" in raw:
        return raw
    return _upgrade_v1_to_v2(raw)


class CharacterService:
    def __init__(
        self,
        data_dir: Path | str,
        default_avatar: Path | str | None = None,
    ) -> None:
        self._chars_dir = Path(data_dir) / "characters"
        self._avatars_dir = Path(data_dir) / "avatars"
        self._default_avatar = (
            Path(default_avatar) if default_avatar
            else Path("frontend/assets/default-avatar.png")
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _char_path(self, character_id: str) -> Path:
        return self._chars_dir / f"{character_id}.json"

    def _avatar_path(self, character_id: str) -> Path:
        return self._avatars_dir / f"{character_id}.png"

    def _load(self, character_id: str) -> CharacterCard:
        path = self._char_path(character_id)
        if not path.exists():
            raise CharacterNotFoundError(f"Character '{character_id}' not found")
        return CharacterCard(**read_json(path))

    def _save(self, card: CharacterCard) -> None:
        self._chars_dir.mkdir(parents=True, exist_ok=True)
        write_json(self._char_path(card.id), card.model_dump(mode="json"))

    @staticmethod
    def _summary(card: CharacterCard) -> CharacterSummary:
        return CharacterSummary(
            id=card.id,
            name=card.data.name,
            description=card.data.description,
            avatar_url=f"/api/characters/{card.id}/avatar",
            has_avatar=card.has_avatar,
            tags=card.data.tags,
            created_at=card.created_at,
            updated_at=card.updated_at,
        )

    def _build_card(
        self,
        data: CharacterData,
        character_id: str | None = None,
        created_at: datetime | None = None,
        has_avatar: bool = False,
    ) -> CharacterCard:
        now = datetime.now(timezone.utc)
        ext = dict(data.extensions)
        _ensure_auberge_ext(ext)
        data = data.model_copy(update={"extensions": ext})
        return CharacterCard(
            id=character_id or str(uuid.uuid4()),
            has_avatar=has_avatar,
            created_at=created_at or now,
            updated_at=now,
            data=data,
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def list_characters(self) -> list[CharacterSummary]:
        if not self._chars_dir.exists():
            return []
        result = []
        for path in sorted(self._chars_dir.glob("*.json")):
            try:
                result.append(self._summary(CharacterCard(**read_json(path))))
            except Exception:
                pass
        return result

    def get_character(self, character_id: str) -> CharacterCard:
        return self._load(character_id)

    def create_character(self, data: CharacterData) -> CharacterCard:
        card = self._build_card(data)
        self._save(card)
        return card

    def update_character(self, character_id: str, data: CharacterData) -> CharacterCard:
        existing = self._load(character_id)
        ext = dict(data.extensions)
        _ensure_auberge_ext(ext)
        data = data.model_copy(update={"extensions": ext})
        updated = existing.model_copy(update={
            "data": data,
            "updated_at": datetime.now(timezone.utc),
        })
        self._save(updated)
        return updated

    def delete_character(self, character_id: str) -> None:
        self._load(character_id)
        self._char_path(character_id).unlink()
        avatar = self._avatar_path(character_id)
        if avatar.exists():
            avatar.unlink()

    def duplicate_character(self, character_id: str) -> CharacterCard:
        original = self._load(character_id)
        now = datetime.now(timezone.utc)
        new_id = str(uuid.uuid4())
        orig_avatar = self._avatar_path(character_id)
        has_avatar = orig_avatar.exists()
        if has_avatar:
            self._avatars_dir.mkdir(parents=True, exist_ok=True)
            self._avatar_path(new_id).write_bytes(orig_avatar.read_bytes())
        card = original.model_copy(update={
            "id": new_id,
            "has_avatar": has_avatar,
            "created_at": now,
            "updated_at": now,
        })
        self._save(card)
        return card

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_character_json(self, content: bytes, filename: str = "") -> CharacterCard:
        try:
            raw = json.loads(content)
        except json.JSONDecodeError as exc:
            raise CharacterImportError(f"Invalid JSON: {exc}") from exc
        return self._create_from_raw(raw)

    def import_character_png(self, content: bytes) -> CharacterCard:
        try:
            card_dict = read_png_metadata(content)
        except Exception as exc:
            raise CharacterImportError(f"Cannot read PNG: {exc}") from exc
        if card_dict is None:
            raise CharacterImportError("PNG has no embedded character card ('chara' chunk missing)")
        card = self._create_from_raw(card_dict)
        # The full PNG becomes the avatar
        self.save_avatar(card.id, content)
        return self._load(card.id)

    def _create_from_raw(self, raw: dict[str, Any]) -> CharacterCard:
        v2 = _normalize_to_v2(raw)
        data_dict: dict[str, Any] = dict(v2.get("data", {}))
        if not data_dict.get("name"):
            raise CharacterImportError("Missing required field 'name'")
        if not data_dict.get("description"):
            raise CharacterImportError("Missing required field 'description'")
        _ensure_auberge_ext(data_dict.setdefault("extensions", {}) or data_dict["extensions"])
        return self.create_character(CharacterData(**data_dict))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_character_json(self, character_id: str) -> dict[str, Any]:
        card = self._load(character_id)
        return {
            "spec": card.spec,
            "spec_version": card.spec_version,
            "data": card.data.model_dump(mode="json"),
        }

    def export_character_png(self, character_id: str) -> bytes:
        card_dict = self.export_character_json(character_id)
        avatar = self._avatar_path(character_id)
        carrier = avatar if avatar.exists() else self._default_avatar
        if not carrier.exists():
            raise CharacterImportError(
                f"No avatar found and default-avatar.png is missing ({carrier})"
            )
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            write_png_metadata(carrier, tmp, card_dict)
            return Path(tmp).read_bytes()
        finally:
            Path(tmp).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Avatar
    # ------------------------------------------------------------------

    def save_avatar(self, character_id: str, content: bytes) -> None:
        card = self._load(character_id)
        self._avatars_dir.mkdir(parents=True, exist_ok=True)
        self._avatar_path(character_id).write_bytes(content)
        if not card.has_avatar:
            self._save(card.model_copy(update={
                "has_avatar": True,
                "updated_at": datetime.now(timezone.utc),
            }))

    def get_avatar_path(self, character_id: str) -> Path | None:
        path = self._avatar_path(character_id)
        return path if path.exists() else None
