# AubergeLLM

AubergeLLM is a lightweight, self-hostable roleplay engine that combines large language models (LLMs) with multimodal generation (image, video, audio) through a **pluggable connector system**.

The goal of AubergeLLM is to provide a clean, minimal, and extensible alternative to tools like SillyTavern, while enabling advanced workflows such as:

* Roleplay chat with SillyTavern-compatible character cards
* Image generation during roleplay via API connectors (OpenRouter, OpenAI, etc.)
* Character-consistent visuals
* Future support for ComfyUI workflows, video, and audio generation

## Architecture — Connector System

AubergeLLM uses a **connector-based architecture** where all external generation backends are pluggable modules. Each connector handles a specific modality:

| Connector Type | Description | MVP Backend |
|---|---|---|
| **Text** | Chat completions / LLM | OpenAI-compatible API (Ollama, OpenRouter, OpenAI, vLLM, etc.) |
| **Image** | Image generation | OpenAI-compatible API (OpenRouter → Gemini/DALL-E/Flux, OpenAI, etc.) |
| **Video** | Video generation | Post-MVP |
| **Audio** | TTS / audio generation | Post-MVP |

This means:
- Adding a new backend = implementing a new connector (no core changes needed)
- Whether the image comes from an API call or a ComfyUI workflow is transparent to the rest of the app
- The MVP uses the simplest possible connectors (OpenAI-compatible APIs) for instant setup

```
[ Frontend UI ]
        ↓
[ AubergeLLM API (FastAPI) ]
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
* Local or remote LLM support via text connectors (Ollama, OpenAI-compatible APIs)
* Structured prompting and system instructions
* SillyTavern-compatible character cards (import/export JSON and PNG)

### Multimodal Generation
* Image generation via image connectors (OpenRouter, OpenAI, etc.)
* Future: ComfyUI connector for local Stable Diffusion workflows
* Future: Video and audio connectors

### Connector System
* Pluggable backends for each modality (text, image, video, audio)
* One active connector per type at a time
* Add, configure, test, and switch connectors via Admin UI
* Easy to extend: implement a new connector class to add a new backend

### Modular Architecture
* Frontend (chat / RP UI) — static HTML + vanilla JS
* Backend (API + connector management) — Python / FastAPI
* External backends accessed only through connectors

## Quick Start

### Prerequisites
- Python 3.10+
- An LLM backend (e.g., [Ollama](https://ollama.com)) for text generation
- (Optional) An image API key (e.g., [OpenRouter](https://openrouter.ai)) for image generation

### Installation

```bash
git clone https://github.com/odoucet/aubergellm.git
cd aubergellm
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

### Run

```bash
python run.py
```

### Configure

1. Open `http://localhost:8000/admin/`
2. Add a **text connector** (e.g., Ollama at `http://localhost:11434/v1`)
3. (Optional) Add an **image connector** (e.g., OpenRouter at `https://openrouter.ai/api/v1`)
4. Import a character card (SillyTavern-compatible JSON or PNG)
5. Go to `http://localhost:8000` and start chatting!

## Documentation

Full specifications are in the [`docs/`](docs/) directory:

| Document | Description |
|---|---|
| [00 — Architecture Overview](docs/00-architecture-overview.md) | High-level architecture, components, communication patterns |
| [01 — Technology Stack](docs/01-technology-stack.md) | Technology choices and justifications |
| [02 — Project Structure](docs/02-project-structure.md) | Directory layout, module organization |
| [03 — Backend API](docs/03-backend-api.md) | REST/SSE API specification |
| [04 — Character System](docs/04-character-system.md) | Character card format, SillyTavern compatibility |
| [05 — Chat and Conversations](docs/05-chat-and-conversations.md) | Chat flow, conversation model, prompt construction |
| [06 — Connector System](docs/06-connector-system.md) | Connector architecture, interfaces, implementations |
| [07 — Frontend Chat UI](docs/07-frontend-chat-ui.md) | Chat interface specification |
| [08 — Admin Interface](docs/08-admin-interface.md) | Admin panel for connectors, characters, health |
| [09 — Configuration and Setup](docs/09-configuration-and-setup.md) | Installation, config files, startup |

## Post-MVP Roadmap

- [ ] ComfyUI connector backend (advanced local image generation)
- [ ] Video generation connectors
- [ ] Audio/TTS connectors
- [ ] Quota management per conversation
- [ ] Enforced NSFW protection
- [ ] GUI customization via admin (custom CSS stylesheet, header/footer HTML injection, static asset management)
- [ ] Admin interface protection (password and/or IP-based access control)
- [ ] Advanced orchestration (automatic image triggers, style inference)
- [ ] Multi-user / authentication
- [ ] Database storage
- [ ] Plugin system
- [ ] Docker deployment

## Disclaimer

AubergeLLM is an experimental project that was mainly vibe-coded. I have 25+ experience in programming, so I hope there is no rookie mistake in it. All contributions are welcome but I am a busy man, so be patient ^^

## License

Apache 2.0

## Contributing

Contributions are welcome. Please open issues and pull requests.
