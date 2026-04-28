# aubergeRP

aubergeRP is a lightweight, self-hostable roleplay engine that combines large language models (LLMs) with multimodal generation (image, video, audio) through a **pluggable connector system**.

The goal is to provide a clean, minimal, and extensible alternative to tools like SillyTavern, while enabling advanced workflows such as:

* Roleplay chat with SillyTavern-compatible character cards.
* Image generation during roleplay, triggered automatically by the LLM.
* Character-consistent visuals.
* ComfyUI support for local Stable Diffusion workflows.

## Architecture — Connector System

aubergeRP uses a **connector-based architecture** where every external generation backend is a pluggable module. Each connector handles a specific modality:

| Connector Type | Description | Available Backends |
|---|---|---|
| **Text** | Chat completions / LLM | OpenAI-compatible API (Ollama, OpenRouter, OpenAI, vLLM, …) |
| **Image** | Image generation | OpenAI-compatible API (OpenRouter → Gemini/DALL-E/Flux, OpenAI, …), ComfyUI |
| **Video** | Video generation | Not yet implemented |
| **Audio** | TTS / audio generation | Not yet implemented |

Adding a new backend = implementing a new connector class. The rest of the app does not change.

```
[ Frontend UI ]
        ↓
[ aubergeRP API (FastAPI) ]
        ↓
[ Connector Manager ]
   ↓              ↓
[ Text           [ Image
  Connector ]      Connector ]
   ↓              ↓
[ LLM Backend ]  [ Image API / ComfyUI ]
```

## Key Features

### LLM-Driven Roleplay
* Local or remote LLM support via text connectors (Ollama, OpenAI-compatible APIs).
* SillyTavern-compatible character cards (import/export JSON and PNG).
* Automatic conversation summarization when approaching context-window limits.
* OOC (out-of-character) protection guardrails.

### Multimodal Generation
* Image generation via image connectors (OpenRouter, OpenAI, ComfyUI, …).
* Images are triggered **by the LLM itself** using an inline marker in its response (see [docs/05-chat-and-conversations.md](docs/05-chat-and-conversations.md)).

### Connector System
* Pluggable backends per modality (text, image).
* One active connector per type at a time.
* Add, configure, test, and switch connectors from the Admin UI.

### Modular Architecture
* Frontend: static HTML + vanilla JS, no build step.
* Backend: Python / FastAPI.
* SQLite storage via SQLModel (automatic migrations).
* All external backends accessed through connectors only.

### Deployment
* **Local GPU stack** — single `make docker <profile>` command provisions Ollama + aubergeRP, downloads GGUF models, and registers them.
* Docker and docker-compose support (hardware profiles for RTX 3090, …).
* Environment-variable config overrides.
* Optional Sentry error tracking.
* Background media cleanup scheduler.

### Admin & Customization
* Character marketplace browser (import community cards).
* GUI customization (custom CSS, header/footer HTML).
* Plugin system for third-party extensions.
* Interactive API reference at `/api-docs`.
* **Admin authentication** — password-protected admin panel; password is generated on first startup and logged to the console.

## Quick Start — Local GPU Stack

```bash
# Install the HuggingFace hf CLI (one-time)
pip install 'huggingface_hub[cli]'

# Start the stack for an RTX 3090
# Downloads models automatically if missing, then starts Ollama + aubergeRP
make docker rtx3090

# Other commands
make stop           # stop containers
make clean          # stop + remove containers and networks
make logs           # tail logs
```

See [docs/installation-guide.md](docs/installation-guide.md) for prerequisites, available profiles, and how to add your own GPU profile.

## Documentation

Full specifications live in [`docs/`](docs/):

| Document | Description |
|---|---|
| [00 — Architecture Overview](docs/00-architecture-overview.md) | High-level architecture, components, scope |
| [01 — Technology Stack](docs/01-technology-stack.md) | Technology choices |
| [02 — Project Structure](docs/02-project-structure.md) | Directory layout, module organization |
| [03 — Backend API](docs/03-backend-api.md) | REST/SSE API specification |
| [04 — Character System](docs/04-character-system.md) | Character card format, SillyTavern compatibility |
| [05 — Chat and Conversations](docs/05-chat-and-conversations.md) | Chat flow, image-trigger marker, prompt construction |
| [06 — Connector System](docs/06-connector-system.md) | Connector architecture, interfaces, implementations |
| [07 — Frontend Chat UI](docs/07-frontend-chat-ui.md) | Chat interface specification |
| [08 — Admin Interface](docs/08-admin-interface.md) | Admin panel for connectors and characters |
| [09 — Configuration](docs/09-configuration-and-setup.md) | Config file, startup sequence, project files |
| [Installation Guide](docs/installation-guide.md) | Step-by-step setup for Linux, macOS, Windows, Docker |
| [POST-MVP](docs/POST-MVP.md) | Features not yet implemented |

## Disclaimer

aubergeRP is an experimental project. Contributions are welcome; please be patient with reviews.

## License

Apache 2.0
