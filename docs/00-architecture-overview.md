# 00 — Architecture Overview

## 1. Purpose

aubergeRP is a self-hosted roleplay frontend that combines:

- A **text connector** for LLM-based chat (any OpenAI-compatible API).
- A **character library** with SillyTavern-compatible character cards.
- A lightweight **web UI** (chat + admin) served as static HTML/JS.
- A **connector-based architecture** where text, image, video, and audio backends are all pluggable modules.

**Product positioning:** a simplified alternative to SillyTavern, focused on text + image roleplay with a pluggable connector system.

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Browser                            │
│  ┌─────────────────┐       ┌──────────────────────┐     │
│  │  Chat UI (HTML) │       │  Admin UI (HTML)     │     │
│  │  /index.html    │       │  /admin/index.html   │     │
│  └────────┬────────┘       └──────────┬───────────┘     │
│           │  REST + SSE               │  REST           │
└───────────┼───────────────────────────┼─────────────────┘
            │                           │
            ▼                           ▼
┌─────────────────────────────────────────────────────────┐
│              aubergeRP Backend (Python / FastAPI)       │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐  │
│  │ Chat     │ │ Character│ │ Connector │ │ Config    │  │
│  │ Service  │ │ Service  │ │ Manager   │ │ Service   │  │
│  └────┬─────┘ └──────────┘ └─────┬─────┘ └───────────┘  │
│       │                          │                      │
└───────┼──────────────────────────┼──────────────────────┘
        │                          │
        ▼                          ▼
┌───────────────┐          ┌───────────────────┐
│ Text Backend  │          │ Image Backend     │
│ (Ollama,      │          │ (OpenRouter,      │
│  OpenAI API,  │          │  OpenAI, …)       │
│  OpenRouter,  │          │                   │
│  vLLM, …)     │          │                   │
└───────────────┘          └───────────────────┘
```

## 3. Components

### 3.1 Frontend — Chat UI

- Static HTML + vanilla JavaScript.
- Talks to the backend via **REST** (send messages, load characters) and **SSE** (stream LLM tokens, image generation events).
- Displays conversation history, character selection, and generated images inline.
- No build step, no framework.

### 3.2 Frontend — Admin UI

- Static HTML + vanilla JavaScript (separate page).
- Connector management: add, configure, test, and activate connectors per type.
- Character management: import (JSON/PNG), edit, duplicate, export, delete.
- REST only.

### 3.3 Backend — aubergeRP API

- **Python 3.12+** with **FastAPI**.
- Serves the static frontend files.
- Exposes a REST + SSE API for all operations.
- Internal services (not microservices — just logical modules in one process).
- All data stored locally as JSON/YAML files on disk (no database).

### 3.4 External: Generation Backends (via Connectors)

aubergeRP communicates with external services only through **connectors**. Each connector is a module for a specific modality:

- **Text connectors** — any OpenAI-compatible chat completions API.
- **Image connectors** — any OpenAI-compatible images API.
- **Video / audio connectors** — see [POST-MVP.md](POST-MVP.md).

All connectors are configured by the user via the Admin UI. See [06 — Connector System](06-connector-system.md).

## 4. Communication Patterns

| Path | Protocol | Usage |
|---|---|---|
| Browser → Backend (chat) | REST POST + SSE | Send user message, stream LLM response, image lifecycle |
| Browser → Backend (admin) | REST | CRUD characters, manage connectors, update config |
| Browser → Backend (images) | REST GET | Retrieve generated images |
| Backend → Text connector | HTTP (OpenAI-compatible) | Chat completions (streaming) |
| Backend → Image connector | HTTP (OpenAI-compatible) | Image generation |

The Chat UI calls **one** generation-triggering endpoint: `POST /api/chat/{id}/message`. The image connector is invoked by the backend as an in-process Python call during chat processing. The frontend never calls the image connector directly.

## 5. Data Flow — Chat Message Lifecycle

1. User sends a message via the Chat UI (REST POST to `/api/chat/{conversation_id}/message`).
2. Backend builds the full prompt (system prompt from character card + conversation history + user message).
3. Backend calls the **active text connector** to stream the LLM response back to the client via SSE.
4. While streaming, if the LLM emits an inline image marker (see [05 — Chat and Conversations](05-chat-and-conversations.md) § 7), the backend:
   a. Strips the marker from the forwarded stream.
   b. Calls the **active image connector** as an in-process Python call.
   c. Sends image lifecycle events via the same SSE stream (`image_start`, `image_complete`).
5. The completed conversation (including image URLs) is persisted atomically to a JSON file on disk.

## 6. Key Architectural Decisions

| Decision | Rationale |
|---|---|
| Static HTML + vanilla JS | Zero build step, easy to serve, easy to modify |
| FastAPI (Python) | Mature async, native SSE, good AI ecosystem |
| JSON/YAML file storage (no DB) | Simplest persistence for the MVP |
| SSE (not WebSocket) | Simpler than WebSocket for unidirectional streaming; sufficient |
| Connector-based architecture | Decouples core logic from specific backends |
| OpenAI-compatible API as default | De facto standard for both text and images |
| Single process | FastAPI serves API + frontend |

## 7. MVP Scope

### In Scope

- **Single user, local deployment.** (Code is structured to allow multi-user later — see § 9.)
- Text and image connector types.
- OpenAI-compatible API backend for both text and image.
- One active connector per type at a time.
- Character library with SillyTavern V1/V2 import/export.
- Conversation persistence as JSON files.
- Admin UI for connectors, config, characters.
- Chat UI for roleplay with image display inline.

### Out of Scope

See [POST-MVP.md](POST-MVP.md).

## 8. Cross-Cutting Concerns

### Error Handling

- Backend returns structured JSON error responses (`{"detail": "..."}`) with HTTP status codes.
- Frontend displays user-friendly error messages.
- Image connector failures are handled gracefully (chat continues without the image).

### Logging

- Python `logging`, structured output to stdout.
- Log level configurable in `config.yaml`.

### CORS

- Enabled for local development. The backend serves the frontend, so CORS is minimal in production.

### Offline-first

- Frontend must not load any resource from external CDNs. All JS/CSS libraries are vendored in `frontend/js/vendor/` (or `frontend/css/vendor/`).

### Security

- **MVP has no authentication.** It is a local, single-user deployment.
- No secrets in code — configuration in `config.yaml`, API keys stored per connector.
- Input sanitization on character card imports (prevent XSS in HTML rendering).

## 9. Multi-User Preparation

Although the MVP is single-user, the code is structured so multi-user support is a drop-in change, not a rewrite. Specifically:

- **Session token constant.** A single constant `SESSION_TOKEN = "00000000-0000-0000-0000-000000000000"` is used wherever a per-user identifier will later plug in. In the MVP, all requests implicitly use this constant.
- **Per-session image folder.** Generated images live at `data/images/{session-token}/{uuid}.png`. In the MVP this means one folder, but no file-layout change is required later.
- **Conversations.** The conversation model will gain an `owner` field post-MVP; for the MVP, no filtering is done.

Each of these seams must be marked with a `# TODO(multi-user): ...` comment in code so they are easy to find when multi-user support is added.

Multi-user authentication and session lifecycle are specified in [POST-MVP.md](POST-MVP.md).
