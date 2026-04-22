from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AppConfigResponse(BaseModel):
    host: str
    port: int
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class ActiveConnectorsResponse(BaseModel):
    text: str = ""
    image: str = ""


class UserConfigResponse(BaseModel):
    name: str


class ConfigResponse(BaseModel):
    app: AppConfigResponse
    user: UserConfigResponse
    active_connectors: ActiveConnectorsResponse


class ConfigUpdate(BaseModel):
    """Partial update — all fields optional."""
    app: AppConfigResponse | None = None
    user: UserConfigResponse | None = None
    active_connectors: ActiveConnectorsResponse | None = None
