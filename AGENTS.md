# AGENTS.md — Context for AI coding agents

This file captures things that an agent working on aubergeRP should know up
front to avoid wasted exploration and common mistakes.

---

## Project at a glance

aubergeRP is a **self-hostable roleplay engine** built with:

- **Backend:** Python 3.12 + FastAPI + SQLModel (SQLite)
- **Frontend:** Vanilla HTML/JS/CSS — no framework, no build step
- **Connectors:** pluggable modules for text (LLM) and image generation; one
  active connector per type at a time

The single-page docs are in `docs/`. Read them in numeric order for
architecture context; the spec files are the ground truth for intended
behaviour.

---

## Storage: it is SQLite, not JSON files

The `data/` directory on disk no longer stores `characters/*.json` or
`conversations/*.json`. **All characters, conversations, and messages live in
`data/auberge.db`** (SQLite, managed by SQLModel).

- DB models: `aubergeRP/db_models.py` (`CharacterRow`, `ConversationRow`,
  `MessageRow`, `SchemaMigration`)
- Engine / session: `aubergeRP/database.py` (`get_engine()`, `get_session()`)
- Migrations: `aubergeRP/migrations/` — numbered Python files; run
  automatically at startup via `init_db()`. Use this pattern for schema
  changes instead of touching `db_models.py` alone.
- The `m001_initial.py` migration imports legacy JSON flat-files (if any)
  into SQLite on first boot — this is a one-time upgrade path.

**Connector config files** (`data/connectors/*.json`) and **avatars/images**
still live on disk as plain files.

---

## Session tokens — fully implemented

Per-user isolation is fully implemented and requires no further work:

| Layer | Mechanism |
|---|---|
| Frontend | `crypto.randomUUID()` stored in `localStorage` under key `auberge_session_token` |
| Frontend | Sent as `X-Session-Token` header on every API call |
| Frontend | `?token=<uuid>` URL param accepted on load (for session sharing) |
| Frontend | "Share session" button (`share-session-btn`) calls `copyShareUrl()` from `api.js` |
| Backend | `get_session_token()` dependency reads `X-Session-Token` in `routers/chat.py` and `routers/conversations.py` |
| Backend | Images stored at `data/images/{session_token}/` (per user) |
| Backend | `ConversationRow.owner` stores the token; `list_conversations()` filters by it |
| Backend | `EventBus` in `event_bus.py` scopes SSE queues to `(session_token, conversation_id)` |
| Backend | `GET /api/chat/{id}/events` lets additional browser tabs subscribe without sending a new message |

The constant `SESSION_TOKEN = "00000000-..."` in `constants.py` is a legacy
artefact — it is imported but unused in `main.py`. Ignore it.

---

## How to run tests

```bash
cd /home/runner/work/aubergeRP/aubergeRP
pip install -r requirements.txt   # once
pytest                             # all tests
pytest tests/test_api_chat.py     # one file
pytest -x                         # stop on first failure
```

Tests use `pytest-asyncio` for async test functions and `respx` for mocking
`httpx` HTTP calls (connector backends). The test fixtures create an in-memory
or temp-dir SQLite database — see `tests/conftest.py`.

**No separate lint/build step is required before tests**, but the CI runs
`ruff check .` and `mypy`. Run those locally before submitting:

```bash
ruff check .
mypy aubergeRP/
```

---

## Key file map

| What you want | Where to look |
|---|---|
| FastAPI app / startup | `aubergeRP/main.py` |
| Config schema + loading | `aubergeRP/config.py` |
| SQLite DB engine | `aubergeRP/database.py` |
| SQLModel tables | `aubergeRP/db_models.py` |
| Migrations | `aubergeRP/migrations/` |
| Connector interfaces (ABC) | `aubergeRP/connectors/base.py` |
| Connector registry | `aubergeRP/connectors/manager.py` |
| OpenAI text connector | `aubergeRP/connectors/openai_text.py` |
| OpenAI image connector | `aubergeRP/connectors/openai_image.py` |
| ComfyUI connector | `aubergeRP/connectors/comfyui.py` |
| Chat flow + image markers | `aubergeRP/services/chat_service.py` |
| OOC detection | `aubergeRP/services/chat_service.py` (top of file) |
| Conversation summarization | `aubergeRP/services/summarization_service.py` |
| Character CRUD | `aubergeRP/services/character_service.py` |
| Conversation CRUD | `aubergeRP/services/conversation_service.py` |
| Multi-browser SSE bus | `aubergeRP/event_bus.py` |
| Background scheduler | `aubergeRP/scheduler.py` |
| Plugin system | `aubergeRP/plugins/` |
| API routes | `aubergeRP/routers/` (one file per resource) |
| REST+SSE API spec | `docs/03-backend-api.md` |
| Remaining work | `sprints.txt` |
| Unimplemented features | `docs/POST-MVP.md` |

---

## Architecture rules to preserve

1. **Routers are thin.** No business logic in `routers/`. Delegate everything
   to a service class.
2. **Services own all logic.** They receive explicit dependencies (config,
   DB session, connector manager). They must NOT import from `routers/`.
3. **Connectors are isolated.** Adding a new backend = one new file in
   `connectors/`. Register it in `connectors/manager.py`; no other changes.
4. **Every schema change needs a migration.** Add a new numbered file in
   `aubergeRP/migrations/` following the `m{version:03d}_{slug}.py` pattern
   and expose a `migrate(session: Session) -> None` function.
5. **Atomic writes for files.** Connector JSON files use write-to-temp +
   `os.rename` (see `utils/file_storage.py`). DB writes use SQLAlchemy sessions.

---

## Common pitfalls

- **Do not look for character/conversation data in JSON files.** The
  `data/characters/` and `data/conversations/` directories exist only for
  legacy migration compatibility. All live data is in SQLite.
- **`SESSION_TOKEN` constant is unused in the real request path.** The
  actual per-user token comes from the `X-Session-Token` request header.
  Do not use the constant when writing new per-user-scoped code.
- **Frontend imports use ES module syntax** (`import … from './api.js'`).
  There is no bundler — browsers load the files directly. Keep each JS file
  self-contained and import only from sibling files.
- **No authentication currently.** The app is single-user by design and has
  no login wall. Do not add auth middleware without a spec from a sprint.
- **config.yaml is authoritative for active connectors.** The `is_active`
  flag in API responses is derived at read time — it is never stored in the
  connector JSON file.
- **`data/auberge.db` is the canonical store.** Do not write character or
  conversation data to JSON files. Migration m001 only runs once.

---

## Adding a new connector backend (quick reference)

1. Create `aubergeRP/connectors/my_backend.py`.
2. Subclass `TextConnector` or `ImageConnector` from `connectors/base.py`.
3. Set `backend_id = "my_backend"` on the class.
4. Add a Pydantic config model in `aubergeRP/models/connector.py`.
5. Register the backend in `ConnectorManager._get_connector_class()` in
   `connectors/manager.py`.
6. Add it to `GET /api/connectors/backends` in `routers/connectors.py`.
7. Write tests in `tests/test_my_backend.py` (use `respx` to mock HTTP).

---

## Adding a new migration (quick reference)

1. Create `aubergeRP/migrations/m{NNN}_{slug}.py` (e.g. `m002_add_tags.py`).
2. Implement `def migrate(session: Session) -> None:`.
3. Register it in `aubergeRP/migrations/__init__.py` inside
   `_builtin_migrations()`.
4. Run `pytest` — the in-test DB will apply the migration automatically.
