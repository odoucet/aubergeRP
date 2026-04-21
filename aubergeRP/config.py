from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator


class AppConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    data_dir: str = "data"


class ActiveConnectorsConfig(BaseModel):
    text: str = ""
    image: str = ""


class UserConfig(BaseModel):
    name: str = "User"


class Config(BaseModel):
    app: AppConfig = AppConfig()
    active_connectors: ActiveConnectorsConfig = ActiveConnectorsConfig()
    user: UserConfig = UserConfig()

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


def load_config(path: str | Path = "config.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        return Config()
    with config_path.open() as f:
        raw = yaml.safe_load(f) or {}
    return Config(**raw)


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    global _config
    _config = None
