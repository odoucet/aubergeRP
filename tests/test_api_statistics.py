from __future__ import annotations

from fastapi.testclient import TestClient

from aubergeRP.config import get_config, reset_config
from aubergeRP.main import create_app
from aubergeRP.models.character import CharacterData
from aubergeRP.services.character_service import CharacterService
from aubergeRP.services.conversation_service import ConversationService
from aubergeRP.services.statistics_service import StatisticsService


def test_statistics_endpoint_returns_usage_aggregates(tmp_path):
    reset_config()
    get_config().app.data_dir = str(tmp_path)

    char_svc = CharacterService(data_dir=tmp_path)
    conv_svc = ConversationService(data_dir=tmp_path, character_service=char_svc)
    stats_svc = StatisticsService(data_dir=tmp_path)

    char = char_svc.create_character(CharacterData(name="Elara", description="Ranger"))
    conv = conv_svc.create_conversation(char.id)
    conv_svc.append_message(conv.id, "user", "Hello there")

    stats_svc.record_text_call(
        conversation_id=conv.id,
        connector_id="conn-1",
        connector_name="OpenAI Main",
        connector_backend="openai_api",
        request_tokens=120,
        response_tokens=56,
        response_time_ms=480,
        success=True,
    )

    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/statistics/?days=30&top=10")

    assert resp.status_code == 200
    data = resp.json()

    summary = data["summary"]
    assert summary["total_conversations"] >= 1
    assert summary["total_messages"] >= 1
    assert summary["llm_calls"] == 1
    assert summary["tokens_in"] == 120
    assert summary["tokens_out"] == 56
    assert summary["avg_latency_ms"] == 480.0

    assert len(data["by_connector"]) >= 1
    top_connector = data["by_connector"][0]
    assert top_connector["backend"] == "openai_api"
    assert top_connector["llm_calls"] == 1

    assert len(data["by_conversation"]) >= 1
    first_conv = data["by_conversation"][0]
    assert first_conv["conversation_id"] == conv.id
