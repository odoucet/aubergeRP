# 09 — Configuration

This document specifies the configuration file, the ancillary project files (`.gitignore`, `requirements.txt`, `pyproject.toml`), and the startup sequence.

## 1. Configuration File

### `config.example.yaml`

```yaml
# aubergeRP Configuration
# Copy this file to config.yaml. All settings can be changed via the Admin UI.

app:
  # Host and port for the aubergeRP server
  host: "0.0.0.0"
  port: 8123
  # Log level: DEBUG, INFO, WARNING, ERROR
  log_level: "INFO"
  # Data directory (relative to project root or absolute path)
  data_dir: "data"
  # Optional Sentry DSN for error tracking. Leave empty to disable.
  # sentry_dsn: ""

# Environment-variable overrides (take precedence over this file):
#   AUBERGE_DATA_DIR    → app.data_dir
#   AUBERGE_HOST        → app.host
#   AUBERGE_PORT        → app.port
#   AUBERGE_LOG_LEVEL   → app.log_level
#   AUBERGE_USER_NAME   → user.name
#   AUBERGE_SENTRY_DSN  → app.sentry_dsn

# Active connector IDs. The Admin UI writes these.
# Leave empty on first start.
active_connectors:
  text: ""
  image: ""

user:
  # Display name for the user in chat (used for {{user}} macro)
  name: "User"

# Background media-cleanup scheduler (default: disabled)
scheduler:
  enabled: false
  # How often to run cleanup (seconds). Default: 24 hours.
  interval_seconds: 86400
  # Delete images older than this many days.
  cleanup_older_than_days: 30

# AI quality settings
chat:
  # Estimated context window of the active text model (tokens).
  context_window: 4096
  # Summarise conversation history when this fraction of the context is used.
  summarization_threshold: 0.75
  # Enable out-of-character (OOC) protection guardrails.
  ooc_protection: true

# GUI customization (injected into every page)
gui:
  custom_css: ""
  custom_header_html: ""
  custom_footer_html: ""

# Character marketplace
marketplace:
  index_url: "https://raw.githubusercontent.com/odoucet/aubergeRP/main/marketplace/index.json"
```

### Schema

| Key | Type | Default | Description |
|---|---|---|---|
| `app.host` | string | `"0.0.0.0"` | Bind host |
| `app.port` | integer | `8123` | Bind port |
| `app.log_level` | string | `"INFO"` | One of DEBUG, INFO, WARNING, ERROR |
| `app.data_dir` | string | `"data"` | Path (relative or absolute) to the runtime data directory |
| `app.sentry_dsn` | string | `""` | Sentry DSN (empty = disabled) |
| `active_connectors.text` | string (UUID or `""`) | `""` | Active text connector ID |
| `active_connectors.image` | string (UUID or `""`) | `""` | Active image connector ID |
| `user.name` | string | `"User"` | Display name substituted for `{{user}}` macro |
| `scheduler.enabled` | bool | `false` | Enable background media-cleanup scheduler |
| `scheduler.interval_seconds` | integer | `86400` | Cleanup interval in seconds |
| `scheduler.cleanup_older_than_days` | integer | `30` | Delete images older than N days |
| `chat.context_window` | integer | `4096` | Estimated model context window in tokens |
| `chat.summarization_threshold` | float | `0.75` | Summarize when this fraction of context is used |
| `chat.ooc_protection` | bool | `true` | Enable OOC guardrail injection |
| `gui.custom_css` | string | `""` | CSS injected in a `<style>` tag on every page |
| `gui.custom_header_html` | string | `""` | HTML injected at the top of every page body |
| `gui.custom_footer_html` | string | `""` | HTML injected at the bottom of every page body |
| `marketplace.index_url` | string | (GitHub URL) | URL of the marketplace card index (http/https only) |

### Environment-Variable Overrides

Environment variables override the corresponding `config.yaml` values at startup:

| Variable | Config field |
|---|---|
| `AUBERGE_DATA_DIR` | `app.data_dir` |
| `AUBERGE_HOST` | `app.host` |
| `AUBERGE_PORT` | `app.port` |
| `AUBERGE_LOG_LEVEL` | `app.log_level` |
| `AUBERGE_USER_NAME` | `user.name` |
| `AUBERGE_SENTRY_DSN` | `app.sentry_dsn` |
| `AUBERGE_ADMIN_PASSWORD_HASH` | `app.admin_password_hash` |

## 2. Configuration Loading

1. On startup, load defaults (from the Pydantic models).
2. If `config.yaml` exists, overlay its values.
3. Validate with Pydantic.
4. Expose as a module-level singleton.

## 3. Data Directory Initialization

On startup, the backend ensures every required subdirectory exists under `app.data_dir`:

- `connectors/`
- `avatars/`
- `images/`
- `comfyui_workflows/` (seeded from built-in templates on first run)

Missing directories are created with `mkdir -p` semantics. The parent `data/` directory is created if missing. The SQLite database file (`data/auberge.db`) is created automatically by `init_db()`.

## 4. `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
venv/
.venv/
*.egg-info/
dist/
build/

# User configuration
config.yaml

# Runtime data (user-specific)
data/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

## 5. `requirements.txt`

```
fastapi>=0.111,<1.0
uvicorn[standard]>=0.30,<1.0
httpx>=0.27,<1.0
pydantic>=2.0,<3.0
sse-starlette>=2.0,<3.0
Pillow>=12.2.0,<13.0
python-multipart>=0.0.9,<1.0
pyyaml>=6.0,<7.0
sqlmodel>=0.0.18,<1.0
aiofiles>=23.0,<25.0
websockets>=12.0,<14.0
sentry-sdk[fastapi]>=2.0,<3.0
pytest>=9.0.3,<10.0
pytest-asyncio>=1.0,<2.0
ruff>=0.4,<1.0
mypy>=1.10,<2.0
respx
```

## 6. `pyproject.toml`

```toml
[project]
name = "aubergeRP"
version = "0.1.0"
description = "A lightweight roleplay frontend with pluggable connectors for LLM and image generation"
requires-python = ">=3.12"
license = "Apache-2.0"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.mypy]
python_version = "3.12"
strict = true
```

## 7. Startup Sequence

When `main.py` runs:

1. Load configuration from `config.yaml` (defaults applied where missing; environment-variable overrides applied).
2. Initialize Sentry if `app.sentry_dsn` is configured.
3. Initialize the data directory structure (§ 3).
4. Initialize the admin password (generate if missing and log to console).
5. Initialize SQLite database (`data/auberge.db`) and run pending migrations.
6. Create the FastAPI app (title, version, description).
7. Apply CORS auto-detection middleware.
8. Load connectors from `data/connectors/` and initialize the ConnectorManager; active connectors are read from `config.yaml:active_connectors`.
9. Mount all routers under `/api/`.
10. Mount `frontend/` as static files at `/`.
11. Mount Redoc API reference at `/api-docs`.
12. Start the background scheduler (if `scheduler.enabled`).
13. Log startup info (listening address, active connectors, data directory).
**Admin authentication:** The admin password is initialized on step 4. If the password hash does not exist in the config or environment, a new random password is generated and logged to the console. All admin API routes require the `X-Admin-Token` header for write operations (POST, PUT, DELETE, PATCH).
