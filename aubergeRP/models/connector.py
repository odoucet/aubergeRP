from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ConnectorType = Literal["text", "image", "video", "audio"]
ConnectorBackend = Literal["openai_api", "comfyui"]


class OpenAITextConfig(BaseModel):
    base_url: str = "http://localhost:11434/v1"
    api_key: str = ""
    model: str = "llama3"
    max_tokens: int = 1024
    context_window: int = 4096
    temperature: float = 0.8
    top_p: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    extra_body: dict[str, Any] = Field(default_factory=dict)
    timeout: int = 120
    supports_tool_calling: bool = True


class OpenAIImageConfig(BaseModel):
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    model: str = "google/gemini-2.0-flash-exp:free"
    size: str = "1024x1024"
    timeout: int = 120


class ComfyUIConfig(BaseModel):
    base_url: str = "http://localhost:8188"
    workflow: str = "default"
    timeout: int = 300


class ConnectorInstance(BaseModel):
    """Stored on disk — includes api_key."""
    id: str
    name: str
    type: ConnectorType
    backend: ConnectorBackend
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ConnectorResponse(BaseModel):
    """API response — api_key is redacted to api_key_set."""
    id: str
    name: str
    type: ConnectorType
    backend: ConnectorBackend
    is_active: bool
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ConnectorCreate(BaseModel):
    name: str = Field(..., min_length=1)
    type: ConnectorType
    backend: ConnectorBackend
    config: dict[str, Any] = Field(default_factory=dict)


class ConnectorUpdate(BaseModel):
    name: str = Field(..., min_length=1)
    type: ConnectorType
    backend: ConnectorBackend
    config: dict[str, Any] = Field(default_factory=dict)


class ConnectorTestResult(BaseModel):
    connected: bool
    details: dict[str, Any] = Field(default_factory=dict)


class ConnectorActivateResult(BaseModel):
    id: str
    type: ConnectorType
    is_active: bool
