"""Integration tests for /api/chat via FastAPI TestClient with mocked ChatService."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi.testclient import TestClient

from aubergeRP.main import create_app
from aubergeRP.routers.chat import get_chat_service


def parse_sse(text: str) -> list[dict[str, Any]]:
    events = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


class _MockService:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = events

    async def stream_chat(
        self, conversation_id: str, content: str, user_name: str = "User"
    ) -> AsyncIterator[dict[str, Any]]:
        for event in self._events:
            yield event


def _make_client(events: list[dict[str, Any]]) -> TestClient:
    app = create_app()
    svc = _MockService(events)
    app.dependency_overrides[get_chat_service] = lambda: svc
    return TestClient(app)


# ---------------------------------------------------------------------------
# Basic SSE format
# ---------------------------------------------------------------------------

def test_chat_returns_200():
    client = _make_client([{"type": "done", "message_id": "m1", "full_content": "", "images": []}])
    resp = client.post("/api/chat/conv-1/message", json={"content": "Hello"})
    assert resp.status_code == 200


def test_chat_content_type_is_event_stream():
    client = _make_client([{"type": "done", "message_id": "m1", "full_content": "", "images": []}])
    resp = client.post("/api/chat/conv-1/message", json={"content": "Hello"})
    assert "text/event-stream" in resp.headers["content-type"]


def test_chat_missing_content_is_422():
    client = _make_client([])
    resp = client.post("/api/chat/conv-1/message", json={})
    assert resp.status_code == 422


def test_chat_empty_content_is_422():
    client = _make_client([])
    resp = client.post("/api/chat/conv-1/message", json={"content": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Token events
# ---------------------------------------------------------------------------

def test_chat_token_events():
    client = _make_client([
        {"type": "token", "content": "Hello"},
        {"type": "token", "content": " world"},
        {"type": "done", "message_id": "m1", "full_content": "Hello world", "images": []},
    ])
    resp = client.post("/api/chat/conv-1/message", json={"content": "Hi"})
    events = parse_sse(resp.text)
    tokens = [e for e in events if e["type"] == "token"]
    assert len(tokens) == 2
    assert tokens[0]["content"] == "Hello"
    assert tokens[1]["content"] == " world"


def test_chat_done_event_shape():
    client = _make_client([
        {"type": "done", "message_id": "msg-42", "full_content": "Hi", "images": []},
    ])
    resp = client.post("/api/chat/conv-1/message", json={"content": "Hello"})
    events = parse_sse(resp.text)
    done = events[-1]
    assert done["type"] == "done"
    assert done["message_id"] == "msg-42"
    assert done["full_content"] == "Hi"
    assert done["images"] == []


# ---------------------------------------------------------------------------
# Image events
# ---------------------------------------------------------------------------

def test_chat_image_start_event():
    client = _make_client([
        {"type": "image_start", "generation_id": "gen-1", "prompt": "a cat"},
        {"type": "image_complete", "generation_id": "gen-1", "image_url": "/api/images/0/cat.png"},
        {"type": "done", "message_id": "m1", "full_content": "", "images": ["/api/images/0/cat.png"]},
    ])
    resp = client.post("/api/chat/conv-1/message", json={"content": "draw"})
    events = parse_sse(resp.text)
    start = next(e for e in events if e["type"] == "image_start")
    assert start["prompt"] == "a cat"
    assert start["generation_id"] == "gen-1"


def test_chat_image_complete_event():
    client = _make_client([
        {"type": "image_start", "generation_id": "gen-1", "prompt": "x"},
        {"type": "image_complete", "generation_id": "gen-1", "image_url": "/api/images/0/x.png"},
        {"type": "done", "message_id": "m1", "full_content": "", "images": ["/api/images/0/x.png"]},
    ])
    resp = client.post("/api/chat/conv-1/message", json={"content": "draw"})
    events = parse_sse(resp.text)
    complete = next(e for e in events if e["type"] == "image_complete")
    assert complete["image_url"] == "/api/images/0/x.png"
    assert complete["generation_id"] == "gen-1"


def test_chat_image_failed_event():
    client = _make_client([
        {"type": "image_start", "generation_id": "gen-1", "prompt": "x"},
        {"type": "image_failed", "generation_id": "gen-1", "detail": "timeout"},
        {"type": "done", "message_id": "m1", "full_content": "", "images": []},
    ])
    resp = client.post("/api/chat/conv-1/message", json={"content": "draw"})
    events = parse_sse(resp.text)
    failed = next(e for e in events if e["type"] == "image_failed")
    assert failed["detail"] == "timeout"


def test_chat_done_includes_image_urls():
    client = _make_client([
        {"type": "image_complete", "generation_id": "g1", "image_url": "/api/images/0/a.png"},
        {"type": "done", "message_id": "m1", "full_content": "", "images": ["/api/images/0/a.png"]},
    ])
    resp = client.post("/api/chat/conv-1/message", json={"content": "Hi"})
    events = parse_sse(resp.text)
    done = next(e for e in events if e["type"] == "done")
    assert "/api/images/0/a.png" in done["images"]


# ---------------------------------------------------------------------------
# Error events
# ---------------------------------------------------------------------------

def test_chat_error_event():
    client = _make_client([
        {"type": "error", "detail": "No active text connector configured"},
    ])
    resp = client.post("/api/chat/conv-1/message", json={"content": "Hi"})
    assert resp.status_code == 200  # SSE always 200
    events = parse_sse(resp.text)
    error = next(e for e in events if e["type"] == "error")
    assert "connector" in error["detail"].lower()


# ---------------------------------------------------------------------------
# SSE framing
# ---------------------------------------------------------------------------

def test_each_event_is_data_prefixed():
    client = _make_client([
        {"type": "token", "content": "Hi"},
        {"type": "done", "message_id": "m1", "full_content": "Hi", "images": []},
    ])
    resp = client.post("/api/chat/conv-1/message", json={"content": "Hello"})
    for line in resp.text.splitlines():
        line = line.strip()
        if line:
            assert line.startswith("data: ")


def test_events_are_valid_json():
    client = _make_client([
        {"type": "token", "content": "Test"},
        {"type": "done", "message_id": "m1", "full_content": "Test", "images": []},
    ])
    resp = client.post("/api/chat/conv-1/message", json={"content": "Hello"})
    events = parse_sse(resp.text)
    assert len(events) == 2
    for e in events:
        assert "type" in e


# ---------------------------------------------------------------------------
# generate-image endpoint
# ---------------------------------------------------------------------------

class _MockServiceWithSceneImage:
    def __init__(self, events: list[dict]) -> None:
        self._events = events

    async def stream_chat(self, conversation_id, content, user_name="User"):
        return
        yield  # make it an async generator

    async def generate_scene_image(self, conversation_id):
        for event in self._events:
            yield event


def _make_gen_image_client(events: list[dict]) -> TestClient:
    app = create_app()
    svc = _MockServiceWithSceneImage(events)
    app.dependency_overrides[get_chat_service] = lambda: svc
    return TestClient(app)


def test_generate_image_returns_200():
    client = _make_gen_image_client([
        {"type": "image_start", "generation_id": "g1", "prompt": ""},
        {"type": "image_complete", "generation_id": "g1", "image_url": "/api/images/tok/img.png"},
    ])
    resp = client.post("/api/chat/conv-1/generate-image")
    assert resp.status_code == 200


def test_generate_image_content_type_is_event_stream():
    client = _make_gen_image_client([
        {"type": "image_start", "generation_id": "g1", "prompt": ""},
        {"type": "image_complete", "generation_id": "g1", "image_url": "/api/images/tok/img.png"},
    ])
    resp = client.post("/api/chat/conv-1/generate-image")
    assert "text/event-stream" in resp.headers["content-type"]


def test_generate_image_emits_image_start_and_complete():
    client = _make_gen_image_client([
        {"type": "image_start", "generation_id": "g1", "prompt": ""},
        {"type": "image_complete", "generation_id": "g1", "image_url": "/api/images/tok/img.png"},
    ])
    resp = client.post("/api/chat/conv-1/generate-image")
    events = parse_sse(resp.text)
    types = [e["type"] for e in events]
    assert "image_start" in types
    assert "image_complete" in types


def test_generate_image_emits_image_failed_on_error():
    client = _make_gen_image_client([
        {"type": "image_start", "generation_id": "g1", "prompt": ""},
        {"type": "image_failed", "generation_id": "g1", "detail": "No image connector"},
    ])
    resp = client.post("/api/chat/conv-1/generate-image")
    events = parse_sse(resp.text)
    failed = next(e for e in events if e["type"] == "image_failed")
    assert "connector" in failed["detail"].lower()


def test_generate_image_no_request_body_required():
    """The endpoint must work without a JSON body."""
    client = _make_gen_image_client([
        {"type": "image_failed", "generation_id": "g1", "detail": "No connector"},
    ])
    # No json= kwarg → body is empty
    resp = client.post("/api/chat/conv-x/generate-image")
    assert resp.status_code == 200
