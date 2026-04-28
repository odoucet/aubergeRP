# Architecture Overview

## Design goals

- **Simplicity first.** Single-user local deployment. No microservices.
- **Pluggable connectors.** Every external backend (LLM, image generator) is a connector module. Swapping backends requires no core changes.
- **Zero-build frontend.** Static HTML + vanilla JS served directly by FastAPI.

## High-level diagram

```
Browser (Chat UI + Admin UI)
        │ REST + SSE
        ▼
aubergeRP API (FastAPI, Python 3.12)
        │
        ▼
ConnectorManager
   ├── TextConnector  → any OpenAI-compatible chat API (LocalAI, OpenRouter, …)
   └── ImageConnector → any OpenAI-compatible image API, or ComfyUI
```

## Key decisions

| Decision | Rationale |
|---|---|
| Static HTML + vanilla JS | Zero build step |
| FastAPI (Python) | Async, native SSE, strong AI ecosystem |
| SQLite via SQLModel | No separate DB server; migrations run automatically |
| SSE (not WebSocket) | Simpler for one-directional LLM token streaming |
| OpenAI-compatible API | De facto standard for both text and images |

## Data flow — sending a message

1. `POST /api/chat/{conversation_id}/message`
2. Backend builds prompt (system prompt + character fields + history + user message).
3. Active text connector streams tokens → forwarded as `token` SSE events.
4. If the LLM emits `[IMG: <prompt>]`, the backend strips the marker, calls the active image connector, and emits `image_start` / `image_complete` / `image_failed` events.
5. On completion, the full message (text + image URLs) is persisted in SQLite.

## Storage

| What | Where |
|---|---|
| Characters, conversations, messages, LLM stats | `data/auberge.db` (SQLite) |
| Connector config | `data/connectors/{uuid}.json` |
| Avatars | `data/avatars/{uuid}.png` |
| Generated images | `data/images/{session-token}/{uuid}.png` |
| Active connector selection | `config.yaml → active_connectors` |

See [02-project-structure.md](02-project-structure.md) for the full file layout.
