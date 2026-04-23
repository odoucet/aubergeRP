import json
import pytest
import httpx
import respx

from aubergeRP.connectors.openai_text import OpenAITextConnector
from aubergeRP.models.connector import OpenAITextConfig

BASE_URL = "http://localhost:11434/v1"


def make_connector(**overrides) -> OpenAITextConnector:
    defaults = dict(base_url=BASE_URL, api_key="test-key", model="llama3")
    defaults.update(overrides)
    return OpenAITextConnector(OpenAITextConfig(**defaults))


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------


@respx.mock
async def test_connection_success():
    respx.get(f"{BASE_URL}/models").respond(
        200,
        json={"data": [{"id": "llama3"}, {"id": "mistral"}]},
    )
    result = await make_connector().test_connection()
    assert result["connected"] is True
    assert "llama3" in result["details"]["models_available"]
    assert "mistral" in result["details"]["models_available"]


@respx.mock
async def test_connection_http_error():
    respx.get(f"{BASE_URL}/models").respond(401)
    result = await make_connector().test_connection()
    assert result["connected"] is False
    assert "error" in result["details"]


@respx.mock
async def test_connection_network_error():
    respx.get(f"{BASE_URL}/models").mock(side_effect=httpx.ConnectError("refused"))
    result = await make_connector().test_connection()
    assert result["connected"] is False


# ---------------------------------------------------------------------------
# stream_chat_completion
# ---------------------------------------------------------------------------

def _sse_body(*contents: str, finish: bool = True) -> bytes:
    lines = []
    for c in contents:
        chunk = {"choices": [{"delta": {"content": c}}]}
        lines.append(f"data: {json.dumps(chunk)}")
        lines.append("")
    if finish:
        finish_chunk = {"choices": [{"delta": {}, "finish_reason": "stop"}]}
        lines.append(f"data: {json.dumps(finish_chunk)}")
        lines.append("")
        lines.append("data: [DONE]")
        lines.append("")
    return "\n".join(lines).encode()


@respx.mock
async def test_stream_yields_tokens():
    respx.post(f"{BASE_URL}/chat/completions").respond(
        200,
        content=_sse_body("Hello", " World"),
        headers={"content-type": "text/event-stream"},
    )
    connector = make_connector()
    tokens = []
    async for token in connector.stream_chat_completion([{"role": "user", "content": "Hi"}]):
        tokens.append(token)
    assert tokens == ["Hello", " World"]


@respx.mock
async def test_stream_uses_config_defaults():
    route = respx.post(f"{BASE_URL}/chat/completions").respond(
        200,
        content=_sse_body("ok"),
        headers={"content-type": "text/event-stream"},
    )
    connector = make_connector(model="phi3", max_tokens=512, temperature=0.5)
    async for _ in connector.stream_chat_completion([{"role": "user", "content": "hi"}]):
        pass
    body = json.loads(route.calls[0].request.content)
    assert body["model"] == "phi3"
    assert body["max_tokens"] == 512
    assert body["temperature"] == 0.5
    assert body["stream"] is True


@respx.mock
async def test_stream_overrides_model_and_params():
    route = respx.post(f"{BASE_URL}/chat/completions").respond(
        200,
        content=_sse_body("ok"),
        headers={"content-type": "text/event-stream"},
    )
    connector = make_connector()
    async for _ in connector.stream_chat_completion(
        [{"role": "user", "content": "hi"}],
        model="mistral",
        temperature=0.1,
        max_tokens=256,
    ):
        pass
    body = json.loads(route.calls[0].request.content)
    assert body["model"] == "mistral"
    assert body["temperature"] == 0.1
    assert body["max_tokens"] == 256


@respx.mock
async def test_stream_skips_empty_delta():
    body = (
        b'data: {"choices": [{"delta": {"content": "A"}}]}\n\n'
        b'data: {"choices": [{"delta": {}}]}\n\n'
        b"data: [DONE]\n\n"
    )
    respx.post(f"{BASE_URL}/chat/completions").respond(
        200, content=body, headers={"content-type": "text/event-stream"}
    )
    tokens = []
    async for token in make_connector().stream_chat_completion([]):
        tokens.append(token)
    assert tokens == ["A"]


@respx.mock
async def test_stream_raises_on_http_error():
    respx.post(f"{BASE_URL}/chat/completions").respond(502)
    with pytest.raises(httpx.HTTPStatusError):
        async for _ in make_connector().stream_chat_completion([]):
            pass


@respx.mock
async def test_stream_sends_authorization_header():
    route = respx.post(f"{BASE_URL}/chat/completions").respond(
        200, content=_sse_body("tok"), headers={"content-type": "text/event-stream"}
    )
    async for _ in make_connector(api_key="sk-secret").stream_chat_completion([]):
        pass
    assert route.calls[0].request.headers["authorization"] == "Bearer sk-secret"
