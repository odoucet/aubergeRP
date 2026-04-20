# AubergeLLM

AubergeLLM is a lightweight, self-hostable roleplay engine designed to combine large language models (LLMs) with multimodal generation (image and video) through ComfyUI.

The goal of AubergeLLM is to provide a clean, minimal, and extensible alternative to tools like SillyTavern, while enabling advanced workflows such as:

* Automatic image generation during roleplay
* Character-consistent visuals
* Integration with Stable Diffusion / ComfyUI workflows
* Future support for image-to-video pipelines

## Key Features

### LLM-Driven Roleplay
* Local or remote LLM support (Ollama, OpenAI-compatible APIs)
* Structured prompting and system instructions
* Character and world configuration

### Multimodal Generation
* Native integration with ComfyUI
* Support for:
  * Text-to-Image (T2I)
  * Image-to-Image (I2I)
  * Future: Image-to-Video (I2V)

### Workflow Abstraction
* Decouples UI from ComfyUI graphs
* Normalized input/output interface
* Workflow selection based on context (scene, style, NSFW level, etc.)

### Tool Calling / Orchestration
* LLM can trigger structured actions such as:
  * `generate_image`
  * `generate_video` (planned)
* Hybrid decision system (LLM + rules)

### Modular Architecture
* Frontend (chat / RP UI)
* Backend (API + orchestration)
* ComfyUI (generation engine)

## Architecture Overview

```
[ Frontend UI ]
        ↓
[ AubergeLLM API (FastAPI) ]
        ↓
[ LLM Runtime (Ollama / vLLM) ]
        ↓
[ Orchestrator Layer ]
        ↓
[ ComfyUI API ]
```

### Components
* **Frontend**: Chat interface focused on roleplay
* **Backend API**: Handles requests, routing, and normalization
* **LLM Runtime**: Generates text and tool calls
* **Orchestrator**: Decides when/how to generate visuals
* **ComfyUI**: Executes workflows for image/video generation

## Workflow System
AubergeLLM does not expose raw ComfyUI graphs directly.

Instead, each workflow is defined with a normalized schema:

```yaml
name: character_portrait
inputs:
  prompt: string
  negative_prompt: string
  character_ref: image
  pose_ref: image
  style: string
  seed: int
outputs:
  image: file
```

The backend maps these inputs to ComfyUI nodes and executes the corresponding workflow.

## Orchestration Logic

AubergeLLM uses a hybrid approach:
* **LLM-driven suggestions** (tool calling)
* **Rule-based validation** (cooldowns, scene changes, etc.)

Example:

```json
{
  "tool": "generate_image",
  "scene_type": "portrait",
  "style": "anime",
  "nsfw_level": 1
}
```

The orchestrator then:
* selects the appropriate workflow
* chooses models and LoRAs
* executes the generation

## Getting Started

### Requirements
* NVIDIA GPU (recommended: 3090 or higher)
* Python 3.10+
* ComfyUI
* Ollama or compatible LLM backend (can be remote)

### Setup

WIP


## ComfyUI Integration

AubergeLLM interacts with ComfyUI via:
* `POST /prompt` → submit workflow
* `GET /history/{id}` → retrieve results
* `GET /view` → fetch generated files
* WebSocket → execution updates

Workflows must be exported and versioned. You can start by using the provided (but simple) workflows, then read the future doc on how to use your own workflow.


## Disclaimer

AubergeLLM is an experimental project that was mainly vibe-coded. I have 25+ experience in programming, so I hope there is no rookie mistake in it. All contributions are welcome but I am a busy man, so be patient ^^

## License

Apache 2.0

## Contributing

Contributions are welcome. Please open issues and pull requests.


## Vision

AubergeLLM aims to become a lightweight, extensible storytelling engine where text, images, and video seamlessly merge into a single interactive experience. Project can be usable in seconds, then tweaked easily through : 
* character prompting
* new ComfyUI workflows for image or video generation
