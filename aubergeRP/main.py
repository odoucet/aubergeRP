from __future__ import annotations

import logging
import shutil
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import Config, get_config
from .routers import admin as admin_router
from .routers import characters as characters_router
from .routers import chat as chat_router
from .routers import config as config_router
from .routers import connectors as connectors_router
from .routers import conversations as conversations_router
from .routers import health as health_router
from .routers import images as images_router
from .routers import media as media_router
from .routers import prompts as prompts_router
from .routers import statistics as statistics_router
from .services.example_seed_service import seed_example_characters
from .utils.auth import get_or_create_admin_password_hash

_BUILTIN_WORKFLOWS_DIR = Path(__file__).parent / "comfyui_workflows"
logger = logging.getLogger(__name__)


def _init_data_dirs(data_dir: str) -> None:
    base = Path(data_dir)
    for subdir in [
        "characters", "conversations", "connectors", "avatars",
        "images",
        "comfyui_workflows",
    ]:
        (base / subdir).mkdir(parents=True, exist_ok=True)

    # Seed built-in workflow templates into the user data dir (never overwrite)
    user_wf_dir = base / "comfyui_workflows"
    if _BUILTIN_WORKFLOWS_DIR.exists():
        for src in _BUILTIN_WORKFLOWS_DIR.glob("*.json"):
            dst = user_wf_dir / src.name
            if not dst.exists():
                shutil.copy2(src, dst)


def _init_sentry(dsn: str) -> None:
    """Initialise Sentry SDK if a DSN is configured."""
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
    except ImportError:
        pass  # sentry-sdk is an optional dependency


_REDOC_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>aubergeRP — API Reference</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
  <style>body { margin: 0; padding: 0; }</style>
</head>
<body>
  <redoc spec-url='/openapi.json'></redoc>
  <script src="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js"></script>
</body>
</html>
"""


def _autoprovision_connectors(config: Config, data_dir: str) -> None:
    """Create and activate connectors from env vars if not already present.

    Env vars (all optional):
        AUBERGE_LLM_API_URL        OpenAI-compatible base URL  (e.g. http://ollama:11434/v1)
        AUBERGE_LLM_MODEL          Model name                  (e.g. qwen3.6-27b:q4km)
        AUBERGE_LLM_CONTEXT_WINDOW Model context window in tokens (default: 4096)
        AUBERGE_LLM_MAX_TOKENS     Max tokens to generate per reply (default: 1024)
        AUBERGE_IMG_API_URL        Image API base URL
        AUBERGE_IMG_MODEL          Image model name
    """
    import os

    from .connectors.manager import ConnectorManager
    from .models.connector import ConnectorCreate, ConnectorType

    llm_context_window = int(os.environ.get("AUBERGE_LLM_CONTEXT_WINDOW", "4096").strip())
    llm_max_tokens = int(os.environ.get("AUBERGE_LLM_MAX_TOKENS", "1024").strip())

    specs: list[tuple[ConnectorType, str, str]] = [
        ("text",  os.environ.get("AUBERGE_LLM_API_URL", "").strip(), os.environ.get("AUBERGE_LLM_MODEL", "").strip()),
        ("image", os.environ.get("AUBERGE_IMG_API_URL", "").strip(), os.environ.get("AUBERGE_IMG_MODEL", "").strip()),
    ]
    if not any(url and model for _, url, model in specs):
        return

    manager = ConnectorManager(data_dir=data_dir, config=config)

    for conn_type, url, model in specs:
        if not url or not model:
            continue
        existing = [
            c for c in manager.list_connectors(conn_type)
            if c.config.get("base_url") == url and c.config.get("model") == model
        ]
        if existing:
            inst = existing[0]
            if not manager.is_active(inst.id):
                logger.info("Auto-provision: activating existing %s connector '%s'", conn_type, model)
                try:
                    manager.set_active(inst.id)
                except OSError:
                    logger.warning("Auto-provision: config.yaml is read-only, active connector not persisted")
            else:
                logger.info("Auto-provision: %s connector '%s' already active", conn_type, model)
            continue
        logger.info("Auto-provision: creating %s connector '%s' @ %s", conn_type, model, url)
        extra = {"context_window": llm_context_window, "max_tokens": llm_max_tokens} if conn_type == "text" else {}
        inst = manager.create_connector(ConnectorCreate(
            name=model,
            type=conn_type,
            backend="openai_api",
            config={"base_url": url, "model": model, "api_key": "", **extra},
        ))
        try:
            manager.set_active(inst.id)
        except OSError:
            logger.warning("Auto-provision: config.yaml is read-only, active connector not persisted")


def _init_admin_password(config: Config) -> None:
    """Initialize admin password: generate if missing and log it."""
    current_hash = config.app.admin_password_hash or ""
    new_hash, plain_password = get_or_create_admin_password_hash(current_hash)
    config.app.admin_password_hash = new_hash

    if plain_password:
        logger.info("=" * 70)
        logger.info("ADMIN PASSWORD GENERATED (first startup)")
        logger.info("Password: %s", plain_password)
        logger.info("Store this securely. You can set AUBERGE_ADMIN_PASSWORD_HASH")
        logger.info("in the environment to reuse the same password across restarts.")
        logger.info("=" * 70)


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    config = get_config()
    logger.info(
        "Starting aubergeRP | data_dir=%s port=%s log_level=%s",
        Path(config.app.data_dir).resolve(),
        config.app.port,
        config.app.log_level,
    )
    _init_data_dirs(config.app.data_dir)
    _init_sentry(config.app.sentry_dsn)
    _init_admin_password(config)
    _autoprovision_connectors(config, config.app.data_dir)

    # Initialise SQLite database and run migrations
    from .database import init_db
    init_db(config.app.data_dir)

    try:
        seed_example_characters(config.app.data_dir)
    except Exception:
        logger.exception("Example character seeding failed at startup")

    from .scheduler import Scheduler
    scheduler = Scheduler(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        scheduler.start()
        yield
        scheduler.stop()

    app = FastAPI(
        title="aubergeRP",
        version="0.1.0",
        description="A lightweight roleplay frontend with pluggable connectors",
        lifespan=lifespan,
        # Disable default docs paths — we serve our own at /api-docs
        docs_url=None,
        redoc_url=None,
    )

    # ── CORS auto-detection middleware ──────────────────────────────────────
    # Reads the Host header from each request and adds it as an allowed origin
    # so that browsers on the same machine always pass CORS checks.
    @app.middleware("http")
    async def cors_auto_detect(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        host = request.headers.get("host", "")
        origin = request.headers.get("origin", "")
        if origin and host:
            try:
                # Compare the origin's netloc (host+port) against the Host header
                # to avoid substring-match false positives (e.g. evil.host.com vs host.com).
                origin_netloc = urlparse(origin).netloc
                if origin_netloc == host:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
                    response.headers["Access-Control-Allow-Headers"] = "*"
            except Exception:
                pass
        return response

    app.include_router(characters_router.router, prefix="/api")
    app.include_router(conversations_router.router, prefix="/api")
    app.include_router(chat_router.router, prefix="/api")
    app.include_router(admin_router.router, prefix="/api")
    app.include_router(connectors_router.router, prefix="/api")
    app.include_router(config_router.router, prefix="/api")
    app.include_router(images_router.router, prefix="/api")
    app.include_router(media_router.router, prefix="/api")
    app.include_router(health_router.router, prefix="/api")
    app.include_router(statistics_router.router, prefix="/api")
    app.include_router(prompts_router.router, prefix="/api")

    # ── API reference (Redoc) ───────────────────────────────────────────────
    @app.get("/api-docs", include_in_schema=False, response_class=HTMLResponse)
    async def api_docs() -> HTMLResponse:
        return HTMLResponse(content=_REDOC_HTML)

    frontend = Path("frontend")
    if frontend.exists():
        app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")

    return app


app = create_app()
