from __future__ import annotations

from fastapi.testclient import TestClient

from aubergeRP.config import get_config, reset_config
from aubergeRP.main import create_app
from aubergeRP.models.character import CharacterData
from aubergeRP.services.character_service import CharacterService
from aubergeRP.services.conversation_service import ConversationService
from aubergeRP.services.media_service import MediaService


def _bootstrap(tmp_path):
    char_svc = CharacterService(data_dir=tmp_path)
    conv_svc = ConversationService(data_dir=tmp_path, character_service=char_svc)
    media_svc = MediaService(data_dir=tmp_path)

    char = char_svc.create_character(CharacterData(name="Mina", description="Mage"))
    conv = conv_svc.create_conversation(char.id, owner="session-1")
    msg = conv_svc.append_message(
        conv.id,
        "assistant",
        "Here is the image",
        images=["/api/images/session-1/example.png"],
    )

    images_dir = tmp_path / "images" / "session-1"
    images_dir.mkdir(parents=True, exist_ok=True)
    (images_dir / "example.png").write_bytes(b"PNGDATA")

    media_svc.record_generated_media(
        conversation_id=conv.id,
        message_id=msg.id,
        media_items=[("/api/images/session-1/example.png", "a fantasy tavern at dusk")],
    )

    return conv_svc


def test_media_list_endpoint_returns_prompt(tmp_path):
    reset_config()
    get_config().app.data_dir = str(tmp_path)
    _bootstrap(tmp_path)

    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/media/")

    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 1
    assert payload[0]["media_type"] == "image"
    assert payload[0]["prompt"] == "a fantasy tavern at dusk"
    assert payload[0]["media_url"] == "/api/images/session-1/example.png"


def test_media_delete_endpoint_removes_db_message_link_and_file(tmp_path):
    reset_config()
    get_config().app.data_dir = str(tmp_path)
    conv_svc = _bootstrap(tmp_path)

    app = create_app()
    with TestClient(app) as client:
        listed = client.get("/api/media/")
        media_id = listed.json()[0]["id"]

        resp = client.delete(f"/api/media/{media_id}")
        assert resp.status_code == 204

        listed_after = client.get("/api/media/")
        assert listed_after.status_code == 200
        assert listed_after.json() == []

    conv = conv_svc.list_conversations()[0]
    full = conv_svc.get_conversation(conv.id)
    assistant_with_images = [m for m in full.messages if m.role == "assistant" and "Here is the image" in m.content]
    assert len(assistant_with_images) == 1
    assert assistant_with_images[0].images == []
    assert not (tmp_path / "images" / "session-1" / "example.png").exists()
