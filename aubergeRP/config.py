from __future__ import annotations

import contextlib
import logging
import os
import re
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, field_validator

# ---------------------------------------------------------------------------
# HTML sanitization helpers
# ---------------------------------------------------------------------------

_SCRIPT_TAG_RE = re.compile(
    r"<\s*script[\s\S]*?>[\s\S]*?<\s*/\s*script\s*>",
    re.IGNORECASE,
)
_EVENT_HANDLER_RE = re.compile(
    r"\s+on\w+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]*)",
    re.IGNORECASE,
)
_JAVASCRIPT_HREF_RE = re.compile(
    r'href\s*=\s*["\']?\s*javascript\s*:',
    re.IGNORECASE,
)


def _strip_js(html: str) -> str:
    """Remove <script> blocks, inline event handlers and javascript: hrefs."""
    html = _SCRIPT_TAG_RE.sub("", html)
    html = _EVENT_HANDLER_RE.sub("", html)
    html = _JAVASCRIPT_HREF_RE.sub('href="#"', html)
    return html


class AppConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8123
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    data_dir: str = "data"
    sentry_dsn: str = ""
    admin_password_hash: str = ""


class ActiveConnectorsConfig(BaseModel):
    text: str = ""
    image: str = ""


class UserConfig(BaseModel):
    name: str = "User"


class SchedulerConfig(BaseModel):
    """Background media-cleanup scheduler settings."""

    enabled: bool = False
    # How often to run the cleanup (in seconds). Default: 24 h.
    interval_seconds: int = 86400
    # Delete images older than this many days. Default: 30.
    cleanup_older_than_days: int = 30

class ChatConfig(BaseModel):
    """Global settings that influence AI quality behaviour."""

    # Estimated size of the model's context window in tokens.
    context_window: int = 4096
    # Summarize conversation history when this fraction of the context window is consumed.
    summarization_threshold: float = 0.75
    # Enable out-of-character (OOC) detection and guardrail injection.
    ooc_protection: bool = True


class GuiConfig(BaseModel):
    """GUI customization settings."""

    # Arbitrary CSS injected into every page inside a <style> tag.
    custom_css: str = ""
    # Raw HTML inserted just after the opening <header> tag.
    custom_header_html: str = ""
    # Raw HTML inserted just before the closing </footer> tag.
    custom_footer_html: str = ""

    @field_validator("custom_header_html", "custom_footer_html", mode="before")
    @classmethod
    def sanitize_html(cls, v: object) -> object:
        if isinstance(v, str):
            return _strip_js(v)
        return v


class Config(BaseModel):
    app: AppConfig = AppConfig()
    active_connectors: ActiveConnectorsConfig = ActiveConnectorsConfig()
    user: UserConfig = UserConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    chat: ChatConfig = ChatConfig()
    gui: GuiConfig = GuiConfig()

    @field_validator("app", mode="before")
    @classmethod
    def validate_app(cls, v: object) -> object:
        return v or {}

    @field_validator("active_connectors", mode="before")
    @classmethod
    def validate_active_connectors(cls, v: object) -> object:
        return v or {}

    @field_validator("user", mode="before")
    @classmethod
    def validate_user(cls, v: object) -> object:
        return v or {}

    @field_validator("scheduler", mode="before")
    @classmethod
    def validate_scheduler(cls, v: object) -> object:
        return v or {}

    @field_validator("chat", mode="before")
    @classmethod
    def validate_chat(cls, v: object) -> object:
        return v or {}

    @field_validator("gui", mode="before")
    @classmethod
    def validate_gui(cls, v: object) -> object:
        return v or {}

def _apply_env_overrides(config: Config) -> Config:
    """Override config values with environment variables if set.

    Supported variables:
        AUBERGE_DATA_DIR           → config.app.data_dir
        AUBERGE_HOST               → config.app.host
        AUBERGE_PORT               → config.app.port  (integer)
        AUBERGE_LOG_LEVEL          → config.app.log_level
        AUBERGE_USER_NAME          → config.user.name
        AUBERGE_SENTRY_DSN         → config.app.sentry_dsn
        AUBERGE_ADMIN_PASSWORD_HASH → config.app.admin_password_hash
    """
    if val := os.environ.get("AUBERGE_DATA_DIR"):
        config.app.data_dir = val
    if val := os.environ.get("AUBERGE_HOST"):
        config.app.host = val
    if val := os.environ.get("AUBERGE_PORT"):
        config.app.port = int(val)
    if val := os.environ.get("AUBERGE_LOG_LEVEL"):
        config.app.log_level = val  # type: ignore[assignment]
    if val := os.environ.get("AUBERGE_USER_NAME"):
        config.user.name = val
    if val := os.environ.get("AUBERGE_SENTRY_DSN"):
        config.app.sentry_dsn = val
    if val := os.environ.get("AUBERGE_ADMIN_PASSWORD_HASH"):
        config.app.admin_password_hash = val
    return config

def load_config(path: str | Path = "config.yaml") -> Config:
    log = logging.getLogger(__name__)
    config_path = Path(path).resolve()
    if not config_path.exists():
        log.warning("config.yaml not found at %s — using defaults", config_path)
        return _apply_env_overrides(Config())
    with config_path.open() as f:
        raw = yaml.safe_load(f) or {}
    config = _apply_env_overrides(Config(**raw))
    log.info(
        "Config loaded from %s | data_dir=%s active_text=%s active_image=%s",
        config_path,
        config.app.data_dir,
        config.active_connectors.text or "(none)",
        config.active_connectors.image or "(none)",
    )
    return config


_config: Config | None = None
_config_path: Path = Path("config.yaml")
_config_mtime: float = 0.0


def get_config() -> Config:
    """Return the current configuration, reloading from disk if the file changed.

    In development (``uvicorn --reload``) the process is not restarted on
    ``config.yaml`` changes, so we detect modifications via the file's mtime
    and reload transparently.  In production the overhead is negligible (a
    single ``stat()`` call per request).
    """
    global _config, _config_mtime
    if _config is None:
        _config = load_config(_config_path)
        with contextlib.suppress(OSError):
            _config_mtime = _config_path.resolve().stat().st_mtime
        return _config

    # Check if the file has been modified since last load.
    try:
        current_mtime = _config_path.resolve().stat().st_mtime
    except OSError:
        return _config

    if current_mtime != _config_mtime:
        logging.getLogger(__name__).info(
            "config.yaml changed on disk — reloading configuration"
        )
        _config = load_config(_config_path)
        _config_mtime = current_mtime

    return _config


def reset_config() -> None:
    global _config, _config_mtime
    _config = None
    _config_mtime = 0.0
