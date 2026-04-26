from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_config
from .constants import SESSION_TOKEN
from .routers import characters as characters_router
from .routers import chat as chat_router
from .routers import config as config_router
from .routers import connectors as connectors_router
from .routers import conversations as conversations_router
from .routers import health as health_router
from .routers import images as images_router


def _init_data_dirs(data_dir: str) -> None:
    base = Path(data_dir)
    for subdir in [
        "characters", "conversations", "connectors", "avatars",
        f"images/{SESSION_TOKEN}",
    ]:
        (base / subdir).mkdir(parents=True, exist_ok=True)


def create_app() -> FastAPI:
    config = get_config()
    _init_data_dirs(config.app.data_dir)

    app = FastAPI(
        title="aubergeRP",
        version="0.1.0",
        description="A lightweight roleplay frontend with pluggable connectors",
    )

    app.include_router(characters_router.router, prefix="/api")
    app.include_router(conversations_router.router, prefix="/api")
    app.include_router(chat_router.router, prefix="/api")
    app.include_router(connectors_router.router, prefix="/api")
    app.include_router(config_router.router, prefix="/api")
    app.include_router(images_router.router, prefix="/api")
    app.include_router(health_router.router, prefix="/api")

    frontend = Path("frontend")
    if frontend.exists():
        app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")

    return app


app = create_app()
