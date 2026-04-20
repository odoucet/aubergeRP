# 09 — Configuration and Setup

## 1. Overview

This document specifies how AubergeLLM is configured, installed, and started. The guiding principle is **time-to-first-roleplay < 1 hour**, so the setup process must be as streamlined as possible.

## 2. Prerequisites

| Requirement | Minimum | Notes |
|---|---|---|
| Python | 3.10+ | Required for the backend |
| pip | Latest | Comes with Python |
| LLM backend | Any OpenAI-compatible API | Ollama recommended for local use |
| Image API | Any OpenAI-compatible image API | OpenRouter recommended for easy setup |
| ComfyUI | Any recent version | Optional, post-MVP (advanced image generation) |
| GPU | NVIDIA recommended | For local LLM; not needed if using remote APIs |
| OS | Linux, macOS, Windows | All supported |

## 3. Installation Steps

### 3.1 Clone and Setup

```bash
# Clone the repository
git clone https://github.com/odoucet/aubergellm.git
cd aubergellm

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3.2 Configuration

```bash
# Copy the example config
cp config.example.yaml config.yaml

# Edit the config (optional — can also be configured via Admin UI)
# nano config.yaml  (or any text editor)
```

### 3.3 Start the Server

```bash
# Start AubergeLLM
python -m uvicorn aubergellm.main:app --host 0.0.0.0 --port 8000

# Or use the convenience script (if provided)
python run.py
```

The application is now accessible at `http://localhost:8000`.

### 3.4 First-Time Configuration via Admin UI

1. Open `http://localhost:8000/admin/` in a browser.
2. Add a **text connector** (e.g., OpenAI-compatible API pointing to Ollama at `http://localhost:11434/v1`).
3. Test the connection.
4. Add an **image connector** (e.g., OpenAI-compatible API pointing to OpenRouter at `https://openrouter.ai/api/v1`).
5. Test the connection.
6. Import at least one character.
7. Navigate to the Chat UI and start roleplaying.

## 4. Configuration File

### `config.example.yaml`

```yaml
# AubergeLLM Configuration
# Copy this file to config.yaml and edit as needed.
# All settings can also be changed via the Admin UI.

app:
  # Host and port for the AubergeLLM server
  host: "0.0.0.0"
  port: 8000
  # Log level: DEBUG, INFO, WARNING, ERROR
  log_level: "INFO"
  # Data directory (relative to project root or absolute path)
  data_dir: "data"

# Active connector IDs (set via Admin UI or here)
# Leave empty to configure via Admin UI on first start
active_connectors:
  text: ""    # UUID of the active text connector
  image: ""   # UUID of the active image connector
  # video: ""  # Post-MVP
  # audio: ""  # Post-MVP

user:
  # Display name for the user in chat (used for {{user}} macro)
  name: "User"
```

### Configuration Model (Pydantic)

```python
class AppConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    data_dir: str = "data"

class ActiveConnectorsConfig(BaseModel):
    text: str = ""   # UUID of active text connector
    image: str = ""  # UUID of active image connector

class UserConfig(BaseModel):
    name: str = "User"

class Config(BaseModel):
    app: AppConfig = AppConfig()
    active_connectors: ActiveConnectorsConfig = ActiveConnectorsConfig()
    user: UserConfig = UserConfig()
```

## 5. Configuration Loading

### Priority Order (highest to lowest)

1. **Admin UI changes** — saved to `config.yaml` in real-time.
2. **`config.yaml`** — primary configuration file.
3. **Environment variables** — override config file values (prefixed with `AUBERGELLM_`).
4. **Default values** — built into the Pydantic models.

### Environment Variable Mapping

| Environment Variable | Config Path | Example |
|---|---|---|
| `AUBERGELLM_APP_PORT` | `app.port` | `9000` |
| `AUBERGELLM_APP_LOG_LEVEL` | `app.log_level` | `DEBUG` |
| `AUBERGELLM_USER_NAME` | `user.name` | `Alice` |

### Config Loading Logic

```
1. Load default Config() with all defaults.
2. If config.yaml exists, read it and overlay values.
3. Check for AUBERGELLM_* environment variables and overlay.
4. Validate the final config with Pydantic.
5. Store as a module-level singleton.
```

## 6. Data Directory Initialization

On startup, the backend ensures the data directory structure exists:

```python
def initialize_data_dir(data_dir: str):
    """Create data directory structure if it doesn't exist."""
    for subdir in ["characters", "conversations", "images", "connectors", "workflows", "avatars"]:
        Path(data_dir, subdir).mkdir(parents=True, exist_ok=True)
```

If the `data/workflows/` directory is empty, copy the default workflow files from the package.

## 7. `run.py` Convenience Script

A simple script at the project root for easy startup:

```python
#!/usr/bin/env python
"""AubergeLLM launcher."""
import uvicorn
from aubergellm.config import load_config

config = load_config()
uvicorn.run(
    "aubergellm.main:app",
    host=config.app.host,
    port=config.app.port,
    log_level=config.app.log_level.lower(),
)
```

## 8. `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
venv/
.venv/
*.egg-info/
dist/
build/

# Configuration (user-specific)
config.yaml

# Data (user-specific)
data/characters/
data/conversations/
data/images/
data/connectors/
data/avatars/

# Keep workflow templates
!data/workflows/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

## 9. `requirements.txt`

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

## 10. `pyproject.toml`

```toml
[project]
name = "aubergellm"
version = "0.1.0"
description = "A lightweight roleplay frontend with LLM and ComfyUI integration"
requires-python = ">=3.10"
license = "Apache-2.0"

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.mypy]
python_version = "3.10"
strict = true
```

## 11. Startup Sequence

When `main.py` runs, the following happens:

1. **Load configuration** from `config.yaml` + environment variables.
2. **Initialize data directory** (create missing directories, including `connectors/`).
3. **Load connectors** from `data/connectors/` and activate the configured ones.
4. **Create FastAPI app** with metadata (title, version, description).
5. **Mount routers** under `/api/`.
6. **Mount static files** (serve `frontend/` at `/`).
7. **Log startup info** (listening address, active connectors, data directory path).

## 12. Quick Start Guide (README-ready)

This section can be used as the basis for a quick start section in the README:

```markdown
## Quick Start

### Prerequisites
- Python 3.10+
- An LLM backend (e.g., [Ollama](https://ollama.com)) for text generation
- (Optional) An image API key (e.g., [OpenRouter](https://openrouter.ai)) for image generation

### Installation
git clone https://github.com/odoucet/aubergellm.git
cd aubergellm
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml

### Run
python run.py

### Configure
1. Open http://localhost:8000/admin/
2. Add a text connector (e.g., Ollama at http://localhost:11434/v1)
3. (Optional) Add an image connector (e.g., OpenRouter)
4. Import a character card (SillyTavern-compatible JSON or PNG)
5. Go to http://localhost:8000 and start chatting!
```
