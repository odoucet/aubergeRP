from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from ..models.connector import OpenAITextConfig
from .base import TextConnector


class OpenAITextConnector(TextConnector):
    backend_id = "openai_api"

    def __init__(self, config: OpenAITextConfig) -> None:
        self.config = config

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}

    async def test_connection(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(
                    f"{self.config.base_url}/models",
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
                models = [m["id"] for m in data.get("data", [])]
                return {"connected": True, "details": {"models_available": models}}
        except Exception as exc:
            return {"connected": False, "details": {"error": str(exc)}}

    async def stream_chat_completion(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model or self.config.model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.config.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload_str = line[6:]
                    if payload_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload_str)
                        content = chunk["choices"][0]["delta"].get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
