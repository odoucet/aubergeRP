# aubergeRP

aubergeRP is a lightweight, self-hostable roleplay engine that combines large language models (LLMs) with multimodal generation (image, video, audio) through a **pluggable connector system**.

The goal is to provide a clean, minimal, and extensible alternative to tools like SillyTavern, while enabling advanced workflows such as:

* Roleplay chat with SillyTavern-compatible character cards.
* Image generation during roleplay, triggered automatically by the LLM.
* Character-consistent visuals.
* Future support for ComfyUI workflows, video, and audio generation.

## Architecture — Connector System

aubergeRP uses a **connector-based architecture** where every external generation backend is a pluggable module. Each connector handles a specific modality:

| Connector Type | Description | MVP Backend |
|---|---|---|
| **Text** | Chat completions / LLM | OpenAI-compatible API (Ollama, OpenRouter, OpenAI, vLLM, …) |
| **Image** | Image generation | OpenAI-compatible API (OpenRouter → Gemini/DALL-E/Flux, OpenAI, …) |
| **Video** | Video generation | Post-MVP |
| **Audio** | TTS / audio generation | Post-MVP |

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
[ LLM Backend ]  [ Image API ]
```

## Key Features

### LLM-Driven Roleplay
* Local or remote LLM support via text connectors (Ollama, OpenAI-compatible APIs).
* SillyTavern-compatible character cards (import/export JSON and PNG).

### Multimodal Generation
* Image generation via image connectors (OpenRouter, OpenAI, …).
* Images are triggered **by the LLM itself** using an inline marker in its response (see [docs/05-chat-and-conversations.md](docs/05-chat-and-conversations.md)).

### Connector System
* Pluggable backends per modality (text, image, video, audio).
* One active connector per type at a time.
* Add, configure, test, and switch connectors from the Admin UI.

### Modular Architecture
* Frontend: static HTML + vanilla JS, no build step.
* Backend: Python / FastAPI.
* All external backends accessed through connectors only.

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
| [POST-MVP](docs/POST-MVP.md) | Features out of scope for the MVP |

## Disclaimer

aubergeRP is an experimental project. Contributions are welcome; please be patient with reviews.

## License

Apache 2.0
