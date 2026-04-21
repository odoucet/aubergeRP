# 00 — Architecture Overview

## 1. Purpose

AubergeLLM is a self-hosted, single-user roleplay frontend that combines:

- A **text connector** for LLM-based roleplay chat (via any OpenAI-compatible API).
- A **character library** with SillyTavern-compatible character cards.
- A lightweight **web UI** (chat + admin) served as static HTML/JS.
- A **connector-based architecture** where text, image, video, and audio backends are all pluggable modules.

**Product positioning:** AubergeLLM is a simplified alternative to SillyTavern, focused on text + image roleplay with a pluggable connector system for all generation backends.

**MVP success criterion:** Time-to-first-roleplay < 1 hour.

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Browser                            │
│  ┌─────────────────┐       ┌──────────────────────┐     │
│  │  Chat UI (HTML) │       │  Admin UI (HTML)     │     │
│  │  /index.html    │       │  /admin/index.html   │     │
│  └────────┬────────┘       └──────────┬───────────┘     │
│           │  REST + SSE               │  REST            │
└───────────┼───────────────────────────┼─────────────────┘
            │                           │
            ▼                           ▼
┌─────────────────────────────────────────────────────────┐
│              AubergeLLM Backend (Python / FastAPI)       │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ │
│  │ Chat     │ │ Character│ │ Connector │ │ Config    │ │
│  │ Service  │ │ Service  │ │ Manager   │ │ Service   │ │
│  └────┬─────┘ └──────────┘ └─────┬─────┘ └───────────┘ │
│       │                          │                      │
└───────┼──────────────────────────┼──────────────────────┘
        │                          │
        ▼                          ▼
┌───────────────┐  ┌───────────────────┐  ┌──────────────┐
│ Text Backend  │  │ Image Backend     │  │ (Post-MVP)   │
│ (Ollama,      │  │ (OpenRouter,      │  │ Video, Audio │
│  OpenAI API,  │  │  OpenAI, ComfyUI) │  │ backends     │
│  OpenRouter)  │  │                   │  │              │
└───────────────┘  └───────────────────┘  └──────────────┘
```

## 3. Components

### 3.1 Frontend — Chat UI

- Static HTML + vanilla JavaScript.
- Communicates with the backend via **REST** (send messages, load characters) and **SSE** (receive streamed LLM responses, image generation status).
- Displays conversation history, character selection, and generated images inline.
- No build step, no framework. Plain files served by the backend.

### 3.2 Frontend — Admin UI

- Static HTML + vanilla JavaScript (separate page/section).
- Connector management: add, configure, test, and switch between connectors for each type (text, image, video, audio).
- Character management: import (JSON/PNG), edit, duplicate, export.
- Communicates with the backend via **REST** only.

### 3.3 Backend — AubergeLLM API

- **Python 3.12+** with **FastAPI**.
- Serves the static frontend files.
- Exposes a REST + SSE API for all operations.
- Organized as internal services (not microservices—just logical modules within one process).
- Stores all data locally as JSON files (no database for MVP).

### 3.4 External: Generation Backends (via Connectors)

AubergeLLM communicates with external services through **connectors**. Each connector is a pluggable module for a specific modality:

- **Text connectors** — Any OpenAI-compatible API (Ollama, vLLM, LM Studio, OpenRouter, OpenAI, etc.) using the chat completions format.
- **Image connectors** — Any OpenAI-compatible image API (OpenRouter → Gemini/DALL-E/Flux, OpenAI directly, etc.) using the `/v1/images/generations` format. Post-MVP: ComfyUI as an advanced image connector.
- **Video connectors** — Post-MVP.
- **Audio connectors** — Post-MVP.

All connectors are configured by the user via the admin interface. See [06 — Connector System](06-connector-system.md) for details.

## 4. Communication Patterns

| Path | Protocol | Usage |
|---|---|---|
| Browser → Backend (chat) | REST POST + SSE | Send user message, stream LLM response tokens |
| Browser → Backend (admin) | REST | CRUD characters, manage connectors, update config |
| Browser → Backend (images) | REST GET | Retrieve generated images |
| Backend → Text connector | HTTP (OpenAI-compatible) | Chat completions (streaming) |
| Backend → Image connector | HTTP (OpenAI-compatible) | Image generation |
| Backend → ComfyUI (post-MVP) | HTTP POST + WebSocket | Submit workflow, monitor execution, retrieve output |

> ⚠️ **Important:** The Chat UI calls **only one endpoint** directly: `POST /api/chat/{id}/message`. All generation backends (image, video, audio connectors) are called **internally by the engine** using the secret internal token (Tier 2) — the frontend never calls them directly. Image generation is triggered automatically by the backend as part of chat processing, never by a dedicated frontend endpoint.

## 5. Data Flow — Chat Message Lifecycle

1. User sends a message via the Chat UI (REST POST to `/api/chat/{conversation_id}/message`).
2. Backend builds the full prompt (system prompt from character card + conversation history + user message).
3. Backend calls the **active text connector** to stream the LLM response back to the client via SSE.
4. If the user triggers image generation, the backend:
   a. Sends the prompt to the **active image connector**.
   b. The connector handles the backend-specific protocol (API call, ComfyUI workflow, etc.).
   c. Retrieves the generated image.
   d. Sends an SSE event to the client with the image URL.
5. The conversation (including image references) is persisted to a JSON file on disk.

## 6. Key Architectural Decisions

| Decision | Rationale |
|---|---|
| **Static HTML + vanilla JS** (no React/Vue) | Simplicity, zero build step, easy to serve, easy to modify. |
| **FastAPI (Python)** | Mature async support, native SSE, good AI ecosystem, fast prototyping. |
| **JSON file storage** (no DB) | Simplest possible persistence for single-user MVP. |
| **SSE** (not WebSocket for chat) | Simpler than WebSocket for unidirectional streaming; sufficient for MVP. |
| **Connector-based architecture** | Decouples core logic from specific backends; new backends = new connector only. |
| **OpenAI-compatible API as default** | De facto standard — works for text (Ollama, vLLM, etc.) and images (OpenRouter, OpenAI). |
| **Single process** | No separate frontend server; FastAPI serves everything. |

## 7. MVP Scope Boundaries

### In Scope

- Single-user, single-process, local deployment.
- Connector system with text and image connector types.
- OpenAI-compatible API backend for both text and image connectors (MVP).
- One active connector per type at a time.
- Character library with SillyTavern-compatible import/export.
- Conversation persistence as JSON files.
- Admin UI for connector management, configuration, and character management.
- Chat UI for roleplay with character selection and image display.

### Out of Scope (Post-MVP)

- Multi-user / authentication.
- Cloud deployment / sync.
- Advanced orchestration (automatic image triggers, style inference).
- ComfyUI connector backend (image/video).
- Video generation connectors (i2v).
- Audio/TTS connectors.
- Plugin system.
- Character marketplace.
- Database storage.
- Quota management per conversation.
- Enforced NSFW protection.
- GUI customization via admin (custom CSS stylesheet, header/footer HTML injection, static asset management).
- Admin interface protection (password and/or IP-based access control).
- OOC protection (if user tries to trick the LLM out of character).
- Hallucination protection (if LLM output is irrelevant, retry with new parameters: different salt, temperature, etc.).
- Multi-character conversations.
- Summary function triggered when max input tokens is reached (threshold configurable in admin GUI).
- Allow use of multiple models per function (chat, summary, classification, etc.).

## 8. Cross-Cutting Concerns

### Error Handling

- Backend returns structured JSON error responses with HTTP status codes.
- Frontend displays user-friendly error messages (e.g., "Cannot reach LLM backend").
- Image connector failures are handled gracefully (chat continues without images).

### Logging

- Python `logging` module, structured output.
- Log level configurable via environment variable.
- **Post-MVP:** Sentry support (user must provide the Sentry DSN URL).

### CORS

- Enabled for local development. Since the backend serves the frontend, CORS is minimal in production.
- **Post-MVP:** When hosted online, automatically detect the `Host` header and adjust CORS origins accordingly.
- **Offline-first:** Avoid loading external libraries (JS/CSS) — prefer vendored files to enable fully offline usage.

### Security (MVP)

- **Two-tier internal token system**: AubergeLLM uses two auto-generated tokens at startup, with distinct scopes:
  - **Session token** (Tier 1): Injected into served HTML pages as a `<meta>` tag. The frontend JS sends it as `X-Session-Token` header on all write endpoints. Protects against external/network-level abuse (bots, port scanners, other LAN devices). Visible to the frontend user via dev tools — this is intentional.
  - **Internal token** (Tier 2): **Never exposed to the frontend**. Used only for backend-internal calls to expensive generation endpoints (`POST /api/generate/image`). Even if a user extracts the session token from the HTML source, they cannot directly trigger image generation — generation is always mediated by the backend through controlled chat-level endpoints. See [03 — Backend API](03-backend-api.md) § 2 for the full route protection table and flow diagram.
- No user authentication beyond the two-tier tokens (single-user, local only).
- No secrets stored in code — configuration in a local file, API keys in connector configs.
- Input sanitization on character card imports (prevent XSS in HTML rendering).
- **Post-MVP:** Any quota/rate-limit system may be based on the session token.

### Configuration and Secrets

- All secrets (connector API keys, etc.) are editable through the admin interface — users may not know how to handle environment variables, so the admin UI is the primary configuration method.
- Power users can also use environment variables (prefixed with `AUBERGELLM_`).
- **Config loading priority order:** environment variables first, then admin-saved config (`config.yaml`).
- Admin parameters are written to a non-versioned `config.yaml` file (`.gitignore`d).
