# Post-MVP Roadmap

This document lists features that are not yet implemented. Items that have been completed are no longer listed here — see the git history for the full sprint log.

## 1. Multi-User Support

- **Authentication** (password and/or IP-based access control; admin-protected section). Note: session scoping (per-user token, conversation ownership, image isolation, session sharing, multi-browser SSE) is already fully implemented.

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
