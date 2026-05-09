# aubergeRP — Installation Guide

This guide is intentionally short.

The recommended setup is Docker-first on Linux, macOS, and Windows using `docker compose`:

- Use `make docker` if you want the fastest path and plan to connect aubergeRP to remote APIs such as OpenRouter, OpenAI, or another OpenAI-compatible backend.
- Use `make docker gpu=rtx3090` if you want the local GPU stack with preconfigured models.

Everything else has been removed on purpose. The goal is to get you to a working app with the fewest possible steps.

---

## Option 1 — Quick Start With Remote APIs

Use this if you want the easiest setup.

### Requirements

- Docker with Compose v2
- Git

### Steps

```bash
git clone https://github.com/aubergeRP/aubergeRP.git
cd aubergeRP
cp config.example.yaml config.yaml
make docker
```

Then open:

- App: **http://localhost:8123**
- Admin: **http://localhost:8123/admin/**

On first startup, aubergeRP generates an admin password and prints it in the container logs.

After that:

1. Open the Admin panel.
2. Add your text connector for OpenRouter, OpenAI, Ollama, vLLM, or any OpenAI-compatible API.
3. Optionally add an image connector.
4. Set the connector as active.
5. Start chatting.

Useful commands:

```bash
make logs
make stop
make clean
```

### Notes

- This path starts `auberge-app` only (no bundled LocalAI container).
- `config.yaml` only needs to exist. Most connector setup can be done from the Admin UI.
- Your data stays in the repository `data/` directory.

---

## Option 2 — Local GPU Stack

Use this if you want aubergeRP plus local models on your own GPU.

### Requirements

- Docker with Compose v2
- GNU `make`
- NVIDIA Container Toolkit

### Steps

```bash
git clone https://github.com/aubergeRP/aubergeRP.git
cd aubergeRP
cp config.example.yaml config.yaml
make docker gpu=rtx3090
```

What this does:

- starts LocalAI and auberge-app
- installs the models via the LocalAI gallery API (models download in the background on first run)

Then open:

- App: **http://localhost:8123**
- Admin: **http://localhost:8123/admin/**

If you need to retrieve the generated admin password after startup:

```bash
make logs gpu=rtx3090
```

### Available Profile

Currently included in this repository:

- `rtx3090`

### Useful Commands

```bash
make logs gpu=rtx3090
make stop gpu=rtx3090
make clean gpu=rtx3090
```

---

## Which Option Should You Choose?

- Choose `make docker` if you want the fastest setup and expect to use remote APIs.
- Choose `make docker gpu=rtx3090` if you want a local GPU-backed stack with models prepared for you.

If you are unsure, start with `make docker`.

---

## Verification

After startup, check these URLs:

- **http://localhost:8123**
- **http://localhost:8123/admin/**
- **http://localhost:8123/api-docs**

If those pages load, the installation is working.

---

## Troubleshooting

| Problem | What to do |
|---|---|
| `config.yaml` missing | Run `cp config.example.yaml config.yaml` |
| Port `8123` already in use | Start with `AUBERGE_PORT=8001 make docker` |
| GPU profile fails to start | Check Docker GPU support and NVIDIA Container Toolkit installation |
| You missed the admin password in logs | Run `make logs` (or `make logs gpu=rtx3090` for the GPU stack) |

Database migrations run automatically at startup.
