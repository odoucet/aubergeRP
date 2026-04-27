# aubergeRP — Installation Guide

This guide explains how to install and run aubergeRP on Linux, macOS, and Windows, as well as via Docker.

---

## Prerequisites

| Requirement | Minimum version |
|-------------|-----------------|
| Python      | 3.12            |
| pip         | 23+             |
| Git         | Any recent      |

---

## 1. Quick Start (all platforms)

### 1a. Clone the repository

```bash
git clone https://github.com/odoucet/aubergeRP.git
cd aubergeRP
```

### 1b. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

| Platform | Command |
|----------|---------|
| Linux / macOS | `source .venv/bin/activate` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |

### 1c. Install dependencies

```bash
pip install -r requirements.txt
```

### 1d. Create a config file (optional)

```bash
cp config.example.yaml config.yaml
# Edit config.yaml to match your setup
```

### 1e. Start the server

```bash
python -m uvicorn aubergeRP.main:app --host 0.0.0.0 --port 8123
```

Open your browser at **http://localhost:8123**.

---

## 2. Linux

The quick-start steps above work on any modern Linux distribution.

### Systemd service (optional)

Create `/etc/systemd/system/aubergerp.service`:

```ini
[Unit]
Description=aubergeRP server
After=network.target

[Service]
Type=simple
User=aubergerp
WorkingDirectory=/opt/aubergeRP
ExecStart=/opt/aubergeRP/.venv/bin/uvicorn aubergeRP.main:app --host 0.0.0.0 --port 8123
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aubergerp
```

---

## 3. macOS

The quick-start steps above work on macOS (Intel and Apple Silicon).

### Homebrew Python (recommended)

```bash
brew install python@3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### launchd service (optional)

Create `~/Library/LaunchAgents/com.aubergerp.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.aubergerp</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/YOU/aubergeRP/.venv/bin/uvicorn</string>
    <string>aubergeRP.main:app</string>
    <string>--host</string><string>0.0.0.0</string>
    <string>--port</string><string>8123</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/YOU/aubergeRP</string>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.aubergerp.plist
```

---

## 4. Windows

### Step-by-step

1. Download and install Python 3.12+ from https://www.python.org/downloads/  
   ✅ Make sure to check **"Add Python to PATH"** during installation.

2. Open **PowerShell** (or cmd) and navigate to the project:

   ```powershell
   cd C:\aubergeRP
   ```

3. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   > If you get an execution-policy error, run:  
   > `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

4. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

5. Start the server:

   ```powershell
   python -m uvicorn aubergeRP.main:app --host 0.0.0.0 --port 8123
   ```

6. Open **http://localhost:8123** in your browser.

### Running as a Windows Service (optional)

Use [NSSM](https://nssm.cc/) to wrap uvicorn as a Windows service:

```bat
nssm install aubergeRP "C:\aubergeRP\.venv\Scripts\uvicorn.exe" "aubergeRP.main:app --host 0.0.0.0 --port 8123"
nssm set aubergeRP AppDirectory C:\aubergeRP
nssm start aubergeRP
```

---

## 5. Docker

Two usage modes are available:

| Mode | When to use |
|------|-------------|
| **Managed stack** (`make docker <profile>`) | Local GPU, Ollama bundled, models auto-downloaded |
| **Bare compose** (`docker compose up`) | Custom infra, remote LLM, CI |

---

### 5a. Managed stack (GPU + Ollama)

The Makefile wraps docker compose with hardware profiles. It downloads missing GGUF
models via `huggingface-cli`, starts the containers, and registers the models in Ollama
— all in one command.

#### Prerequisites

| Requirement | Version |
|-------------|---------|
| Docker + Docker Compose v2 | 24+ |
| NVIDIA Container Toolkit | For GPU profiles |
| Python + hf CLI | `pip install 'huggingface_hub[cli]'` |
| `make` | Any GNU make |

#### Commands

```bash
make docker rtx3090    # start stack with RTX 3090 profile
make stop              # stop containers (data preserved)
make clean             # stop + remove containers and networks
make logs              # tail all container logs
```

Listing or requesting an undefined profile shows a clear error:

```
Error: Profile 'idonotexist' does not exist.
Profiles: rtx3090
```

#### How it works

1. **Model download** — checks `data/models/` for each required `.gguf` file; downloads from HuggingFace if missing.
2. **Stack start** — merges `docker/docker-compose.yml` with `docker/profiles/<profile>.yml` and runs `docker compose up -d`.
3. **Model registration** — waits for Ollama to become ready, then runs `ollama create <name> -f /modelfiles/<file>` for each model (skipped if already loaded).

#### Available profiles

| Profile | GPU | LLM | Image model |
|---------|-----|-----|-------------|
| `rtx3090` | NVIDIA RTX 3090 (24 GB) | GLM-4.7-Flash Q4\_0 (~17.2 GB) | FLUX.2-klein 9B Q4\_K\_M (~5.91 GB) |

#### Adding a new profile

1. Create `docker/profiles/<name>.yml` — override GPU reservations and `LLM_MODEL` / `IMAGE_MODEL` env vars.
2. Add the GGUF specs and a `_setup-<name>` target in the `Makefile` (follow the `_setup-rtx3090` block as a template).
3. Create the corresponding `docker/modelfiles/<name>.Modelfile` files.

---

### 5b. Bare compose

```bash
git clone https://github.com/odoucet/aubergeRP.git
cd aubergeRP
cp config.example.yaml config.yaml
docker compose up -d
```

The server will be available at **http://localhost:8123**.

---

### Environment variables

All configuration values can be overridden via environment variables without editing `config.yaml`:

| Variable | Config field |
|----------|-------------|
| `AUBERGE_DATA_DIR` | `app.data_dir` |
| `AUBERGE_HOST` | `app.host` |
| `AUBERGE_PORT` | `app.port` |
| `AUBERGE_LOG_LEVEL` | `app.log_level` |
| `AUBERGE_USER_NAME` | `user.name` |
| `AUBERGE_SENTRY_DSN` | `app.sentry_dsn` |

Example override in a compose profile:

```yaml
environment:
  AUBERGE_LOG_LEVEL: DEBUG
  AUBERGE_SENTRY_DSN: "https://xxx@sentry.io/123"
```

---

## 6. Verifying the installation

Open the **Admin** panel at **http://localhost:8123/admin/** and check:

- **Health** tab → all services report their status.
- **API Reference** at **http://localhost:8123/api-docs** → interactive Redoc UI.
- **OpenAPI spec** at **http://localhost:8123/openapi.json** → machine-readable schema.

---

## 7. Updating

```bash
git pull
pip install -r requirements.txt
# Restart the server
```

Database migrations run automatically on startup.

---

## 8. Troubleshooting

| Symptom | Solution |
|---------|----------|
| `ModuleNotFoundError` | Make sure the virtual environment is activated and `pip install -r requirements.txt` completed successfully. |
| Port already in use | Change the port with `--port 8001` or set `AUBERGE_PORT=8001`. |
| Cannot reach from another machine | Bind to `0.0.0.0` (default) and check your firewall. |
| Database locked | Only one process should run at a time against the same `data/` directory. |
