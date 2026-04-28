# aubergeRP

A lightweight, self-hostable roleplay engine. Connect any LLM (local or remote), import SillyTavern characters, and chat with inline AI image generation.

**Get running in under 10 minutes** → see [Installation Guide](docs/installation-guide.md).

## What it does

- **Roleplay chat** with any OpenAI-compatible LLM (Ollama, OpenRouter, vLLM, …).
- **SillyTavern-compatible** character cards (import/export JSON and PNG).
- **LLM-triggered image generation** — the model writes `[IMG: …]` markers; the backend calls the image connector automatically.
- **ComfyUI support** for local Stable Diffusion workflows (EARLY DRAFT, NOT TESTED YET).
- **Admin panel** — manage connectors, characters, and usage stats.
- **No build step** — vanilla HTML/JS frontend, Python/FastAPI backend, SQLite storage.

## Quick Start

```bash
git clone https://github.com/odoucet/aubergeRP.git
cd aubergeRP
cp config.example.yaml config.yaml
make docker
```

Open **http://localhost:8123** — the admin password is printed in the startup logs.

Then: 
 * go to Admin 
 * add a text connector (your LLM)
 * (optional) add an image connector
 * (optional) import a character (or use one of the bundled examples)
 * Chat !

See [docs/installation-guide.md](docs/installation-guide.md) for the local GPU stack (`make docker gpu=rtx3090`) and other options.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
make run      # dev server with hot-reload at http://localhost:8123
make test     # run test suite
make lint     # ruff + mypy
make doc      # regenerate docs/03-backend-api.md from source
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full contribution guidelines.

## Documentation

| Document | Description |
|---|---|
| [Installation Guide](docs/installation-guide.md) | Docker, GPU stack, troubleshooting |
| [Architecture](docs/00-architecture-overview.md) | High-level design decisions |
| [Configuration](docs/09-configuration-and-setup.md) | `config.yaml` reference |
| [Connector System](docs/06-connector-system.md) | How to add a new backend |
| [API Reference](docs/03-backend-api.md) | REST/SSE endpoints (run `make doc` to regenerate) |

## License

Apache 2.0
