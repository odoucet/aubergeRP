from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..models.connector import OpenAITextConfig
from .base import TextConnector

logger = logging.getLogger(__name__)


class OpenAITextConnector(TextConnector):
    backend_id = "openai_api"

    def __init__(self, config: OpenAITextConfig) -> None:
        self.config = config
        self.supports_tool_calling = config.supports_tool_calling

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

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

                details: dict[str, Any] = {"models_available": models}

                # If models are available, check if the configured model is in the list
                if models and self.config.model not in models:
                    details["model_warning"] = f"Model '{self.config.model}' not found in available models"

                return {"connected": True, "details": details}
        except Exception as exc:
            return {"connected": False, "details": {"error": str(exc)}}

    async def stream_chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": model or self.config.model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }

        # Add optional parameters if provided or configured
        if top_p is not None:
            payload["top_p"] = top_p
        elif self.config.top_p is not None:
            payload["top_p"] = self.config.top_p

        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        elif self.config.presence_penalty is not None:
            payload["presence_penalty"] = self.config.presence_penalty

        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty
        elif self.config.frequency_penalty is not None:
            payload["frequency_penalty"] = self.config.frequency_penalty

        # Merge extra_body (runtime overrides config)
        extra_body_config = self.config.extra_body or {}
        if extra_body:
            extra_body_config = {**extra_body_config, **extra_body}
        if extra_body_config:
            payload.update(extra_body_config)

        model_name = payload["model"]
        req_bytes = len(json.dumps(payload).encode())
        logger.info("LLM request: model=%s messages=%d req=%d bytes", model_name, len(messages), req_bytes)
        logger.debug("LLM payload: %s", json.dumps(payload, ensure_ascii=False))

        total_chars = 0
        total_ignored_chars = 0
        async with httpx.AsyncClient(timeout=self.config.timeout) as client, client.stream(
            "POST",
            f"{self.config.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip(): # Ignorer les lignes vides (Keep-alive)
                    continue
                if not line.startswith("data: "):
                    continue

                payload_str = line[6:]
                if payload_str == "[DONE]":
                    break
                
                try:
                    chunk = json.loads(payload_str)
                    content = chunk["choices"][0]["delta"].get("content")
                    if content:
                        total_chars += len(content)
                        yield content
                    else:
                        total_ignored_chars += len(payload_str)
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
        logger.info("LLM response: model=%s resp=%d chars ignored=%d chars", model_name, total_chars, total_ignored_chars)

    async def stream_chat_completion_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat completion that may produce text tokens and/or tool calls.

        Yields:
          {"type": "token", "content": str}
          {"type": "tool_call", "name": str, "arguments": dict}
        """
        payload: dict[str, Any] = {
            "model": model or self.config.model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "tools": tools,
            "tool_choice": "auto",
        }

        # Add optional parameters if provided or configured
        if top_p is not None:
            payload["top_p"] = top_p
        elif self.config.top_p is not None:
            payload["top_p"] = self.config.top_p

        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        elif self.config.presence_penalty is not None:
            payload["presence_penalty"] = self.config.presence_penalty

        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty
        elif self.config.frequency_penalty is not None:
            payload["frequency_penalty"] = self.config.frequency_penalty

        # Merge extra_body (runtime overrides config)
        extra_body_config = self.config.extra_body or {}
        if extra_body:
            extra_body_config = {**extra_body_config, **extra_body}
        if extra_body_config:
            payload.update(extra_body_config)

        model_name = payload["model"]
        req_bytes = len(json.dumps(payload).encode())
        logger.info("LLM request (tools): model=%s messages=%d tools=%d req=%d bytes", model_name, len(messages), len(tools), req_bytes)
        logger.debug("LLM payload: %s", json.dumps(payload, ensure_ascii=False))

        # Accumulate tool-call argument fragments keyed by call index.
        tool_calls: dict[int, dict[str, Any]] = {}
        total_chars = 0

        async with httpx.AsyncClient(timeout=self.config.timeout) as client, client.stream(
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
                    delta = chunk["choices"][0]["delta"]

                    # Text content
                    content = delta.get("content")
                    if content:
                        total_chars += len(content)
                        yield {"type": "token", "content": content}

                    # Tool call fragments
                    for tc_delta in delta.get("tool_calls") or []:
                        idx: int = tc_delta["index"]
                        if idx not in tool_calls:
                            tool_calls[idx] = {
                                "id": tc_delta.get("id", ""),
                                "name": tc_delta.get("function", {}).get("name", ""),
                                "arguments_raw": "",
                            }
                        fn = tc_delta.get("function", {})
                        if fn.get("name"):
                            tool_calls[idx]["name"] = fn["name"]
                        if fn.get("arguments"):
                            tool_calls[idx]["arguments_raw"] += fn["arguments"]
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

        logger.info("LLM response (tools): model=%s resp=%d chars tool_calls=%d", model_name, total_chars, len(tool_calls))

        # Emit completed tool calls in order.
        for idx in sorted(tool_calls):
            tc = tool_calls[idx]
            try:
                arguments = json.loads(tc["arguments_raw"]) if tc["arguments_raw"] else {}
            except json.JSONDecodeError:
                arguments = {"raw": tc["arguments_raw"]}
            yield {"type": "tool_call", "name": tc["name"], "arguments": arguments}
