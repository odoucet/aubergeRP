# 01 — Technology Stack

## 1. Overview

AubergeLLM follows a deliberate strategy of minimal dependencies, zero-build-step frontend, and a **connector-based architecture** to maximize simplicity, reduce onboarding friction, and ensure a time-to-first-roleplay under one hour.

The connector pattern means that all external generation backends (text, image, video, audio) are accessed through a unified abstraction layer, and the MVP ships with the simplest possible connectors (OpenAI-compatible APIs).

## 2. Backend

### Language & Runtime

| Component | Choice | Version |
|---|---|---|
| Language | Python | 3.12+ |
| Package manager | pip (with `requirements.txt`) | — |
| Virtual environment | venv (standard library) | — |

**Rationale:** Python has the best ecosystem for LLM and AI integration, and is familiar to the target audience (ML/AI hobbyists).

### Framework & Libraries

| Library | Purpose | Version (pinned) |
|---|---|---|
| `fastapi` | Web framework, REST API, SSE | ≥ 0.111 |
| `uvicorn` | ASGI server | ≥ 0.30 |
| `httpx` | Async HTTP client (connector backends) | ≥ 0.27 |
| `pydantic` | Data validation and serialization (comes with FastAPI) | ≥ 2.0 |
| `sse-starlette` | Server-Sent Events support for FastAPI | ≥ 2.0 |
| `Pillow` | PNG metadata read/write for character cards | ≥ 10.0 |
| `python-multipart` | File upload handling (FastAPI dependency) | ≥ 0.0.9 |
| `pyyaml` | YAML configuration file parsing | ≥ 6.0 |

**Post-MVP additions (for ComfyUI connector):**

| Library | Purpose | Version (pinned) |
|---|---|---|
| `websockets` | WebSocket client for ComfyUI monitoring | ≥ 12.0 |

### Storage

| Component | Choice | Rationale |
|---|---|---|
| Character data | JSON files on disk | No DB setup, human-readable, easy to debug |
| Conversation data | JSON files on disk | Same rationale; one file per conversation |
| Configuration | YAML file (`config.yaml`) | Human-readable, supports comments |
| Generated images | Files on disk (`data/images/`) | Simple, served through a FastAPI endpoint requiring session token |
| Connector configs | JSON files on disk (`data/connectors/`) | One file per connector instance |

### Directory Structure for Data

```
data/
├── characters/          # One JSON file per character
│   ├── {uuid}.json
│   └── ...
├── conversations/       # One JSON file per conversation
│   ├── {uuid}.json
│   └── ...
├── images/              # Generated images
│   ├── {uuid}.png
│   └── ...
├── connectors/          # Connector instance configs
│   ├── {uuid}.json
│   └── ...
├── comfyui_workflows/   # ComfyUI workflow templates (post-MVP)
│   └── default_t2i.json
└── avatars/             # Character avatar images
    ├── {uuid}.png
    └── ...
```

> **Post-MVP:** Add a scheduled action (or admin-triggered action) to automatically clean generated media files older than X days. X is configurable in the admin, with a default value of 30 days.

## 3. Frontend

### Approach

| Component | Choice | Rationale |
|---|---|---|
| Framework | None (vanilla HTML + JS) | Zero build step, instant iteration, minimal complexity |
| CSS | Plain CSS (single file or minimal set) | No preprocessor needed for MVP |
| Templating | DOM manipulation in JS | Simple, no library needed |
| HTTP client | `fetch` API (native) | No library needed |
| SSE client | `EventSource` API (native) | Built into all modern browsers |
| Markdown rendering | `marked.js` (CDN or vendored) | Lightweight, widely used |
| Code highlighting | `highlight.js` (CDN or vendored) | Optional, for code blocks in chat |

### File Organization

```
frontend/
├── index.html              # Chat UI entry point
├── admin/
│   └── index.html          # Admin UI entry point
├── css/
│   ├── main.css            # Chat UI styles
│   └── admin.css           # Admin UI styles
├── js/
│   ├── chat.js             # Chat logic (send/receive messages, SSE)
│   ├── characters.js       # Character selection UI logic
│   ├── images.js           # Image display logic
│   ├── api.js              # API client (fetch wrappers)
│   ├── admin/
│   │   ├── config.js       # Configuration management
│   │   ├── characters.js   # Character CRUD management
│   │   └── workflows.js    # Workflow management
│   └── vendor/
│       └── marked.min.js   # Vendored markdown renderer
└── assets/
    └── ...                 # Static assets (icons, default images)
```

## 4. External Dependencies (Runtime)

### Text Generation Backend (via Text Connector)

- **Protocol:** OpenAI-compatible Chat Completions API (`/v1/chat/completions`).
- **Supported backends:** Ollama, vLLM, LM Studio, text-generation-webui (with OpenAI extension), OpenRouter, OpenAI API, any OpenAI-compatible server.
- **Streaming:** Uses `stream: true` in the request to receive tokens via SSE from the backend.

### Image Generation Backend (via Image Connector)

- **Protocol:** OpenAI-compatible Images API (`/v1/images/generations`).
- **Supported backends:** OpenRouter (→ Gemini, DALL-E, Flux), OpenAI directly, any compatible endpoint.
- **No GPU required locally** — images can be generated via remote APIs.
- **Media serving:** Generated images (and other media) are served through a **Python FastAPI endpoint** (`GET /api/images/{id}`), not as static files. This endpoint requires the user's session token to prevent other users from accessing media they didn't generate.
- **Access control:** The image generation endpoint (`POST /api/generate/image`) **cannot be called directly by users** — it is for internal backend use only, protected by the internal token (Tier 2). Users request image generation indirectly via the chat endpoint (`POST /api/chat/{id}/message`), and the backend triggers generation automatically when the LLM indicates it is appropriate.

### ComfyUI (Post-MVP, via ComfyUI Image Connector)

- **Protocol:** ComfyUI native HTTP + WebSocket API.
  - `POST /prompt` — submit a workflow for execution.
  - `GET /history/{prompt_id}` — retrieve execution results.
  - `GET /view?filename=...` — retrieve generated images.
  - `ws://host:port/ws?clientId=...` — monitor execution progress.
- **Version:** Any recent ComfyUI version with the standard API.

## 5. Development Tools

| Tool | Purpose |
|---|---|
| `pytest` | Unit and integration testing |
| `ruff` | Python linting and formatting |
| `mypy` | Optional static type checking |

### Makefile

A `Makefile` is provided at the project root with the following targets:

| Target | Command | Description |
|---|---|---|
| `make lint` | `ruff check` | Run linter |
| `make lint-fix` | `ruff check --fix` | Run linter and auto-fix issues |
| `make test` | `pytest` | Run test suite |
| `make run` | `uvicorn aubergellm.main:app --host 0.0.0.0 --port 8000` | Start the server |

### Testing Strategy

- **Unit tests** for services (character parsing, connector logic, prompt building).
- **Integration tests** for API endpoints (using FastAPI test client).
- **No frontend tests in MVP** (manual testing only).
- Any pull request **must** include tests for the new or modified functionality.

## 6. Deployment

### Local Deployment (MVP)

```bash
# 1. Clone the repository
git clone https://github.com/odoucet/aubergellm.git
cd aubergellm

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy default configuration
cp config.example.yaml config.yaml

# 5. Start the server
make run
```

The server serves both the API and the static frontend files.

### No Containerization in MVP

Docker and docker-compose **will** be added in a post-MVP release.

## 7. Dependency Policy

- Pin major and minor versions in `requirements.txt` (e.g., `fastapi>=0.111,<1.0`).
- Minimize the number of dependencies. Every addition must have a clear justification.
- Prefer standard library solutions when available (e.g., `uuid`, `json`, `pathlib`, `logging`).
- Frontend: prefer vendored files over CDN to enable fully offline usage.
