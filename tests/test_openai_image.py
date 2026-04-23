import base64
import json
import pytest
import httpx
import respx

from aubergeRP.connectors.openai_image import OpenAIImageConnector
from aubergeRP.models.connector import OpenAIImageConfig

BASE_URL = "https://openrouter.ai/api/v1"
IMAGE_URL = "https://cdn.example.com/img/abc.png"
FAKE_PNG = b"\x89PNG\r\n\x1a\nFAKE"


def make_connector(**overrides) -> OpenAIImageConnector:
    defaults = dict(base_url=BASE_URL, api_key="sk-or-test")
    defaults.update(overrides)
    return OpenAIImageConnector(OpenAIImageConfig(**defaults))


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------


@respx.mock
async def test_connection_success():
    respx.get(f"{BASE_URL}/models").respond(
        200, json={"data": [{"id": "gemini-flash"}, {"id": "dall-e-3"}]}
    )
    result = await make_connector().test_connection()
    assert result["connected"] is True
    assert "gemini-flash" in result["details"]["models_available"]


@respx.mock
async def test_connection_auth_error():
    respx.get(f"{BASE_URL}/models").respond(401)
    result = await make_connector().test_connection()
    assert result["connected"] is False


@respx.mock
async def test_connection_network_error():
    respx.get(f"{BASE_URL}/models").mock(side_effect=httpx.ConnectError("no route"))
    result = await make_connector().test_connection()
    assert result["connected"] is False


# ---------------------------------------------------------------------------
# generate_image — b64_json path
# ---------------------------------------------------------------------------


@respx.mock
async def test_generate_image_b64_json():
    b64 = base64.b64encode(FAKE_PNG).decode()
    respx.post(f"{BASE_URL}/images/generations").respond(
        200, json={"data": [{"b64_json": b64}]}
    )
    result = await make_connector().generate_image("a red apple")
    assert result == FAKE_PNG


@respx.mock
async def test_generate_image_url_fallback():
    respx.post(f"{BASE_URL}/images/generations").respond(
        200, json={"data": [{"url": IMAGE_URL}]}
    )
    respx.get(IMAGE_URL).respond(200, content=FAKE_PNG)
    result = await make_connector().generate_image("a blue sky")
    assert result == FAKE_PNG


# ---------------------------------------------------------------------------
# generate_image — prompt construction
# ---------------------------------------------------------------------------


@respx.mock
async def test_generate_image_negative_prompt_appended():
    route = respx.post(f"{BASE_URL}/images/generations").respond(
        200, json={"data": [{"b64_json": base64.b64encode(FAKE_PNG).decode()}]}
    )
    await make_connector().generate_image("an elf", negative_prompt="blurry, deformed")
    body = json.loads(route.calls[0].request.content)
    assert body["prompt"] == "an elf. Avoid: blurry, deformed"


@respx.mock
async def test_generate_image_no_negative_prompt():
    route = respx.post(f"{BASE_URL}/images/generations").respond(
        200, json={"data": [{"b64_json": base64.b64encode(FAKE_PNG).decode()}]}
    )
    await make_connector().generate_image("a forest")
    body = json.loads(route.calls[0].request.content)
    assert body["prompt"] == "a forest"


@respx.mock
async def test_generate_image_uses_config_defaults():
    route = respx.post(f"{BASE_URL}/images/generations").respond(
        200, json={"data": [{"b64_json": base64.b64encode(FAKE_PNG).decode()}]}
    )
    connector = make_connector(model="dall-e-3", size="512x512")
    await connector.generate_image("test")
    body = json.loads(route.calls[0].request.content)
    assert body["model"] == "dall-e-3"
    assert body["size"] == "512x512"
    assert body["n"] == 1


@respx.mock
async def test_generate_image_overrides_model_and_size():
    route = respx.post(f"{BASE_URL}/images/generations").respond(
        200, json={"data": [{"b64_json": base64.b64encode(FAKE_PNG).decode()}]}
    )
    await make_connector().generate_image("test", model="flux", size="768x768")
    body = json.loads(route.calls[0].request.content)
    assert body["model"] == "flux"
    assert body["size"] == "768x768"


@respx.mock
async def test_generate_image_raises_on_error():
    respx.post(f"{BASE_URL}/images/generations").respond(502)
    with pytest.raises(httpx.HTTPStatusError):
        await make_connector().generate_image("test")


@respx.mock
async def test_generate_image_sends_auth_header():
    route = respx.post(f"{BASE_URL}/images/generations").respond(
        200, json={"data": [{"b64_json": base64.b64encode(FAKE_PNG).decode()}]}
    )
    await make_connector(api_key="sk-or-secret").generate_image("test")
    assert route.calls[0].request.headers["authorization"] == "Bearer sk-or-secret"
