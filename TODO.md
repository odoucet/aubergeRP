# TODO

Items not yet implemented. PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## High priority

- [ ] **Full user authentication** — password or IP-allowlist protecting the chat UI (the admin panel already has its own password). Config: `app.auth_mode` (`none` | `password` | `ip_allowlist`).

---

## Medium priority

- [ ] **Manual "Generate Image" button** — UI fallback to trigger image generation without relying on the LLM emitting a `[IMG: …]` marker.
- [ ] **Hallucination mitigation** — detect clearly off-topic or repetitive responses; retry with a corrective system message. Config: `chat.hallucination_retry`.
- [ ] **Configurable NSFW filter** — pre/post-processing layer. Config: `chat.nsfw_filter` (`off` | `warn` | `block`).

---

## Low priority / Future

- [ ] **Multi-character conversations** — more than one character per conversation.
- [ ] **Multi-model support** — separate connectors for chat, summarization, and classification.
- [ ] **Proactive image triggering** — LLM decides on its own when to emit an image (not only on explicit user request).
- [ ] **Quota management** — per-conversation token or cost limit.
- [ ] **Video generation connector** (`[VID: …]` marker, `VideoConnector` interface).
- [ ] **Audio/TTS connector** — play synthesized speech after each assistant message.
- [ ] **Cloud deployment / sync** — hosted SQLite (Turso/LiteFS), Postgres backend, or backup to object storage.
- [ ] Handle storing version (used in GUI and API).
---

## Documentation / housekeeping

- [ ] Write usage examples: OpenRouter API key setup, local Ollama, ComfyUI, importing SillyTavern characters.
- [ ] Document Docker GPU profiles => auto generate doc based on `docker/profiles/*.yaml` files.
