"""Migration 003 — add media library table and backfill existing image entries."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlmodel import Session


def migrate(session: Session) -> None:
    """Create media_library table and import existing message image URLs."""
    session.exec(
        text(
            """
        CREATE TABLE IF NOT EXISTS media_library (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            message_id TEXT NOT NULL DEFAULT '',
            owner TEXT NOT NULL DEFAULT '',
            media_type TEXT NOT NULL DEFAULT 'image',
            media_url TEXT NOT NULL,
            prompt TEXT NOT NULL DEFAULT '',
            generated_via_connector BOOLEAN NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
        )
    )
    session.exec(
        text(
            "CREATE INDEX IF NOT EXISTS ix_media_library_conversation_id ON media_library (conversation_id)"
        )
    )
    session.exec(
        text(
            "CREATE INDEX IF NOT EXISTS ix_media_library_message_id ON media_library (message_id)"
        )
    )
    session.exec(
        text("CREATE INDEX IF NOT EXISTS ix_media_library_owner ON media_library (owner)")
    )

    rows = session.exec(
        text(
            """
            SELECT m.id, m.conversation_id, m.images_json, m.timestamp, COALESCE(c.owner, '')
            FROM messages AS m
            LEFT JOIN conversations AS c ON c.id = m.conversation_id
            WHERE m.images_json IS NOT NULL AND m.images_json != '[]'
            """
        )
    ).all()

    for message_id, conversation_id, images_json, timestamp, owner in rows:
        try:
            images = json.loads(images_json or "[]")
        except Exception:
            continue

        if not isinstance(images, list):
            continue

        created_at = _normalize_timestamp(timestamp)
        for media_url in images:
            if not isinstance(media_url, str) or not media_url:
                continue
            session.execute(
                text(
                    """
                    INSERT INTO media_library (
                        id, conversation_id, message_id, owner, media_type,
                        media_url, prompt, generated_via_connector, created_at
                    ) VALUES (
                        :id, :conversation_id, :message_id, :owner, :media_type,
                        :media_url, :prompt, :generated_via_connector, :created_at
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "owner": owner,
                    "media_type": "image",
                    "media_url": media_url,
                    "prompt": "",
                    "generated_via_connector": 1,
                    "created_at": created_at,
                },
            )


def _normalize_timestamp(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return dt.isoformat()
    return datetime.now(UTC).isoformat()
