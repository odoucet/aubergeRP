"""Migration 001 — Initial schema creation and JSON flat-file import.

This migration is applied once when the database is first created.  It
imports existing JSON data from the data directory so that users upgrading
from a flat-file installation do not lose their characters or conversations.

The migrate() function is idempotent: if data is already in the DB it is
skipped (insert-or-ignore semantics).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session

from aubergeRP.db_models import CharacterRow, ConversationRow, MessageRow


def migrate(session: Session) -> None:
    """Create tables (already done by SQLModel.metadata.create_all) and import JSON."""
    _import_json_data(session)


# ---------------------------------------------------------------------------
# JSON → SQLite import helpers
# ---------------------------------------------------------------------------

def _import_json_data(session: Session) -> None:
    """Import characters and conversations from JSON flat files, if any exist.

    The data directory is discovered by inspecting the SQLite URL attached to
    the session's engine.  If no JSON files are found this is a no-op.
    """
    engine = session.get_bind()
    db_url = str(engine.url)  # type: ignore[union-attr]
    # sqlite:////abs/path/to/auberge.db  → extract data_dir from DB location
    if not db_url.startswith("sqlite:///"):
        return
    db_path = Path(db_url[len("sqlite:///"):])
    data_dir = db_path.parent

    _import_characters(session, data_dir)
    _import_conversations(session, data_dir)


def _import_characters(session: Session, data_dir: Path) -> None:
    chars_dir = data_dir / "characters"
    if not chars_dir.exists():
        return

    for path in sorted(chars_dir.glob("*.json")):
        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        char_id = raw.get("id")
        if not char_id:
            continue

        # Skip if already imported
        existing = session.get(CharacterRow, char_id)
        if existing is not None:
            continue

        data_blob = raw.get("data", {})
        row = CharacterRow(
            id=char_id,
            has_avatar=bool(raw.get("has_avatar", False)),
            spec=raw.get("spec", "chara_card_v2"),
            spec_version=raw.get("spec_version", "2.0"),
            data_json=json.dumps(data_blob, ensure_ascii=False),
            created_at=_parse_dt(raw.get("created_at")),
            updated_at=_parse_dt(raw.get("updated_at")),
        )
        session.add(row)

    session.flush()


def _import_conversations(session: Session, data_dir: Path) -> None:
    convs_dir = data_dir / "conversations"
    if not convs_dir.exists():
        return

    for path in sorted(convs_dir.glob("*.json")):
        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        conv_id = raw.get("id")
        if not conv_id:
            continue

        # Skip if already imported
        existing = session.get(ConversationRow, conv_id)
        if existing is not None:
            continue

        conv_row = ConversationRow(
            id=conv_id,
            character_id=raw.get("character_id", ""),
            character_name=raw.get("character_name", ""),
            title=raw.get("title", ""),
            owner=raw.get("owner", ""),
            created_at=_parse_dt(raw.get("created_at")),
            updated_at=_parse_dt(raw.get("updated_at")),
        )
        session.add(conv_row)

        for msg in raw.get("messages", []):
            msg_id = msg.get("id")
            if not msg_id:
                continue
            existing_msg = session.get(MessageRow, msg_id)
            if existing_msg is not None:
                continue
            msg_row = MessageRow(
                id=msg_id,
                conversation_id=conv_id,
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                images_json=json.dumps(msg.get("images", []), ensure_ascii=False),
                timestamp=_parse_dt(msg.get("timestamp")),
            )
            session.add(msg_row)

    session.flush()


def _parse_dt(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            pass
    return datetime.now(UTC)
