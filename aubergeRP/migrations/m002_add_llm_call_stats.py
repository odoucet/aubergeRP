"""Migration 002 — add llm_call_stats table for chat usage analytics."""
from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session


def migrate(session: Session) -> None:
    """Create llm_call_stats when upgrading existing databases."""
    session.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS llm_call_stats (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            connector_id TEXT NOT NULL DEFAULT '',
            connector_name TEXT NOT NULL DEFAULT '',
            connector_backend TEXT NOT NULL DEFAULT '',
            request_tokens INTEGER NOT NULL DEFAULT 0,
            response_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            response_time_ms INTEGER NOT NULL DEFAULT 0,
            success BOOLEAN NOT NULL DEFAULT 1,
            error_detail TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
        )
    )
    session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_llm_call_stats_conversation_id ON llm_call_stats (conversation_id)"
        )
    )
