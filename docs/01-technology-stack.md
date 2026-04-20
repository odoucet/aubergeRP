# 01 — Technology Stack

## 1. Overview

AubergeLLM follows a deliberate strategy of minimal dependencies and zero-build-step frontend to maximize simplicity, reduce onboarding friction, and ensure a time-to-first-roleplay under one hour.

## 2. Backend

### Language & Runtime

| Component | Choice | Version |
|---|---|---|
| Language | Python | 3.10+ |
| Package manager | pip (with `requirements.txt`) | — |
| Virtual environment | venv (standard library) | — |

**Rationale:** Python has the best ecosystem for LLM and ComfyUI integration, and is familiar to the target audience (ML/AI hobbyists).

### Framework & Libraries

| Library | Purpose | Version (pinned) |
|---|---|---|
| `fastapi` | Web framework, REST API, SSE | ≥ 0.111 |
| `uvicorn` | ASGI server | ≥ 0.30 |
| `httpx` | Async HTTP client (LLM + ComfyUI calls) | ≥ 0.27 |
| `websockets` | WebSocket client for ComfyUI monitoring | ≥ 12.0 |
| `pydantic` | Data validation and serialization (comes with FastAPI) | ≥ 2.0 |
| `sse-starlette` | Server-Sent Events support for FastAPI | ≥ 2.0 |
| `Pillow` | PNG metadata read/write for character cards | ≥ 10.0 |
| `python-multipart` | File upload handling (FastAPI dependency) | ≥ 0.0.9 |
| `pyyaml` | YAML configuration file parsing | ≥ 6.0 |

### Storage

| Component | Choice | Rationale |
|---|---|---|
| Character data | JSON files on disk | No DB setup, human-readable, easy to debug |
| Conversation data | JSON files on disk | Same rationale; one file per conversation |
| Configuration | YAML file (`config.yaml`) | Human-readable, supports comments |
| Generated images | Files on disk (`data/images/`) | Simple, served directly by the backend |
| Workflow templates | JSON files on disk (`data/workflows/`) | ComfyUI native format |

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
├── workflows/           # ComfyUI workflow templates
│   └── default_t2i.json
└── avatars/             # Character avatar images
    ├── {uuid}.png
    └── ...
```

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

### LLM Backend

- **Protocol:** OpenAI-compatible Chat Completions API (`/v1/chat/completions`).
- **Supported backends:** Ollama, vLLM, LM Studio, text-generation-webui (with OpenAI extension), OpenAI API, any OpenAI-compatible server.
- **Streaming:** Uses `stream: true` in the request to receive tokens via SSE from the LLM backend.

### ComfyUI

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

### Testing Strategy

- **Unit tests** for services (character parsing, workflow mapping, prompt building).
- **Integration tests** for API endpoints (using FastAPI test client).
- **No frontend tests in MVP** (manual testing only).

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
python -m uvicorn aubergellm.main:app --host 0.0.0.0 --port 8000
```

The server serves both the API and the static frontend files.

### No Containerization in MVP

Docker/docker-compose may be added post-MVP but is not a requirement.

## 7. Dependency Policy

- Pin major and minor versions in `requirements.txt` (e.g., `fastapi>=0.111,<1.0`).
- Minimize the number of dependencies. Every addition must have a clear justification.
- Prefer standard library solutions when available (e.g., `uuid`, `json`, `pathlib`, `logging`).
- Frontend: prefer vendored files over CDN to enable fully offline usage.
