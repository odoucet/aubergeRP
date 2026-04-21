# Post-MVP Roadmap

This document consolidates all planned features that are out of scope for the MVP. Individual specification documents reference this file for post-MVP items.

## 1. New Connector Backends

- **ComfyUI image/video connector** — local Stable Diffusion with workflow abstraction. Uses `POST /prompt`, `GET /history/{prompt_id}`, `GET /view?filename=...`, and WebSocket for progress monitoring. Requires the `websockets` Python library (≥ 12.0).
- **Video generation connectors** (i2v).
- **Audio/TTS connectors**.

## 2. Infrastructure and Deployment

- **Docker and docker-compose** packaging for easy deployment.
- **Sentry error tracking** — user provides the Sentry DSN URL; errors and exceptions are forwarded to their Sentry instance.
- **CORS auto-detection** — when hosted online, automatically detect the `Host` header and adjust CORS allowed origins accordingly.
- **Automatic media cleanup** — a scheduled or admin-triggered action to delete generated media files older than X days. X is configurable in the admin UI (default: 30 days).

## 3. AI Quality and Safety

- **OOC (out-of-character) protection** — detect and block attempts by the user to trick the LLM out of its character.
- **Hallucination protection** — if the LLM outputs something irrelevant or unexpected, automatically retry with new parameters (different salt, temperature, or sampling strategy — exact parameters TBD).
- **Summary function** — automatically summarize conversation history when the max input token threshold is reached. Threshold is configurable in the admin UI.

## 4. Advanced Features

- **Multi-character conversations** (complex; requires significant rework of the conversation and prompt-building system).
- **Multi-model support** — allow different models to be configured for different functions (chat, summarization, classification, etc.).
- **Quota management per conversation** — track and enforce token or cost limits per conversation.
- **Enforced NSFW protection** — configurable content filtering.

## 5. Admin and Customization

- **GUI customization via admin** — custom CSS stylesheet, header/footer HTML injection, static asset management.
- **Admin interface protection** — password-based and/or IP-based access control for the admin UI.
- **Character marketplace** — browse and import community character cards.

## 6. Infrastructure and Storage

- **Database storage** — replace JSON file storage with a proper database (e.g., SQLite) for better scalability and query capability.
- **Cloud deployment and sync** — support for multi-device or cloud-hosted scenarios.
- **Plugin system** — extensible plugin architecture for third-party integrations.
