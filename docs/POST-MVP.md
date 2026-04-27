# Post-MVP Roadmap

This document lists features that are not yet implemented. Items that have been completed are no longer listed here — see the git history for the full sprint log.

## 1. Multi-User Support

- **Per-user session tokens.** Replace the constant `SESSION_TOKEN = "00000000-0000-0000-0000-000000000000"` with a per-client token (cookie or `localStorage`). The token identifier lands naturally in `data/images/{session-token}/` — no file-layout change. See the `# TODO(multi-user): ...` markers in the code.
- **Per-user conversation ownership.** The `owner` column exists in the `conversations` table but is not yet populated or used for filtering. Filter `GET /api/conversations` by the caller's session token.
- **Shareable read-only conversation links** (e.g., `?conversation=<uuid>` for cross-session viewing).
- **Authentication** (password and/or IP-based access control; admin-protected section).

## 2. New Connector Backends

- **Video generation connectors** (i2v).
- **Audio / TTS connectors.**

## 3. Infrastructure and Deployment

- **Cloud deployment / sync** — multi-device or hosted scenarios.

## 4. AI Quality and Safety

- **Hallucination mitigation** — retry with different sampling on irrelevant outputs.
- **Enforced NSFW protection** — configurable content filtering.

## 5. Advanced Chat Features

- **Automatic image triggering without explicit user request** — today the LLM only emits markers on explicit user request; a future version may proactively suggest visuals based on scene context.
- **Manual "Generate Image" button** — optional UI fallback to trigger generation explicitly when the LLM does not emit a marker.
- **Multi-character conversations.**
- **Multi-model support** — different models for chat, summarization, classification, etc.
- **Quota management per conversation** — token/cost limits.
