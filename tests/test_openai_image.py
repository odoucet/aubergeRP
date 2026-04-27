import base64
import json

import httpx
import pytest
import respx

from aubergeRP.connectors.openai_image import OpenAIImageConnector
from aubergeRP.models.connector import OpenAIImageConfig

BASE_OPENROUTER = "https://openrouter.ai/api/v1"
BASE_OPENAI_COMPAT = "https://api.example.com/v1"
IMAGE_URL = "https://cdn.example.com/img/abc.png"
FAKE_PNG = b"\x89PNG\r\n\x1a\nFAKE"


def make_connector(**overrides) -> OpenAIImageConnector:
    defaults = dict(base_url=BASE_OPENROUTER, api_key="sk-or-test")
    defaults.update(overrides)
    return OpenAIImageConnector(OpenAIImageConfig(**defaults))


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------


@respx.mock
async def test_connection_success():
    respx.get(f"{BASE_OPENROUTER}/models").respond(
        200, json={"data": [{"id": "gemini-flash"}, {"id": "dall-e-3"}]}
    )
    result = await make_connector().test_connection()
    assert result["connected"] is True
    assert "gemini-flash" in result["details"]["models_available"]


@respx.mock
async def test_connection_auth_error():
    respx.get(f"{BASE_OPENROUTER}/models").respond(401)
    result = await make_connector().test_connection()
    assert result["connected"] is False


@respx.mock
async def test_connection_network_error():
    respx.get(f"{BASE_OPENROUTER}/models").mock(side_effect=httpx.ConnectError("no route"))
    result = await make_connector().test_connection()
    assert result["connected"] is False


# ---------------------------------------------------------------------------
# generate_image (OpenRouter) — /chat/completions path
# ---------------------------------------------------------------------------


@respx.mock
async def test_generate_image_openrouter_data_url_response():
    data_url = "data:image/png;base64," + base64.b64encode(FAKE_PNG).decode()
    respx.post(f"{BASE_OPENROUTER}/chat/completions").respond(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            }
                        ]
                    }
                }
            ]
        },
    )
    result = await make_connector().generate_image("a red apple")
    assert result == FAKE_PNG


@respx.mock
async def test_generate_image_openrouter_remote_url_response():
    respx.post(f"{BASE_OPENROUTER}/chat/completions").respond(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": IMAGE_URL},
                            }
                        ]
                    }
                }
            ]
        },
    )
    respx.get(IMAGE_URL).respond(200, content=FAKE_PNG)
    result = await make_connector().generate_image("a blue sky")
    assert result == FAKE_PNG


@respx.mock
async def test_generate_image_openrouter_negative_prompt_and_config():
    route = respx.post(f"{BASE_OPENROUTER}/chat/completions").respond(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/png;base64," + base64.b64encode(FAKE_PNG).decode(),
                                },
                            }
                        ]
                    }
                }
            ]
        },
    )
    await make_connector().generate_image("an elf", negative_prompt="blurry, deformed")
    body = json.loads(route.calls[0].request.content)
    assert body["messages"][0]["content"] == "an elf. Avoid: blurry, deformed"
    assert body["modalities"] == ["image"]
    assert body["image_config"]["size"] == "1024x1024"


@respx.mock
async def test_generate_image_openrouter_uses_overrides():
    route = respx.post(f"{BASE_OPENROUTER}/chat/completions").respond(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/png;base64," + base64.b64encode(FAKE_PNG).decode(),
                                },
                            }
                        ]
                    }
                }
            ]
        },
    )
    await make_connector().generate_image("test", model="openai/gpt-image-1", size="768x768")
    body = json.loads(route.calls[0].request.content)
    assert body["model"] == "openai/gpt-image-1"
    assert body["image_config"]["size"] == "768x768"


@respx.mock
async def test_generate_image_openrouter_raises_on_error():
    respx.post(f"{BASE_OPENROUTER}/chat/completions").respond(502)
    with pytest.raises(httpx.HTTPStatusError):
        await make_connector().generate_image("test")


@respx.mock
async def test_generate_image_openrouter_raises_if_no_image():
    respx.post(f"{BASE_OPENROUTER}/chat/completions").respond(
        200,
        json={"choices": [{"message": {"content": [{"type": "text", "text": "no image"}]}}]},
    )
    with pytest.raises(ValueError, match="did not return an image"):
        await make_connector().generate_image("test")


@respx.mock
async def test_generate_image_openrouter_sends_auth_header():
    route = respx.post(f"{BASE_OPENROUTER}/chat/completions").respond(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/png;base64," + base64.b64encode(FAKE_PNG).decode(),
                                },
                            }
                        ]
                    }
                }
            ]
        },
    )
    await make_connector(api_key="sk-or-secret").generate_image("test")
    assert route.calls[0].request.headers["authorization"] == "Bearer sk-or-secret"


# ---------------------------------------------------------------------------
# generate_image (OpenAI-compatible) — /images/generations path
# ---------------------------------------------------------------------------


@respx.mock
async def test_generate_image_openai_compat_b64_json():
    b64 = base64.b64encode(FAKE_PNG).decode()
    respx.post(f"{BASE_OPENAI_COMPAT}/images/generations").respond(
        200, json={"data": [{"b64_json": b64}]}
    )
    result = await make_connector(base_url=BASE_OPENAI_COMPAT).generate_image("a red apple")
    assert result == FAKE_PNG


@respx.mock
async def test_generate_image_openai_compat_url_fallback():
    respx.post(f"{BASE_OPENAI_COMPAT}/images/generations").respond(
        200, json={"data": [{"url": IMAGE_URL}]}
    )
    respx.get(IMAGE_URL).respond(200, content=FAKE_PNG)
    result = await make_connector(base_url=BASE_OPENAI_COMPAT).generate_image("a blue sky")
    assert result == FAKE_PNG
