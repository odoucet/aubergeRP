# 02 — Project Structure

> **Cross-references:** This document details the precise file and module layout. For architecture rationale, see [`00-architecture-overview.md`](00-architecture-overview.md). For technology choices and the data directory structure, see [`01-technology-stack.md`](01-technology-stack.md).

## 1. Top-Level Layout

```
aubergellm/
├── docs/                        # Specification documents (this folder)
├── frontend/                    # Static HTML/JS/CSS frontend
├── aubergellm/                  # Backend
├── tests/                       # Backend tests
├── data/                        # Runtime data (characters, conversations, images)
├── config.example.yaml          # Example configuration file
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Project metadata and tool configuration
├── Makefile                     # Developer convenience targets (lint, test, run)
├── README.md                    # Project README
└── LICENSE                      # Apache 2.0 license
```

## 2. Backend Package: `aubergellm/`

```
aubergellm/
├── __init__.py
├── main.py                      # FastAPI app initialization, route mounting, startup
├── config.py                    # Configuration loading and validation
├── models/                      # Pydantic data models
│   ├── __init__.py
│   ├── character.py             # Character card models (internal + SillyTavern)
│   ├── conversation.py          # Conversation and message models
│   ├── chat.py                  # Chat request/response models
│   ├── connector.py             # Connector instance and config models
│   └── config.py                # Configuration models
├── connectors/                  # Connector implementations (pluggable backends)
│   ├── __init__.py
│   ├── base.py                  # Abstract base classes (TextConnector, ImageConnector, etc.)
│   ├── manager.py               # ConnectorManager — registry and lifecycle
│   ├── openai_text.py           # OpenAI-compatible text connector
│   └── openai_image.py          # OpenAI-compatible image connector
├── services/                    # Business logic services
│   ├── __init__.py
│   ├── character_service.py     # Character CRUD, import/export
│   ├── conversation_service.py  # Conversation persistence and retrieval
│   └── chat_service.py          # Prompt building, LLM interaction, response streaming
├── routers/                     # FastAPI route handlers
│   ├── __init__.py
│   ├── chat.py                  # POST /api/chat/... , SSE streaming
│   ├── characters.py            # GET/POST/PUT/DELETE /api/characters/...
│   ├── conversations.py         # GET/POST/DELETE /api/conversations/...
│   ├── connectors.py            # GET/POST/PUT/DELETE /api/connectors/...
│   ├── generate.py              # POST /api/generate/image, GET /api/images/...
│   ├── config.py                # GET/PUT /api/config
│   └── health.py                # GET /api/health
├── utils/                       # Shared utilities
│   ├── __init__.py
│   ├── png_metadata.py          # Read/write PNG tEXt chunks (character card metadata)
│   └── file_storage.py          # JSON file read/write helpers
└── resources/                   # Bundled static resources
    └── comfyui_workflows/       # Default ComfyUI workflow templates (future)
        └── default_t2i.json
```

## 3. Frontend: `frontend/`

```
frontend/
├── index.html                   # Chat UI entry point
├── admin/
│   └── index.html               # Admin UI entry point
├── css/
│   ├── main.css                 # Chat UI styles
│   └── admin.css                # Admin UI styles
├── js/
│   ├── api.js                   # Shared API client (fetch wrappers)
│   ├── chat.js                  # Chat UI logic (messages, SSE, image display)
│   ├── characters.js            # Character selection sidebar logic
│   ├── images.js                # Inline image display logic
│   ├── admin/
│   │   ├── config.js            # Admin config management logic
│   │   ├── characters.js        # Admin character CRUD logic
│   │   └── connectors.js        # Admin connector management logic
│   └── vendor/
│       └── marked.min.js        # Vendored markdown parser
└── assets/
    ├── logo.svg                 # App logo
    └── default-avatar.png       # Default character avatar
```

## 4. Tests: `tests/`

```
tests/
├── conftest.py                  # Shared fixtures (test client, temp data dir, etc.)
├── test_character_service.py    # Character CRUD, import/export logic
├── test_conversation_service.py # Conversation persistence
├── test_chat_service.py         # Prompt building
├── test_connector_manager.py    # Connector manager lifecycle
├── test_openai_text.py          # OpenAI text connector (mocked HTTP)
├── test_openai_image.py         # OpenAI image connector (mocked HTTP)
├── test_api_characters.py       # Character API endpoints
├── test_api_chat.py             # Chat API endpoints
├── test_api_connectors.py       # Connector API endpoints
├── test_api_config.py           # Config API endpoints
├── test_png_metadata.py         # PNG metadata extraction
└── fixtures/                    # Test data files
    ├── sample_character.json    # Sample SillyTavern character card
    ├── sample_character.png     # Sample PNG with embedded metadata
    └── sample_connector.json    # Sample connector config
```

> **SillyTavern compatibility:** A dedicated unit test **must** verify that both SillyTavern V1 and V2 character cards are fully compatible and can be correctly parsed. Test fixtures (sample `.json` and `.png` character card files for both versions) will be provided in `tests/fixtures/`.

## 5. Data Directory: `data/`

See [`01-technology-stack.md`](01-technology-stack.md) § 2 "Directory Structure for Data" for the full layout.

```
data/
├── characters/                  # Character JSON files ({uuid}.json)
├── conversations/               # Conversation JSON files ({uuid}.json)
├── images/                      # Generated images ({session-token}/{uuid}.png)
│   └── {session-token}/
│       └── {uuid}.png
├── connectors/                  # Connector instance configs ({uuid}.json)
├── comfyui_workflows/           # ComfyUI workflow templates (post-MVP)
│   └── default_t2i.json        # Default text-to-image workflow
└── avatars/                     # Character avatar images ({uuid}.png)
```

The `data/` directory is created automatically on first startup if it doesn't exist. It is `.gitignore`d.

> **ComfyUI workflows (future):** User-customized workflow files are stored in `data/comfyui_workflows/` (gitignored). Default/shipped ComfyUI workflow templates will be stored at `aubergellm/resources/comfyui_workflows/` — as part of the Python package so they are installed with pip and can be copied to `data/comfyui_workflows/` on first use. See [POST-MVP roadmap](POST-MVP.md).

## 6. Configuration Files

| File | Purpose | Tracked in Git |
|---|---|---|
| `config.example.yaml` | Example config with all options documented | Yes |
| `config.yaml` | User's actual configuration (created by copying example) | No (`.gitignore`d) |
| `pyproject.toml` | Project metadata, ruff/mypy/pytest config | Yes |
| `requirements.txt` | Pinned Python dependencies | Yes |
| `.gitignore` | Ignore patterns | Yes |

## 7. Module Responsibilities

### `main.py`

- Creates the FastAPI app instance.
- Mounts all routers under `/api/`.
- Mounts the `frontend/` directory as static files at `/`.
- Runs startup logic (create data directories, load config).

### `config.py`

- Loads `config.yaml` from disk.
- Validates it using Pydantic models.
- Provides a singleton config object accessible throughout the app.

### `models/`

- Pure Pydantic models. No business logic.
- Used for API request/response validation and internal data passing.

### `connectors/`

- Connector implementations. Each backend is a separate file.
- All connectors inherit from base classes in `base.py`.
- `manager.py` handles connector lifecycle (create, configure, activate, test).
- Must not import from `routers/`.

### `services/`

- All business logic lives here.
- Services are stateless functions or classes that accept dependencies (config, file paths, connectors) explicitly.
- Services never import from `routers/`.

### `routers/`

- Thin layer. Receives HTTP requests, calls services, returns responses.
- No business logic in routers—only input parsing, service calls, and response formatting.
- Each router file is a `fastapi.APIRouter` instance.

### `utils/`

- Shared helper functions that don't belong to any specific service.
- Must not import from `services/` or `routers/`.

## 8. Import Rules

```
routers/ → services/ → models/
routers/ → connectors/
routers/ → models/
services/ → connectors/
services/ → utils/
services/ → models/
connectors/ → models/
connectors/ → utils/
routers/ → utils/
```

Circular imports are forbidden. The dependency graph is strictly:

```
routers → services → models
    ↓        ↓
connectors → utils
```

## 9. Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Python files | `snake_case.py` | `character_service.py` |
| Python classes | `PascalCase` | `CharacterCard` |
| Python functions | `snake_case` | `import_character()` |
| API routes | `kebab-case` or `snake_case` (consistent) | `/api/characters`, `/api/chat` |
| JS files | `camelCase.js` or `kebab-case.js` (consistent) | `chat.js`, `api.js` |
| JSON data files | `{uuid}.json` | `a1b2c3d4-....json` |
| Config keys | `snake_case` | `llm_base_url` |

## 10. Git Conventions

- Branch from `main` for each feature.
- Commit messages: `type: short description` (e.g., `feat: add character import endpoint`).
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- One logical change per commit.
