from __future__ import annotations

import asyncio
from typing import Any


class EventBus:
    """Simple asyncio-based pub/sub bus keyed by (session_token, conversation_id).

    Each subscriber gets its own :class:`asyncio.Queue`.  The server-sent event
    generator for ``GET /api/chat/{id}/events`` keeps a queue alive for the
    lifetime of the HTTP connection so that multiple browser tabs sharing the
    same session token all receive real-time updates.
    """

    def __init__(self) -> None:
        self._subscribers: dict[tuple[str, str], list[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, session_token: str, conversation_id: str) -> asyncio.Queue[dict[str, Any]]:
        key = (session_token, conversation_id)
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.setdefault(key, []).append(q)
        return q

    def unsubscribe(self, session_token: str, conversation_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        key = (session_token, conversation_id)
        subs = self._subscribers.get(key)
        if subs is None:
            return
        try:
            subs.remove(q)
        except ValueError:
            pass
        if not subs:
            self._subscribers.pop(key, None)

    async def publish(self, session_token: str, conversation_id: str, event: dict[str, Any]) -> None:
        key = (session_token, conversation_id)
        for q in list(self._subscribers.get(key, [])):
            await q.put(event)


_bus = EventBus()


def get_event_bus() -> EventBus:
    return _bus
