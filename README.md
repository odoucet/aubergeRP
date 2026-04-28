# 🏰 AubergeRP

**The cozy, distraction-free roleplay engine.** *Stop configuring, start roleplaying.*

AubergeRP is a lightweight, self-hostable alternative to SillyTavern. It’s designed for those who want a beautiful, "plug-and-play" experience with local or remote LLMs, featuring native AI image generation without the headache of complex extensions.

## ✨ Why AubergeRP?

| Feature            | AubergeRP          | Other Tools (ST, etc.)      |
| :---               | :---               | :---                        |
| **Setup Time**     | < 10 minutes       | Can take hours              |
| **Interface**      | Minimalist & Cozy  | Complex "Control Room"      |
| **Image Gen**      | Native & Automatic | Requires complex extensions |
| **Learning Curve** | None (Plug & Play) | High (Many sliders/tabs)    |

## 📸 Preview

| Desktop View | Mobile View |
| :---         | :--- |
| ![Desktop Screenshot](docs/img/desktop-main.png) | ![Mobile Screenshot](docs/img/mobile-view.png) |


## 🚀 Key Features

* **Zero-Friction Setup:** Get running in minutes with Docker.
* **Universal Connectivity:** Support for any OpenAI-compatible API (Ollama, OpenRouter, **but also local setup!** vLLM, ollama, etc.).
* **SillyTavern Compatible:** Seamlessly import and export your favorite `.png` or `.json` character cards.
* **Smart Image Generation:** The AI triggers image generation automatically based on the story context (via ComfyUI or SD-WebUI).
* **Lightweight Stack:** No complex build steps. Just Python (FastAPI) and Vanilla JS.
* **Admin Dashboard:** Easily manage your connectors, characters, and check your usage stats.


## 🛠 Quick Start

1. **Clone & Config**
   ```bash
   git clone https://github.com/odoucet/aubergeRP.git
   cd aubergeRP
   cp config.example.yaml config.yaml
   ```

2. **Launch with Docker**
   ```bash
   make docker
   ```

3. **Enjoy!**
   Open **http://localhost:8123**. The admin password is displayed in your terminal logs.
   * Go to **Admin** -> Add a **Text Connector**.
   * Import a character and start your story.

> [!TIP]
> Using a local GPU? Check the [Installation Guide](docs/installation-guide.md) for optimized Docker commands (`make docker gpu=rtx3090`).


## 🏗 Technology Stack

* **Backend:** Python 3.11+, FastAPI, SQLite.
* **Frontend:** Vanilla HTML/JS + Tailwind CSS (No heavy frameworks).
* **Protocols:** SSE (Server-Sent Events) for real-time streaming.
* **License:** Apache 2.0.


## 📚 Documentation

* 📖 [Installation Guide](docs/installation-guide.md) – Step-by-step setup (Docker, GPU, etc.).
* 🧩 [Connector System](docs/06-connector-system.md) – How to add new AI backends.
* ⚙️ [Configuration](docs/09-configuration-and-setup.md) – `config.yaml` reference.
* 🏗 [Architecture](docs/00-architecture-overview.md) – High-level design for contributors.


**AubergeRP** is a labor of love. If you like the project, consider giving it a ⭐ on GitHub!
