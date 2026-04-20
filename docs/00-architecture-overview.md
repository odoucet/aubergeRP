# 00 — Architecture Overview

## 1. Purpose

AubergeLLM is a self-hosted, single-user roleplay frontend that combines:

- An **LLM backend** for text-based roleplay chat.
- A **character library** with SillyTavern-compatible character cards.
- A **ComfyUI backend** for image generation triggered from conversations.
- A lightweight **web UI** (chat + admin) served as static HTML/JS.

**Product positioning:** AubergeLLM is a simplified alternative to SillyTavern, focused on text + image roleplay with structured ComfyUI integration.

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
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Chat     │ │ Character│ │ ComfyUI  │ │ Config    │  │
│  │ Service  │ │ Service  │ │ Service  │ │ Service   │  │
│  └────┬─────┘ └──────────┘ └────┬─────┘ └───────────┘  │
│       │                         │                       │
└───────┼─────────────────────────┼───────────────────────┘
        │                         │
        ▼                         ▼
┌───────────────┐        ┌────────────────┐
│  LLM Backend  │        │   ComfyUI      │
│  (Ollama,     │        │   Instance     │
│   OpenAI API) │        │                │
└───────────────┘        └────────────────┘
```

## 3. Components

### 3.1 Frontend — Chat UI

- Static HTML + vanilla JavaScript.
- Communicates with the backend via **REST** (send messages, load characters) and **SSE** (receive streamed LLM responses, image generation status).
- Displays conversation history, character selection, and generated images inline.
- No build step, no framework. Plain files served by the backend.

### 3.2 Frontend — Admin UI

- Static HTML + vanilla JavaScript (separate page/section).
- Allows configuration of LLM backend URL, ComfyUI URL.
- Character management: import (JSON/PNG), edit, duplicate, export.
- Communicates with the backend via **REST** only.

### 3.3 Backend — AubergeLLM API

- **Python 3.10+** with **FastAPI**.
- Serves the static frontend files.
- Exposes a REST + SSE API for all operations.
- Organized as internal services (not microservices—just logical modules within one process).
- Stores all data locally as JSON files (no database for MVP).

### 3.4 External: LLM Backend

- Any OpenAI-compatible API (Ollama, vLLM, LM Studio, text-generation-webui, remote OpenAI, etc.).
- The backend communicates with it using the OpenAI chat completions format.
- Configured by the user via the admin interface.

### 3.5 External: ComfyUI

- A running ComfyUI instance, local or remote.
- AubergeLLM interacts with it via its HTTP + WebSocket API.
- Configured by the user via the admin interface.

## 4. Communication Patterns

| Path | Protocol | Usage |
|---|---|---|
| Browser → Backend (chat) | REST POST + SSE | Send user message, stream LLM response tokens |
| Browser → Backend (admin) | REST | CRUD characters, update config |
| Browser → Backend (images) | REST GET | Retrieve generated images |
| Backend → LLM | HTTP (OpenAI-compatible) | Chat completions (streaming) |
| Backend → ComfyUI | HTTP POST + WebSocket | Submit workflow, monitor execution, retrieve output |

## 5. Data Flow — Chat Message Lifecycle

1. User sends a message via the Chat UI (REST POST to `/api/chat/{conversation_id}/message`).
2. Backend builds the full prompt (system prompt from character card + conversation history + user message).
3. Backend streams the LLM response back to the client via SSE.
4. If the LLM response or user message triggers image generation, the backend:
   a. Builds a ComfyUI workflow payload from the configured workflow template.
   b. Submits it to ComfyUI.
   c. Monitors execution via WebSocket.
   d. Retrieves the generated image.
   e. Sends an SSE event to the client with the image URL.
5. The conversation (including image references) is persisted to a JSON file on disk.

## 6. Key Architectural Decisions

| Decision | Rationale |
|---|---|
| **Static HTML + vanilla JS** (no React/Vue) | Simplicity, zero build step, easy to serve, easy to modify. |
| **FastAPI (Python)** | Mature async support, native SSE, good OpenAI/ComfyUI ecosystem, fast prototyping. |
| **JSON file storage** (no DB) | Simplest possible persistence for single-user MVP. |
| **SSE** (not WebSocket for chat) | Simpler than WebSocket for unidirectional streaming; sufficient for MVP. |
| **OpenAI-compatible API format** | De facto standard supported by Ollama, vLLM, LM Studio, etc. |
| **Workflow abstraction layer** | Decouples UI/business logic from raw ComfyUI graph format. |
| **Single process** | No separate frontend server; FastAPI serves everything. |

## 7. MVP Scope Boundaries

### In Scope

- Single-user, single-process, local deployment.
- One LLM backend at a time.
- One ComfyUI instance at a time.
- One image generation workflow (text-to-image).
- Character library with SillyTavern-compatible import/export.
- Conversation persistence as JSON files.
- Admin UI for configuration and character management.
- Chat UI for roleplay with character selection and image display.

### Out of Scope (Post-MVP)

- Multi-user / authentication.
- Cloud deployment / sync.
- Advanced orchestration (automatic image triggers, style inference).
- Video generation (i2v).
- Plugin system.
- Character marketplace.
- Database storage.

## 8. Cross-Cutting Concerns

### Error Handling

- Backend returns structured JSON error responses with HTTP status codes.
- Frontend displays user-friendly error messages (e.g., "Cannot reach LLM backend").
- ComfyUI connection failures are handled gracefully (chat continues without images).

### Logging

- Python `logging` module, structured output.
- Log level configurable via environment variable.

### CORS

- Enabled for local development. Since the backend serves the frontend, CORS is minimal in production.

### Security (MVP)

- No authentication (single-user, local only).
- No secrets stored in code—configuration in a local file.
- Input sanitization on character card imports (prevent XSS in HTML rendering).
