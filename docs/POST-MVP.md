# Post-MVP Roadmap

This document consolidates all features that are out of scope for the MVP. Other specification documents reference this file; they do not duplicate its items.

## 1. Multi-User Support

- **Per-user session tokens.** Replace the MVP constant `SESSION_TOKEN = "00000000-0000-0000-0000-000000000000"` with a per-client token (cookie or `localStorage`). The token identifier lands naturally in `data/images/{session-token}/` — no file-layout change. See the `# TODO(multi-user): ...` markers in the code.
- **Per-user conversation ownership.** Add an `owner` field to the conversation model; filter `GET /api/conversations` by the caller's session token.
- **Shareable read-only conversation links** (e.g., `?conversation=<uuid>` for cross-session viewing).
- **Authentication** (password and/or IP-based access control; admin-protected section).

## 2. New Connector Backends

- **ComfyUI image/video connector.** Local Stable Diffusion with a workflow abstraction. Uses `POST /prompt`, `GET /history/{prompt_id}`, `GET /view?filename=...`, and a WebSocket for progress monitoring. Requires `websockets` (≥ 12.0). Workflow templates live in `data/comfyui_workflows/` (user-customized) and a shipped-with-package default directory.
- **Video generation connectors** (i2v).
- **Audio / TTS connectors.**

## 3. Infrastructure and Deployment

- **Docker and docker-compose** packaging.
- **Environment-variable overrides** for configuration (MVP intentionally has none).
- **Sentry error tracking** — user provides DSN in config.
- **CORS auto-detection** — detect the `Host` header and adjust allowed origins.
- **Automatic media cleanup** — scheduled or admin-triggered, configurable retention (default 30 days).
- **Database storage** — replace JSON file storage with SQLite or similar.
- **Cloud deployment / sync** — multi-device or hosted scenarios.

## 4. AI Quality and Safety

- **OOC (out-of-character) protection** — detect and block attempts to break the character.
- **Hallucination mitigation** — retry with different sampling on irrelevant outputs.
- **Automatic summarization** — compress history when the input-token budget nears its limit. Threshold configurable.
- **Enforced NSFW protection** — configurable content filtering.

## 5. Advanced Chat Features

- **Automatic image triggering without explicit user request** — today the LLM only emits markers on explicit user request; the post-MVP version may proactively suggest visuals based on scene context.
- **Tool-calling / structured output for image triggers** — replace the `[IMG: …]` marker with native structured outputs on backends that support it.
- **Manual "Generate Image" button** — optional UI fallback to trigger generation explicitly when the LLM does not emit a marker.
- **Multi-character conversations.**
- **Multi-model support** — different models for chat, summarization, classification, etc.
- **Quota management per conversation** — token/cost limits.
- **Image-generation progress updates** — granular progress from connectors that support it (e.g., ComfyUI WS).

## 6. Admin and Customization

- **GUI customization** — custom CSS, header/footer HTML injection, static asset management.
- **Character marketplace** — browse and import community character cards.
- **Regenerated configuration reference** — auto-generated reference doc from Pydantic model comments (previously `make docs` — dropped from MVP).
- **Plugin system** — extensible plugin architecture for third-party integrations.

## 7. Documentation and Installation

- **Installation and quick-start documentation.** The MVP docs focus on architecture and specification; end-user install instructions will be added when the deployment story is finalized (alongside Docker).
