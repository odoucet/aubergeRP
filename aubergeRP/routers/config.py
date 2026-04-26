from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, Depends

from ..config import get_config
from ..models.config import (
    ActiveConnectorsResponse,
    AppConfigResponse,
    ConfigResponse,
    ConfigUpdate,
    UserConfigResponse,
)

router = APIRouter(prefix="/config", tags=["config"])


def get_config_save_path() -> Path:
    return Path("config.yaml")


def _to_response() -> ConfigResponse:
    config = get_config()
    return ConfigResponse(
        app=AppConfigResponse(
            host=config.app.host,
            port=config.app.port,
            log_level=config.app.log_level,
        ),
        user=UserConfigResponse(name=config.user.name),
        active_connectors=ActiveConnectorsResponse(
            text=config.active_connectors.text,
            image=config.active_connectors.image,
        ),
    )


@router.get("/")
def get_config_endpoint():
    return _to_response()


@router.put("/")
def update_config(
    update: ConfigUpdate,
    save_path: Path = Depends(get_config_save_path),
):
    config = get_config()

    if update.app is not None:
        config.app.host = update.app.host
        config.app.port = update.app.port
        config.app.log_level = update.app.log_level

    if update.user is not None:
        config.user.name = update.user.name

    if update.active_connectors is not None:
        config.active_connectors.text = update.active_connectors.text
        config.active_connectors.image = update.active_connectors.image

    data = {
        "app": config.app.model_dump(),
        "active_connectors": config.active_connectors.model_dump(),
        "user": config.user.model_dump(),
    }
    with save_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    return _to_response()
