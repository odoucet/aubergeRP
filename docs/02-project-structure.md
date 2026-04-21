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
│   └── openai_image.py          # OpenAI-compatible image connector
├── services/                    # Business logic
│   ├── __init__.py
│   ├── character_service.py
│   ├── conversation_service.py
│   └── chat_service.py          # Prompt building, streaming, image trigger
├── routers/                     # FastAPI route handlers (thin)
│   ├── __init__.py
│   ├── chat.py
│   ├── characters.py
│   ├── conversations.py
│   ├── connectors.py
│   ├── images.py                # GET /api/images/{session-token}/{id}
│   ├── config.py
│   └── health.py
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
├── test_api_characters.py
├── test_api_chat.py             # Streaming + image SSE events
├── test_api_connectors.py
├── test_api_config.py
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
├── characters/                  # {uuid}.json
├── conversations/               # {uuid}.json
├── connectors/                  # {uuid}.json
├── avatars/                     # {character-uuid}.png
└── images/
    └── {session-token}/         # One folder per session (MVP: one constant folder)
        └── {uuid}.png
```

- `data/` is created on first startup if missing.
- `data/` is gitignored.
- `images/{session-token}/` is the seam for future multi-user support. In the MVP, `session-token` is the constant `00000000-0000-0000-0000-000000000000` (see [00 § 9](00-architecture-overview.md)).

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
- Runs startup logic (create data dirs, load config, initialize connector manager).

### `config.py`
- Loads `config.yaml` from disk.
- Validates it with Pydantic.
- Exposes a singleton config object.

### `models/`
- Pure Pydantic models. No business logic.
- Used for API request/response validation and internal data passing.

### `connectors/`
- Each backend is one file.
- All connectors inherit from the base classes in `base.py`.
- `manager.py` handles connector lifecycle (create, configure, activate, test).
- Must not import from `routers/` or `services/`.

### `services/`
- Business logic only.
- Functions or classes with dependencies injected explicitly (config, file paths, connectors).
- Must not import from `routers/`.

### `routers/`
- Thin. Receive HTTP requests, call services, return responses.
- No business logic.
- Each router is a `fastapi.APIRouter`.

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
