# 02 — Project Structure

This document is the **single source of truth** for file layout (repo, backend, frontend, data).

## 1. Top-Level Layout

```
aubergeRP/
├── docs/                        # Specification documents (this folder)
├── frontend/                    # Static HTML/JS/CSS frontend
├── aubergeRP/                   # Python backend package
├── tests/                       # Backend tests
├── data/                        # Runtime data (gitignored)
├── config.example.yaml          # Example configuration file
├── requirements.txt             # Pinned Python dependencies
├── pyproject.toml               # Project metadata + tool configuration
├── Makefile                     # Developer targets (lint, test, run)
├── Dockerfile                   # Container image definition
├── docker-compose.yml           # Docker Compose service definition
├── README.md
└── LICENSE
```

## 2. Backend Package: `aubergeRP/`

```
aubergeRP/
├── __init__.py
├── main.py                      # FastAPI app, route mounting, startup
├── config.py                    # Configuration loading and validation
├── constants.py                 # SESSION_TOKEN constant (see 00 § 9)
├── database.py                  # SQLite engine + session management
├── db_models.py                 # SQLModel table definitions (CharacterRow, ConversationRow, …)
├── event_bus.py                 # In-process async event bus
├── scheduler.py                 # Background media-cleanup scheduler
├── models/                      # Pydantic data models
│   ├── __init__.py
│   ├── character.py
│   ├── conversation.py
│   ├── chat.py
│   ├── connector.py
│   └── config.py
├── connectors/                  # Connector implementations
│   ├── __init__.py
│   ├── base.py                  # Abstract base classes
│   ├── manager.py               # ConnectorManager — registry + lifecycle
│   ├── openai_text.py           # OpenAI-compatible text connector
│   ├── openai_image.py          # OpenAI-compatible image connector
│   └── comfyui.py               # ComfyUI image connector (local SD)
├── comfyui_workflows/           # Built-in ComfyUI workflow templates (JSON)
├── migrations/                  # Numbered SQLite migration scripts
│   └── __init__.py
├── services/                    # Business logic
│   ├── __init__.py
│   ├── character_service.py
│   ├── conversation_service.py
│   ├── chat_service.py          # Prompt building, streaming, image trigger
│   └── summarization_service.py # Automatic conversation summarization
├── routers/                     # FastAPI route handlers (thin)
│   ├── __init__.py
│   ├── chat.py
│   ├── characters.py
│   ├── conversations.py
│   ├── connectors.py
│   ├── images.py                # GET /api/images/…, POST /api/images/cleanup
│   ├── config.py
│   ├── health.py
│   └── marketplace.py           # GET /api/marketplace/search
├── plugins/                     # Plugin system
│   ├── __init__.py
│   ├── base.py                  # BasePlugin abstract class
│   └── manager.py               # PluginManager — discover, load, call_hook
└── utils/                       # Shared helpers
    ├── __init__.py
    ├── png_metadata.py          # PNG tEXt chunks for character cards
    └── file_storage.py          # Atomic JSON read/write
```

## 3. Frontend: `frontend/`

```
frontend/
├── index.html                   # Chat UI
├── admin/
│   └── index.html               # Admin UI
├── css/
│   ├── main.css                 # Chat UI styles
│   └── admin.css                # Admin UI styles
├── js/
│   ├── api.js                   # Shared API client (fetch wrappers)
│   ├── chat.js                  # Chat logic (SSE, messages, images)
│   ├── characters.js            # Character selection sidebar
│   ├── admin/
│   │   ├── characters.js
│   │   └── connectors.js
│   └── vendor/
│       └── marked.min.js        # Vendored markdown renderer
└── assets/
    ├── logo.svg
    └── default-avatar.png
```

## 4. Tests: `tests/`

```
tests/
├── conftest.py                  # Shared fixtures
├── test_character_service.py
├── test_conversation_service.py
├── test_chat_service.py         # Prompt building + image marker parsing
├── test_connector_manager.py
├── test_openai_text.py          # Mocked HTTP
├── test_openai_image.py         # Mocked HTTP
├── test_comfyui_connector.py    # Mocked HTTP + WS
├── test_api_characters.py
├── test_api_chat.py             # Streaming + image SSE events
├── test_api_connectors.py
├── test_api_config.py
├── test_config.py
├── test_models.py
├── test_file_storage.py
├── test_png_metadata.py
└── fixtures/
    ├── sample_character_v1.json
    ├── sample_character_v2.json
    ├── sample_character_v1.png
    ├── sample_character_v2.png
    └── sample_connector.json
```

SillyTavern compatibility: a dedicated unit test **must** verify that both V1 and V2 character cards (JSON and PNG) parse correctly. Fixtures live in `tests/fixtures/`.

## 5. Data Directory: `data/`

```
data/
├── auberge.db                   # SQLite database (characters, conversations, messages)
├── connectors/                  # {uuid}.json — one file per connector instance
├── avatars/                     # {character-uuid}.png
├── comfyui_workflows/           # User ComfyUI workflow templates (JSON)
└── images/
    └── {session-token}/         # One folder per session (currently: one constant folder)
        └── {uuid}.png
```

- `data/` is created on first startup if missing.
- `data/` is gitignored.
- `images/{session-token}/` is the seam for future multi-user support. In the current single-user setup, `session-token` is the constant `00000000-0000-0000-0000-000000000000` (see [00 § 9](00-architecture-overview.md)).
- `comfyui_workflows/` is seeded from `aubergeRP/comfyui_workflows/` (built-in templates) on first startup. User files are never overwritten.

## 6. Configuration Files

| File | Purpose | Tracked in Git |
|---|---|---|
| `config.example.yaml` | Example config | Yes |
| `config.yaml` | User's actual config | No |
| `pyproject.toml` | Project metadata, ruff/mypy/pytest config | Yes |
| `requirements.txt` | Pinned Python dependencies | Yes |
| `.gitignore` | Ignore patterns | Yes |

## 7. Module Responsibilities

### `main.py`
- Creates the FastAPI app.
- Mounts all routers under `/api/`.
- Mounts the `frontend/` directory as static files at `/`.
- Runs startup logic (create data dirs, load config, initialize SQLite, start scheduler).
- Applies CORS auto-detection middleware.
- Initializes Sentry if `app.sentry_dsn` is configured.

### `database.py`
- Manages the SQLite engine singleton.
- Exposes `init_db()` (creates tables + runs migrations) and `get_session()` (FastAPI dependency).

### `db_models.py`
- SQLModel table definitions: `CharacterRow`, `ConversationRow`, `MessageRow`, `SchemaMigration`.

### `scheduler.py`
- Background asyncio task for periodic media cleanup (image files older than a configurable threshold).

### `config.py`
- Loads `config.yaml` from disk.
- Validates it with Pydantic.
- Applies environment-variable overrides (see [09 § 1](09-configuration-and-setup.md)).
- Exposes a singleton config object.

### `models/`
- Pure Pydantic models. No business logic.
- Used for API request/response validation and internal data passing.

### `connectors/`
- Each backend is one file.
- All connectors inherit from the base classes in `base.py`.
- `manager.py` handles connector lifecycle (create, configure, activate, test).
- Must not import from `routers/` or `services/`.

### `migrations/`
- Numbered Python migration scripts run automatically on startup by `init_db()`.
- Each migration is a simple function; the framework tracks applied versions in `schema_migrations`.

### `services/`
- Business logic only.
- Functions or classes with dependencies injected explicitly (config, DB session, connectors).
- Must not import from `routers/`.

### `routers/`
- Thin. Receive HTTP requests, call services, return responses.
- No business logic.
- Each router is a `fastapi.APIRouter`.

### `plugins/`
- `base.py`: `BasePlugin` abstract class with life-cycle and message/image/connector hooks.
- `manager.py`: `PluginManager` discovers, loads, and calls plugin hooks.

### `utils/`
- Shared helpers. No imports from `services/` or `routers/`.

## 8. Import Rules

```
routers → services → models
routers → connectors
services → connectors → models
services → utils
connectors → utils
```

Circular imports are forbidden.

## 9. Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Python files | `snake_case.py` | `character_service.py` |
| Python classes | `PascalCase` | `CharacterCard` |
| Python functions | `snake_case` | `import_character()` |
| API routes | `kebab-case` | `/api/characters`, `/api/generate-image/status` |
| JS files | `kebab-case.js` | `chat.js`, `api.js` |
| JSON data files | `{uuid}.json` | `a1b2c3d4-….json` |
| YAML config keys | `snake_case` | `active_connectors`, `log_level` |

## 10. Git Conventions

- Branch from `main` for each feature.
- Commit messages: `type: short description` (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`).
- One logical change per commit.
