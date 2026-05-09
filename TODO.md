# TODO

Items not yet implemented. PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

When using the project and navigating, I sometimes add items here that I think are missing or could be improved. This is not an exhaustive list of all the work that needs to be done, but it gives an idea of the current state of the project and the next steps.

---

## High priority

- [x] **JWT admin authentication** — replace the current in-memory session token store (`_admin_sessions: set[str]`) with stateless JWT tokens signed with a server secret. This removes the multi-worker incompatibility (each uvicorn worker has its own in-memory set), adds configurable token expiry, and makes tokens survive server restarts without requiring Redis. See `aubergeRP/routers/admin.py`.

- [ ] **Admin error log viewer** — expose a `/api/admin/logs` endpoint (or a dedicated admin UI page) so administrators can inspect recent server errors without SSH access. This is especially useful to diagnose image-generation failures, since connector errors are currently logged server-side only and replaced by a generic message in the UI.

---

## Medium priority

- [ ] **Hallucination mitigation** — detect clearly off-topic or repetitive responses; retry with a corrective system message. Config: `chat.hallucination_retry`.

- [ ] **Configurable NSFW filter** — pre/post-processing layer. Config: `chat.nsfw_filter` (`off` | `warn` | `block`). Actually the implementation is very incomplete, with just a declaration on connectors but no actual filtering logic. There is a prompt for this, make sure it is used correctly. 
On frontend, all images generated with an NSFW connector must be blurried by default and visible only when the user clicks on them.

- [ ] **Periodic connector health checks** — `_TestResultsStore` in `routers/connectors.py` currently reloads from disk on every call to `.get()` (including the `/api/health` endpoint). A better approach: run `test_connector()` for each active connector on a schedule (e.g. every 5 minutes) in the background scheduler, persist the result once, and have `/api/health` return the last known state. This avoids disk I/O on every health poll and gives operators a real-time liveness signal without user-triggered tests.

- [ ] Test ComfyUI connector with a real Comfy instance and fix any issues. The connector code is currently untested and may require adjustments to work with the actual Comfy API.

---

## Low priority / Future

- [ ] **Standalone Dockerfile** — the current `Dockerfile` requires the repository to be cloned locally because `aubergeRP/` and `frontend/` are bind-mounted at runtime (see `docker/docker-compose.yml`). Add a `Dockerfile.standalone` that `COPY`s the source into the image so the app can be distributed as a self-contained Docker image (e.g. on Docker Hub) without needing the repository on the host.
- [ ] **Full user authentication** — password or IP-allowlist protecting the chat UI (the admin panel already has its own password). Config: `app.auth_mode` (`none` | `password` | `ip_allowlist`).
- [x] **Admin session expiry** — admin tokens currently live until the server restarts or an explicit logout. Add a configurable TTL (e.g. 24 h) so leaked tokens eventually expire.
- [ ] **Multi-character conversations** — more than one character per conversation.
- [ ] **Multi-model support** — separate connectors for chat, summarization, and classification.
- [ ] **Proactive image triggering** — LLM decides on its own when to emit an image (not only on explicit user request). Maybe work on the system prompt to let the LLM know it can do this ?
- [ ] **Quota management** — per-conversation token limit, when connecting external APIs with quotas (like OpenAI). 
- [ ] **Video generation connector** (`[VID: …]` marker, `VideoConnector` interface) — currently hidden from the UI until implemented. Design the connector interface, define the SSE event flow, and add UI controls for video playback.
- [ ] **Audio/TTS connector** — play synthesized speech after each assistant message. Currently hidden from the UI. Design the connector interface and add playback controls to the chat UI.
- [ ] Maintain a list of character cards websites. Actually : 
      * https://jannyai.com/characters
- [ ] One-click translation of a character card in another language, using the LLM. This is a common user request and would be a nice feature to have. It could be implemented as a button on the admin panel, next to each character, that triggers the translation process.

---

## Documentation / housekeeping

- [ ] Write usage examples: OpenRouter API key setup, local Ollama, ComfyUI, importing SillyTavern characters.
- [ ] Document Docker GPU profiles => auto generate doc based on `docker/profiles/*.yaml` files with LLM used and size (note: where to grab this info ?).
- [ ] **Environment variables reference** — create a `docs/env-vars.md` file listing every supported environment variable with its default, description, and security notes (especially `AUBERGE_DISABLE_ADMIN_AUTH`). This page should be auto-generated by `make doc` using the existing `scripts/generate_api_docs.py` script (or a companion script).
