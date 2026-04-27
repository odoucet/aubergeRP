# 01 — Technology Stack

## 1. Overview

aubergeRP targets minimal dependencies, zero-build-step frontend, and a **connector-based architecture** for all external backends. The MVP ships with the simplest possible connectors (OpenAI-compatible APIs for both text and image).

## 2. Backend

### Language & Runtime

| Component | Choice | Version |
|---|---|---|
| Language | Python | 3.12+ |
| Package manager | pip (with `requirements.txt`) | — |
| Virtual environment | venv (standard library) | — |

### Framework & Libraries

| Library | Purpose | Version |
|---|---|---|
| `fastapi` | Web framework, REST API, SSE | ≥ 0.111, < 1.0 |
| `uvicorn[standard]` | ASGI server | ≥ 0.30, < 1.0 |
| `httpx` | Async HTTP client (connector backends) | ≥ 0.27, < 1.0 |
| `pydantic` | Data validation and serialization | ≥ 2.0, < 3.0 |
| `sse-starlette` | Server-Sent Events for FastAPI | ≥ 2.0, < 3.0 |
| `Pillow` | PNG metadata read/write for character cards | ≥ 10.0, < 12.0 |
| `python-multipart` | File upload handling | ≥ 0.0.9, < 1.0 |
| `pyyaml` | YAML configuration file parsing | ≥ 6.0, < 7.0 |
| `sqlmodel` | SQLite ORM + Pydantic integration | ≥ 0.0.18, < 1.0 |
| `websockets` | WebSocket client for ComfyUI progress monitoring | ≥ 12.0, < 14.0 |
| `aiofiles` | Async file I/O helpers | ≥ 23.0, < 25.0 |
| `sentry-sdk[fastapi]` | Optional error tracking (no-op if DSN not set) | ≥ 2.0, < 3.0 |

### Storage

| Component | Choice | Rationale |
|---|---|---|
| Characters, Conversations, Messages, LLM call stats | SQLite (`data/auberge.db`) via **SQLModel** | Structured queries, migrations, no separate DB server |
| Configuration | YAML file (`config.yaml`) | Human-readable, supports comments |
| Connector instances | JSON files | One file per connector |
| Generated images | Files on disk | Organized per session (see [02 § 5](02-project-structure.md)) |
| Avatars | Image files | One per character |

File layout is specified in [02 — Project Structure](02-project-structure.md).

Writes to connector JSON files are **atomic** (write to temp file + `os.rename`). Database writes use SQLAlchemy sessions (ACID guarantees from SQLite).

## 3. Frontend

| Component | Choice | Rationale |
|---|---|---|
| Framework | None (vanilla HTML + JS) | Zero build step, minimal complexity |
| CSS | Plain CSS | No preprocessor needed |
| Templating | DOM manipulation in JS | No library |
| HTTP client | `fetch` API (native) | — |
| SSE client | `fetch` + `ReadableStream` | `EventSource` can't send custom headers; we read SSE off a POST (see [07 § 6](07-frontend-chat-ui.md)) |
| Markdown rendering | `marked.js` (vendored) | Lightweight |

All external JS/CSS is **vendored** under `frontend/js/vendor/` — no CDN loads at runtime. aubergeRP is offline-capable.

File layout is specified in [02 — Project Structure](02-project-structure.md).

## 4. External Dependencies (Runtime)

### Text Generation (via Text Connector)

- **Protocol:** OpenAI-compatible Chat Completions (`/v1/chat/completions`).
- **Supported backends:** Ollama, vLLM, LM Studio, text-generation-webui (with OpenAI extension), OpenRouter, OpenAI API, any OpenAI-compatible server.
- **Streaming required** — MVP uses `stream: true` exclusively.

### Image Generation (via Image Connector)

- **Protocol:** OpenAI-compatible Images API (`/v1/images/generations`).
- **Supported backends:** OpenRouter (→ Gemini, DALL-E, Flux), OpenAI directly, any compatible endpoint.
- **No GPU required locally** — images are generated via remote APIs.
- **Media serving:** generated images are served through `GET /api/images/{session-token}/{image_id}`.

## 5. Development Tools

| Tool | Purpose |
|---|---|
| `pytest` | Unit and integration testing |
| `pytest-asyncio` | Async test support |
| `ruff` | Linting and formatting |
| `mypy` | Optional static type checking |
| `respx` | Mock `httpx` calls in tests |

### Makefile

A `Makefile` at the project root provides developer targets:

| Target | Command | Description |
|---|---|---|
| `make lint` | `ruff check` | Run linter |
| `make lint-fix` | `ruff check --fix` | Run linter and auto-fix |
| `make test` | `pytest` | Run test suite |
| `make run` | `uvicorn aubergeRP.main:app --host 0.0.0.0 --port 8000` | Start the server |

### Testing Strategy

- **Unit tests** for services (character parsing, connector logic, prompt building).
- **Integration tests** for API endpoints (using FastAPI test client).
- **No frontend tests** (manual testing).
- Every pull request **must** include tests for the new or modified functionality.

## 6. Dependency Policy

- Pin major and minor bounds in `requirements.txt` (e.g., `fastapi>=0.111,<1.0`).
- Minimize the number of dependencies. Every addition must have a clear justification.
- Prefer standard library when available (`uuid`, `json`, `pathlib`, `logging`, `secrets`).
- Frontend: vendor everything. No CDN loads.
