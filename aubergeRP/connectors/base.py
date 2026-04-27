from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class BaseConnector(ABC):
    connector_type: str
    backend_id: str

    @abstractmethod
    async def test_connection(self) -> dict:
        """Return {'connected': bool, 'details': {...}}."""


class TextConnector(BaseConnector):
    connector_type = "text"

    @abstractmethod
    async def stream_chat_completion(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield text tokens from a streaming chat completion."""


class ImageConnector(BaseConnector):
    connector_type = "image"

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        model: str | None = None,
        size: str | None = None,
    ) -> bytes:
        """Generate an image and return raw PNG bytes."""

    async def generate_image_with_progress(
        self,
        prompt: str,
        negative_prompt: str = "",
        model: str | None = None,
        size: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield progress and completion events during image generation.

        Events:
          {"type": "progress", "step": int, "total": int}
          {"type": "complete", "bytes": bytes}

        Default implementation wraps generate_image() with a single complete event.
        Subclasses can override to emit granular progress events.
        """
        img_bytes = await self.generate_image(prompt, negative_prompt, model, size)
        yield {"type": "complete", "bytes": img_bytes}
