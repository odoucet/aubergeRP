from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator


class AppConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    data_dir: str = "data"
    sentry_dsn: str = ""


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
        AUBERGE_DATA_DIR      → config.app.data_dir
        AUBERGE_HOST          → config.app.host
        AUBERGE_PORT          → config.app.port  (integer)
        AUBERGE_LOG_LEVEL     → config.app.log_level
        AUBERGE_USER_NAME     → config.user.name
        AUBERGE_SENTRY_DSN    → config.app.sentry_dsn
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
    return config

def load_config(path: str | Path = "config.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        return _apply_env_overrides(Config())
    with config_path.open() as f:
        raw = yaml.safe_load(f) or {}
    return _apply_env_overrides(Config(**raw))


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    global _config
    _config = None
