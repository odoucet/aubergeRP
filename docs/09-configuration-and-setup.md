# 09 — Configuration

This document specifies the configuration file, the ancillary project files (`.gitignore`, `requirements.txt`, `pyproject.toml`), and the startup sequence. Installation / setup instructions are intentionally not part of the MVP documentation.

## 1. Configuration File

### `config.example.yaml`

```yaml
# aubergeRP Configuration
# Copy this file to config.yaml. All settings can be changed via the Admin UI.

app:
  # Host and port for the aubergeRP server
  host: "0.0.0.0"
  port: 8000
  # Log level: DEBUG, INFO, WARNING, ERROR
  log_level: "INFO"
  # Data directory (relative to project root or absolute path)
  data_dir: "data"

# Active connector IDs. The Admin UI writes these.
# Leave empty on first start.
active_connectors:
  text: ""
  image: ""
  # video: ""   # post-MVP
  # audio: ""   # post-MVP

user:
  # Display name for the user in chat (used for {{user}} macro)
  name: "User"
```

### Schema

| Key | Type | Default | Description |
|---|---|---|---|
| `app.host` | string | `"0.0.0.0"` | Bind host |
| `app.port` | integer | `8000` | Bind port |
| `app.log_level` | string | `"INFO"` | One of DEBUG, INFO, WARNING, ERROR |
| `app.data_dir` | string | `"data"` | Path (relative or absolute) to the runtime data directory |
| `active_connectors.text` | string (UUID or `""`) | `""` | Active text connector ID |
| `active_connectors.image` | string (UUID or `""`) | `""` | Active image connector ID |
| `user.name` | string | `"User"` | Display name substituted for `{{user}}` macro |

No environment-variable overrides in the MVP. All configuration is in `config.yaml`, which the Admin UI writes.

## 2. Configuration Loading

1. On startup, load defaults (from the Pydantic models).
2. If `config.yaml` exists, overlay its values.
3. Validate with Pydantic.
4. Expose as a module-level singleton.

## 3. Data Directory Initialization

On startup, the backend ensures every required subdirectory exists under `app.data_dir`:

- `characters/`
- `conversations/`
- `connectors/`
- `avatars/`
- `images/{SESSION_TOKEN}/` — where `SESSION_TOKEN` is the constant `00000000-0000-0000-0000-000000000000` (see [00 § 9](00-architecture-overview.md)).

Missing directories are created with `mkdir -p` semantics. The parent `data/` directory is created if missing.

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
Pillow>=10.0,<12.0
python-multipart>=0.0.9,<1.0
pyyaml>=6.0,<7.0
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

1. Load configuration from `config.yaml` (defaults applied where missing).
2. Initialize the data directory structure (§ 3).
3. Create the FastAPI app (title, version, description).
4. Load connectors from `data/connectors/` and initialize the ConnectorManager; active connectors are read from `config.yaml:active_connectors`.
5. Mount all routers under `/api/`.
6. Mount `frontend/` as static files at `/`.
7. Log startup info (listening address, active connectors, data directory).

No tokens are generated or logged. No auth middleware is installed.
