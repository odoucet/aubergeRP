from __future__ import annotations

import base64
from typing import Any

import httpx

from ..models.connector import OpenAIImageConfig
from .base import ImageConnector


class OpenAIImageConnector(ImageConnector):
    backend_id = "openai_api"

    def __init__(self, config: OpenAIImageConfig) -> None:
        self.config = config

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _is_openrouter(self) -> bool:
        return "openrouter.ai" in self.config.base_url.lower()

    async def test_connection(self) -> dict[str, Any]:
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

    async def _extract_image_bytes(self, item: dict[str, Any], client: httpx.AsyncClient) -> bytes:
        b64_json = item.get("b64_json")
        if isinstance(b64_json, str) and b64_json:
            return base64.b64decode(b64_json)

        image_url_data = item.get("image_url")
        url = image_url_data.get("url") if isinstance(image_url_data, dict) else item.get("url")

        if not isinstance(url, str) or not url:
            raise ValueError("Image response did not include b64_json or url")

        if url.startswith("data:"):
            _, _, raw = url.partition(",")
            return base64.b64decode(raw)

        img_response = await client.get(url)
        img_response.raise_for_status()
        return img_response.content

    async def _generate_via_openai_images_api(
        self,
        full_prompt: str,
        model: str,
        size: str,
        client: httpx.AsyncClient,
    ) -> bytes:
        payload = {
            "model": model,
            "prompt": full_prompt,
            "size": size,
            "n": 1,
        }
        response = await client.post(
            f"{self.config.base_url}/images/generations",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        item = response.json()["data"][0]
        return await self._extract_image_bytes(item, client)

    async def _generate_via_openrouter_chat_api(
        self,
        full_prompt: str,
        model: str,
        size: str,
        client: httpx.AsyncClient,
    ) -> bytes:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": full_prompt}],
            "modalities": ["image"],
            "stream": False,
            "image_config": {"size": size},
        }
        response = await client.post(
            f"{self.config.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        message = (data.get("choices") or [{}])[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return await self._extract_image_bytes(part, client)

        images = message.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict):
                return await self._extract_image_bytes(first, client)

        raise ValueError("OpenRouter did not return an image in chat/completions response")

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        model: str | None = None,
        size: str | None = None,
    ) -> bytes:
        full_prompt = f"{prompt}. Avoid: {negative_prompt}" if negative_prompt else prompt
        resolved_model = model or self.config.model
        resolved_size = size or self.config.size

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            if self._is_openrouter():
                return await self._generate_via_openrouter_chat_api(
                    full_prompt,
                    resolved_model,
                    resolved_size,
                    client,
                )
            return await self._generate_via_openai_images_api(
                full_prompt,
                resolved_model,
                resolved_size,
                client,
            )
