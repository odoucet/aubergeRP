# Project Structure

```
aubergeRP/
├── aubergeRP/               # Python backend package
│   ├── main.py              # FastAPI app, startup
│   ├── config.py            # Config loading (YAML + env overrides)
│   ├── database.py          # SQLite engine + session
│   ├── db_models.py         # SQLModel table definitions
│   ├── event_bus.py         # In-process SSE event bus
│   ├── scheduler.py         # Background media-cleanup scheduler
│   ├── connectors/          # Connector implementations
│   │   ├── base.py          # Abstract base classes
│   │   ├── manager.py       # ConnectorManager
│   │   ├── openai_text.py
│   │   ├── openai_image.py
│   │   └── comfyui.py
│   ├── migrations/          # Numbered SQLite migrations (auto-applied at startup)
│   ├── models/              # Pydantic request/response models
│   ├── routers/             # FastAPI route handlers (thin — delegate to services)
│   ├── services/            # Business logic
│   ├── plugins/             # Plugin system skeleton
│   └── utils/               # Shared helpers
├── frontend/                # Static HTML/JS/CSS
│   ├── index.html           # Chat UI
│   ├── admin/index.html     # Admin UI
│   ├── js/                  # JavaScript modules
│   └── vendor/              # Vendored JS libs (marked.js, …)
├── tests/                   # Pytest test suite
├── docs/                    # Developer documentation (this folder)
├── docker/                  # Docker stack
│   ├── docker-compose.yml
│   └── profiles/            # Hardware profiles (rtx3090.yml, …)
├── config.example.yaml      # Example config — copy to config.yaml
├── Makefile
├── Dockerfile
├── requirements.txt         # Runtime Python dependencies
└── requirements-dev.txt     # Test/lint/dev-only Python dependencies
```

## Architecture rules

1. **Routers are thin.** No business logic — delegate to services.
2. **Services own all logic.** No imports from `routers/`.
3. **Connectors are isolated.** One file per backend. Register in `connectors/manager.py`.
4. **Every schema change needs a migration.** Add `aubergeRP/migrations/m{NNN}_{slug}.py`.

## Adding a connector backend

See [06-connector-system.md](06-connector-system.md) for the step-by-step guide.
