# 06 — Connector System

## 1. Overview

A **connector** is a pluggable module that talks to a specific external generation backend for a specific modality (text, image, video, audio).

Consequences:

- The frontend and chat service never talk to specific backends directly.
- Whether an image comes from an API call or a local ComfyUI workflow is transparent to the rest of the app.
- A new backend = a new connector class. No core changes.

## 2. Connector Types

| Type | Status |
|---|---|
| `text` (chat completions) | ✅ |
| `image` (image generation) | ✅ |
| `video` | — (see [POST-MVP.md](POST-MVP.md)) |
| `audio` | — (see [POST-MVP.md](POST-MVP.md)) |

## 3. Connector Backends

A **backend** is the specific service implementation for a connector type.

| Backend ID | Supported Types | Description | Status |
|---|---|---|---|
| `openai_api` | `text`, `image` | Any OpenAI-compatible API (Ollama, OpenRouter, OpenAI, vLLM, LM Studio, …) | ✅ |
| `comfyui` | `image` | Local ComfyUI instance with workflow templates | ✅ |

Additional backends (e.g., video, audio) are listed in [POST-MVP.md](POST-MVP.md).

## 4. Architecture

```
┌───────────────────────────────────────────────────────┐
│                 aubergeRP Backend                     │
│                                                       │
│  ┌────────────────────────────────────────────────┐   │
│  │             ConnectorManager                   │   │
│  │  ┌──────────────────┐  ┌──────────────────┐    │   │
│  │  │ Text Connector   │  │ Image Connector  │    │   │
│  │  │ (active: 1)      │  │ (active: 1)      │    │   │
│  │  └────────┬─────────┘  └────────┬─────────┘    │   │
│  └───────────┼─────────────────────┼──────────────┘   │
│              ▼                     ▼                  │
│  ┌───────────────────┐  ┌───────────────────┐         │
│  │ OpenAI API Client │  │ OpenAI API Client │         │
│  └─────────┬─────────┘  └─────────┬─────────┘         │
└────────────┼──────────────────────┼───────────────────┘
             ▼                      ▼
    ┌─────────────────┐   ┌──────────────────┐
    │ LLM Backend     │   │ Image API        │
    └─────────────────┘   └──────────────────┘
```

The chat service calls the active image connector as a **plain in-process Python call**. There is no HTTP endpoint for triggering generation.

## 5. Connector Model

### 5.1 Connector Instance

Each configured connector is persisted as `data/connectors/{uuid}.json`:

```json
{
  "id": "uuid-string",
  "name": "My OpenRouter Image Gen",
  "type": "image",
  "backend": "openai_api",
  "config": {
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "sk-or-...",
    "model": "google/gemini-2.0-flash-exp:free",
    "timeout": 120
  },
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

Notes:

- `api_key` is stored on disk (single-user local deployment).
- There is **no** `is_active` or `enabled` field stored here. Active connector selection lives in `config.yaml` (see § 8).
- `api_key` is **never** returned by the API (redacted to `api_key_set: bool`; see [03 § 8](03-backend-api.md)).

### 5.2 Backend-Specific Config

#### `openai_api` (text)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `base_url` | string | yes | `http://localhost:11434/v1` | Base URL of the API |
| `api_key` | string | no | `""` | API key |
| `model` | string | yes | `llama3` | Model name |
| `max_tokens` | integer | no | `1024` | Max response tokens |
| `temperature` | float | no | `0.8` | Generation temperature |
| `timeout` | integer | no | `120` | Request timeout (seconds) |

#### `openai_api` (image)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `base_url` | string | yes | `https://openrouter.ai/api/v1` | Base URL |
| `api_key` | string | yes | — | API key (typically required) |
| `model` | string | yes | `google/gemini-2.0-flash-exp:free` | Model name |
| `size` | string | no | `1024x1024` | Default image size |
| `timeout` | integer | no | `120` | Request timeout (seconds) |

#### `comfyui` (image)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `base_url` | string | yes | `http://localhost:8188` | Base URL of the ComfyUI server |
| `workflow` | string | no | `default` | Workflow template name (without `.json`) |
| `timeout` | integer | no | `120` | Request timeout (seconds) |

## 6. Connector Interface

All connectors implement a type-specific abstract base class.

### 6.1 Base

```python
from abc import ABC, abstractmethod

class BaseConnector(ABC):
    connector_type: str  # "text", "image", "video", "audio"
    backend_id: str      # "openai_api", ...

    @abstractmethod
    async def test_connection(self) -> dict:
        """Return {'connected': bool, 'details': {...}}."""
```

### 6.2 Text Connector

```python
class TextConnector(BaseConnector):
    connector_type = "text"

    @abstractmethod
    async def stream_chat_completion(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield text tokens from a streaming chat completion."""
```

### 6.3 Image Connector

```python
class ImageConnector(BaseConnector):
    connector_type = "image"

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        model: str | None = None,
        size: str | None = None,
    ) -> bytes:
        """Generate an image. Return raw image bytes (PNG)."""
```

Video/audio connector interfaces are specified in [POST-MVP.md](POST-MVP.md).

## 7. Implementations

### 7.1 `OpenAITextConnector`

```
POST {base_url}/chat/completions
Authorization: Bearer {api_key}
Body: {"model": "...", "messages": [...], "stream": true, "max_tokens": ..., "temperature": ...}
```

Streaming SSE response format (from upstream):

```
data: {"choices": [{"delta": {"content": "token"}}]}
data: {"choices": [{"delta": {}}], "finish_reason": "stop"}
data: [DONE]
```

The connector parses these and yields each `content` delta as a string.

### 7.2 `OpenAIImageConnector`

```
POST {base_url}/images/generations
Authorization: Bearer {api_key}
Body: {"model": "...", "prompt": "...", "size": "1024x1024", "n": 1}
```

Upstream response:

```json
{
  "data": [
    {"url": "https://...", "b64_json": "..."}
  ]
}
```

The connector:

1. Sends the request.
2. Reads `data[0]`. If `b64_json` is present, decode it. Otherwise fetch the `url`.
3. Returns the raw image bytes.

`negative_prompt` is not part of the OpenAI spec. If provided, the connector appends `". Avoid: <negative_prompt>"` to the prompt.

### 7.3 `ComfyUIConnector`

Talks to a local ComfyUI instance via its REST API and WebSocket.

```
POST {base_url}/prompt
Body: <workflow JSON with __PROMPT__ and __NEGATIVE__ placeholders substituted>
```

1. Submits the workflow via `POST /prompt`, receiving a `prompt_id`.
2. Opens a WebSocket (`ws://{host}/ws?clientId={uuid}`) to receive progress events.
3. When the WebSocket signals completion, fetches the output image via `GET /view?filename=...`.
4. Returns the raw PNG bytes.

**Workflow templates** live in `data/comfyui_workflows/` (user directory, seeded from built-in templates on startup). The active workflow is selected by name via the connector's `workflow` config field.

#### `comfyui` config fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `base_url` | string | yes | `http://localhost:8188` | Base URL of the ComfyUI server |
| `workflow` | string | no | `default` | Workflow template name (without `.json`) |
| `timeout` | integer | no | `120` | Request timeout (seconds) |

## 8. Connector Manager

```python
class ConnectorManager:
    def get_active_text_connector(self) -> TextConnector | None: ...
    def get_active_image_connector(self) -> ImageConnector | None: ...

    def list_connectors(self, type: str | None = None) -> list[ConnectorInstance]: ...
    def get_connector(self, connector_id: str) -> ConnectorInstance: ...

    def create_connector(self, data) -> ConnectorInstance: ...
    def update_connector(self, connector_id: str, data) -> ConnectorInstance: ...
    def delete_connector(self, connector_id: str) -> None: ...

    def test_connector(self, connector_id: str) -> dict: ...
    def set_active(self, connector_id: str) -> None:
        """Write config.yaml:active_connectors.{type} = connector_id."""
```

### Active Connector — Single Source of Truth

**`config.yaml` is authoritative.** The active connector IDs per type are stored there:

```yaml
active_connectors:
  text: "uuid-of-active-text-connector"
  image: "uuid-of-active-image-connector"
```

- `is_active` in API responses is **derived** by comparing a connector's `id` to the value in `config.yaml`.
- Connector JSON files never store an `is_active` flag.
- If a connector is deleted and it was the active one for its type, the corresponding entry in `config.yaml` is cleared.

### Storage

- Connectors: `data/connectors/{uuid}.json` (one file per instance, atomic writes).
- Active selection: `config.yaml` top-level `active_connectors` map.

## 9. Image Storage

- Generated images are saved to `data/images/{SESSION_TOKEN}/{uuid}.png` where `SESSION_TOKEN` is the constant `00000000-0000-0000-0000-000000000000` in the MVP (see [00 § 9](00-architecture-overview.md)).
- Images are served through `GET /api/images/{session_token}/{image_id}` (see [03 § 7](03-backend-api.md)).
- No automatic cleanup in MVP; users manage disk space manually.

## 10. Error Handling

| Scenario | Behavior |
|---|---|
| No active connector for the requested type | HTTP 400 with `"No {type} connector configured"` (text) or `image_failed` SSE (image inside chat) |
| Backend unreachable | HTTP 502 / `image_failed` SSE |
| API key invalid/missing | HTTP 502 with descriptive detail |
| Generation fails upstream | Propagate upstream detail |
| Timeout | HTTP 504 / `image_failed` SSE |
| Unknown backend ID on create | HTTP 400 |

## 11. Adding a New Connector Backend

1. Add a file in `connectors/` (e.g., `stability_image.py`).
2. Implement the appropriate base class.
3. Register the backend ID in the connector factory / `manager.py`.
4. Declare its config schema for the admin UI (via `GET /api/connectors/backends`).
5. No changes needed in routers, frontend, or services.
