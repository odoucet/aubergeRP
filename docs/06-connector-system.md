# 06 — Connector System

## 1. Overview

AubergeLLM uses a **connector-based architecture** to abstract all external generation services. A connector is a pluggable module that handles communication with a specific type of backend for a specific modality (text, image, video, audio).

This design means:

- The frontend and chat system never interact with specific backends directly.
- Whether an image is generated via an API call to OpenRouter/Gemini or via a ComfyUI workflow is transparent to the rest of the application.
- Adding support for a new backend (e.g., a new image API, a TTS service) only requires implementing a new connector — no changes to the core application.
- The simplest connectors (OpenAI-compatible APIs) ship first, making the MVP much easier to set up.

## 2. Connector Types

Each connector has a **type** that defines what modality it handles:

| Type | Description | MVP | Post-MVP |
|---|---|---|---|
| `text` | Text generation (chat completions) | ✅ | — |
| `image` | Image generation from prompts | ✅ | — |
| `video` | Video generation | — | ✅ |
| `audio` | Audio/TTS generation | — | ✅ |

## 3. Connector Backends

A **backend** is the specific service implementation for a connector type:

| Backend ID | Supported Types | Description | MVP |
|---|---|---|---|
| `openai_api` | `text`, `image` | Any OpenAI-compatible API (Ollama, OpenRouter, OpenAI, vLLM, LM Studio, etc.) | ✅ |
| `comfyui` | `image`, `video` | ComfyUI instance with workflow abstraction | Post-MVP |

### Why OpenAI API first?

The OpenAI-compatible API format is the de facto standard. For **image generation**, services like OpenRouter (which routes to Gemini, DALL-E, Flux, etc.), OpenAI directly, or any compatible server all use the same `/v1/images/generations` endpoint. This means:

- **Zero extra setup** — if you already have an OpenRouter or OpenAI API key, image generation works immediately.
- **No GPU required locally** — images are generated remotely.
- **ComfyUI becomes a power-user option** — added as a second connector backend for users who want local Stable Diffusion control.

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   AubergeLLM Backend                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Connector Manager                      │    │
│  │                                                     │    │
│  │  ┌─────────────────┐  ┌─────────────────┐          │    │
│  │  │ Text Connector   │  │ Image Connector  │  ...    │    │
│  │  │ (active: 1)      │  │ (active: 1)      │         │    │
│  │  └────────┬─────────┘  └────────┬─────────┘         │    │
│  │           │                     │                    │    │
│  └───────────┼─────────────────────┼────────────────────┘    │
│              │                     │                         │
│              ▼                     ▼                         │
│  ┌───────────────────┐  ┌───────────────────┐               │
│  │ OpenAI API Client │  │ OpenAI API Client │               │
│  │ (text backend)    │  │ (image backend)   │               │
│  └─────────┬─────────┘  └─────────┬─────────┘               │
│            │                      │                          │
└────────────┼──────────────────────┼──────────────────────────┘
             │                      │
             ▼                      ▼
    ┌─────────────────┐   ┌──────────────────┐
    │ LLM Backend     │   │ Image API        │
    │ (Ollama,        │   │ (OpenRouter,     │
    │  OpenAI, etc.)  │   │  OpenAI, etc.)   │
    └─────────────────┘   └──────────────────┘
```

Post-MVP addition:

```
             ┌───────────────────┐
             │ ComfyUI Client    │   (additional image backend)
             │ (HTTP + WS)       │
             └─────────┬─────────┘
                       │
                       ▼
              ┌──────────────┐
              │   ComfyUI    │
              │   Instance   │
              └──────────────┘
```

## 5. Connector Model

### 5.1 Connector Instance

Each configured connector is an instance with the following structure:

```json
{
  "id": "uuid-string",
  "name": "My OpenRouter Image Gen",
  "type": "image",
  "backend": "openai_api",
  "enabled": true,
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

### 5.2 Backend-Specific Configuration

#### `openai_api` backend (text)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `base_url` | string | Yes | `http://localhost:11434/v1` | Base URL of the API |
| `api_key` | string | No | `""` | API key |
| `model` | string | Yes | `llama3` | Model name |
| `max_tokens` | integer | No | `1024` | Max response tokens |
| `temperature` | float | No | `0.8` | Generation temperature |
| `timeout` | integer | No | `120` | Request timeout (seconds) |

#### `openai_api` backend (image)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `base_url` | string | Yes | `https://openrouter.ai/api/v1` | Base URL of the API |
| `api_key` | string | Yes | — | API key (typically required for image APIs) |
| `model` | string | Yes | `google/gemini-2.0-flash-exp:free` | Model name |
| `size` | string | No | `1024x1024` | Default image size |
| `quality` | string | No | `standard` | Image quality (`standard` or `hd`) |
| `timeout` | integer | No | `120` | Request timeout (seconds) |

#### `comfyui` backend (image) — Post-MVP

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `base_url` | string | Yes | `http://localhost:8188` | ComfyUI URL |
| `timeout` | integer | No | `120` | Request timeout |
| `ws_timeout` | integer | No | `300` | WebSocket monitoring timeout |
| `workflow_dir` | string | No | `data/comfyui_workflows` | Path to workflow templates |

## 6. Connector Interface

All connectors implement a common interface per type. This is the Python abstract base class:

### 6.1 Base Connector

```python
from abc import ABC, abstractmethod

class BaseConnector(ABC):
    """Base class for all connectors."""

    connector_type: str  # "text", "image", "video", "audio"
    backend_id: str      # "openai_api", "comfyui", etc.

    @abstractmethod
    async def test_connection(self) -> dict:
        """Test if the backend is reachable. Returns status dict."""
        ...

    @abstractmethod
    async def get_capabilities(self) -> dict:
        """Return available models/options for this connector."""
        ...
```

### 6.2 Text Connector Interface

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
        """Stream text tokens from a chat completion request."""
        ...
```

### 6.3 Image Connector Interface

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
        """Generate an image from a prompt. Returns image bytes."""
        ...
```

### 6.4 Video Connector Interface (Post-MVP)

```python
class VideoConnector(BaseConnector):
    connector_type = "video"

    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        source_image: bytes | None = None,
        model: str | None = None,
    ) -> bytes:
        """Generate a video. Returns video bytes."""
        ...
```

### 6.5 Audio Connector Interface (Post-MVP)

```python
class AudioConnector(BaseConnector):
    connector_type = "audio"

    @abstractmethod
    async def generate_audio(
        self,
        text: str,
        voice: str | None = None,
        model: str | None = None,
    ) -> bytes:
        """Generate audio/speech from text. Returns audio bytes."""
        ...
```

## 7. MVP Connector Implementations

### 7.1 `OpenAITextConnector`

Implements `TextConnector` using the OpenAI Chat Completions API.

```python
# POST {base_url}/chat/completions
# Headers: Authorization: Bearer {api_key}
# Body: {"model": "...", "messages": [...], "stream": true, ...}
```

This is the same protocol used by Ollama, vLLM, LM Studio, OpenRouter, and OpenAI.

**Streaming response parsing:**

```
data: {"choices": [{"delta": {"content": "token"}}]}
data: {"choices": [{"delta": {}}], "finish_reason": "stop"}
data: [DONE]
```

### 7.2 `OpenAIImageConnector`

Implements `ImageConnector` using the OpenAI Images API.

```python
# POST {base_url}/images/generations
# Headers: Authorization: Bearer {api_key}
# Body: {"model": "...", "prompt": "...", "size": "1024x1024", "n": 1}
```

**Response:**

```json
{
  "data": [
    {
      "url": "https://...",
      "b64_json": "..."
    }
  ]
}
```

The connector:
1. Sends the generation request.
2. Receives either a URL or base64-encoded image.
3. Downloads the image if a URL is provided.
4. Returns the raw image bytes.

This works with OpenRouter (→ Gemini, Flux, DALL-E), OpenAI directly, and any compatible endpoint.

## 8. Connector Manager

The `ConnectorManager` is the central service that manages all connector instances:

```python
class ConnectorManager:
    """Manages all configured connectors."""

    def get_active_text_connector(self) -> TextConnector | None:
        """Get the currently active text connector."""

    def get_active_image_connector(self) -> ImageConnector | None:
        """Get the currently active image connector."""

    def list_connectors(self, type: str | None = None) -> list[ConnectorInstance]:
        """List all configured connectors, optionally filtered by type."""

    def get_connector(self, connector_id: str) -> ConnectorInstance:
        """Get a specific connector by ID."""

    def create_connector(self, data: ConnectorCreate) -> ConnectorInstance:
        """Create a new connector instance."""

    def update_connector(self, connector_id: str, data: ConnectorUpdate) -> ConnectorInstance:
        """Update connector configuration."""

    def delete_connector(self, connector_id: str) -> None:
        """Delete a connector."""

    def test_connector(self, connector_id: str) -> dict:
        """Test a connector's connection."""

    def set_active(self, connector_id: str) -> None:
        """Set a connector as the active one for its type."""
```

### Active Connector Selection

For the MVP, there is **one active connector per type**. The chat service uses the active text connector, and the image generation uses the active image connector. The admin can switch which connector is active.

### Connector Storage

Connectors are stored as individual JSON files in `data/connectors/`:

```
data/connectors/
├── {uuid}.json    # One file per connector instance
└── ...
```

The active connector IDs are stored in `config.yaml`:

```yaml
active_connectors:
  text: "uuid-of-active-text-connector"
  image: "uuid-of-active-image-connector"
```

## 9. ComfyUI Connector (Post-MVP)

When implemented, the ComfyUI connector will be an `ImageConnector` backend that:

1. Loads workflow templates from `data/comfyui_workflows/`.
2. Injects prompt and parameters into the workflow JSON.
3. Submits to ComfyUI via HTTP.
4. Monitors execution via WebSocket.
5. Retrieves the generated image.

This follows the same `ImageConnector` interface, so the rest of the application doesn't need to change.

### Workflow Abstraction (ComfyUI-specific)

Each ComfyUI workflow is defined by:
- A template JSON file (exported from ComfyUI API format).
- A YAML definition mapping named inputs to ComfyUI node IDs.

```yaml
id: default_t2i
name: "Default Text-to-Image"
inputs:
  - name: prompt
    inject: { node_id: "6", field: "inputs.text" }
  - name: negative_prompt
    inject: { node_id: "7", field: "inputs.text" }
  - name: seed
    inject: { node_id: "3", field: "inputs.seed" }
outputs:
  - name: image
    extract: { node_id: "9" }
```

## 10. Image Storage

- Generated images are saved to `data/images/{generation_uuid}.png`.
- Images are served via `GET /api/images/{image_id}`.
- No automatic cleanup in MVP. Users manage disk space manually.

## 11. Error Handling

| Scenario | Behavior |
|---|---|
| No active connector for type | Return 400 error: "No {type} connector configured" |
| Connector backend unreachable | Return 502 error; chat continues without that modality |
| API key invalid/missing | Return 502 error with descriptive message |
| Generation fails | Return error detail from the backend |
| Timeout | Return 504 error |
| Unknown backend type | Return 400 error on connector creation |

## 12. Adding a New Connector Backend

To add support for a new backend (e.g., a Stability AI image connector):

1. Create a new file in `connectors/` (e.g., `stability_image.py`).
2. Implement the appropriate interface (`ImageConnector`).
3. Register the backend ID in the connector factory.
4. Add backend-specific config fields.
5. No changes needed to routers, frontend, or other services.
