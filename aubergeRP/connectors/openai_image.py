from __future__ import annotations

import base64

import httpx

from ..models.connector import OpenAIImageConfig
from .base import ImageConnector


class OpenAIImageConnector(ImageConnector):
    backend_id = "openai_api"

    def __init__(self, config: OpenAIImageConfig) -> None:
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

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        model: str | None = None,
        size: str | None = None,
    ) -> bytes:
        full_prompt = f"{prompt}. Avoid: {negative_prompt}" if negative_prompt else prompt
        payload = {
            "model": model or self.config.model,
            "prompt": full_prompt,
            "size": size or self.config.size,
            "n": 1,
        }
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.base_url}/images/generations",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            item = response.json()["data"][0]

            if item.get("b64_json"):
                return base64.b64decode(item["b64_json"])

            img_response = await client.get(item["url"])
            img_response.raise_for_status()
            return img_response.content
