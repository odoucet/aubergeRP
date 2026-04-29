from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sqlmodel import Session, func, select

from ..db_models import ConversationRow, MediaRow, MessageRow


class MediaNotFoundError(KeyError):
    pass


class MediaService:
    def __init__(self, data_dir: Path | str) -> None:
        self._data_dir = Path(data_dir)

    def _get_session(self) -> Session:
        from ..database import get_engine

        return Session(get_engine(self._data_dir))

    def list_media(
        self,
        page: int = 1,
        per_page: int = 50,
        media_type: str | None = None,
    ) -> tuple[list[MediaRow], int]:
        with self._get_session() as session:
            created_at_expr = cast(Any, MediaRow.created_at)

            count_query = select(func.count()).select_from(MediaRow)
            if media_type:
                count_query = count_query.where(MediaRow.media_type == media_type)
            total = session.exec(count_query).one()

            rows_query = select(MediaRow).order_by(created_at_expr.desc())
            if media_type:
                rows_query = rows_query.where(MediaRow.media_type == media_type)
            offset = (page - 1) * per_page
            rows = list(session.exec(rows_query.offset(offset).limit(per_page)))
            return rows, total

    def record_generated_media(
        self,
        conversation_id: str,
        message_id: str,
        media_items: list[tuple[str, str]],
    ) -> None:
        if not media_items:
            return

        with self._get_session() as session:
            conv = session.get(ConversationRow, conversation_id)
            owner = conv.owner if conv is not None else ""
            now = datetime.now(UTC)

            for media_url, prompt in media_items:
                if not media_url:
                    continue
                media_type = _infer_media_type(media_url)
                row = MediaRow(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    message_id=message_id,
                    owner=owner,
                    media_type=media_type,
                    media_url=media_url,
                    prompt=prompt,
                    generated_via_connector=True,
                    created_at=now,
                )
                session.add(row)
            session.commit()

    def delete_media(self, media_id: str) -> None:
        with self._get_session() as session:
            row = session.get(MediaRow, media_id)
            if row is None:
                raise MediaNotFoundError(f"Media '{media_id}' not found")

            duplicate_count = len(
                list(
                    session.exec(
                        select(MediaRow.id).where(
                            MediaRow.media_url == row.media_url,
                            MediaRow.id != row.id,
                        )
                    )
                )
            )

            message = session.get(MessageRow, row.message_id) if row.message_id else None
            if message is not None:
                try:
                    images = json.loads(message.images_json or "[]")
                except Exception:
                    images = []
                if isinstance(images, list):
                    message.images_json = json.dumps(
                        [img for img in images if img != row.media_url], ensure_ascii=False
                    )
                    session.add(message)

            session.delete(row)
            session.commit()

        if duplicate_count == 0:
            file_path = _resolve_local_media_path(self._data_dir, row.media_url)
            if file_path is not None and file_path.exists():
                file_path.unlink()


def _infer_media_type(media_url: str) -> str:
    lower = media_url.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return "image"
    if lower.endswith((".mp4", ".webm", ".ogg", ".mov")):
        return "video"
    if lower.endswith((".mp3", ".wav", ".ogg", ".m4a", ".flac")):
        return "audio"
    return "image"


def _resolve_local_media_path(data_dir: Path, media_url: str) -> Path | None:
    if not media_url.startswith("/api/images/"):
        return None

    parts = media_url.strip("/").split("/")
    # /api/images/{session_token}/{filename}
    if len(parts) != 4 or parts[0] != "api" or parts[1] != "images":
        return None

    session_token = parts[2]
    filename = parts[3]
    if not session_token or not filename:
        return None

    candidate = (data_dir / "images" / session_token / filename).resolve()
    images_root = (data_dir / "images").resolve()
    try:
        inside_root = os.path.commonpath([str(images_root), str(candidate)]) == str(images_root)
    except ValueError:
        inside_root = False

    if not inside_root:
        return None
    return candidate
