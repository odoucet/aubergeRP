from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, AsyncIterator

from ..connectors.manager import ConnectorManager
from ..models.character import CharacterCard
from ..models.conversation import Conversation
from ..services.character_service import CharacterService
from ..services.conversation_service import ConversationService, resolve_macros

_PREFIX = "[IMG:"
_MAX_IMAGE_MARKERS = 3


class ImageMarkerParser:
    """State machine that parses [IMG:prompt] markers in streaming text chunks."""

    def __init__(self) -> None:
        self._state = "text"   # "text" | "prefix" | "marker"
        self._buf = ""         # partial prefix buffer
        self._marker_buf = ""  # content inside [IMG:...]
        self._marker_count = 0  # hard cap: max 3 per message

    def feed(self, chunk: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        pending = ""

        for char in chunk:
            if self._state == "text":
                if char == "[":
                    if pending:
                        events.append({"type": "token", "text": pending})
                        pending = ""
                    self._state = "prefix"
                    self._buf = "["
                else:
                    pending += char

            elif self._state == "prefix":
                candidate = self._buf + char
                if _PREFIX.startswith(candidate):
                    self._buf = candidate
                    if self._buf == _PREFIX:
                        self._state = "marker"
                        self._marker_buf = ""
                        self._buf = ""
                else:
                    events.append({"type": "token", "text": candidate})
                    self._buf = ""
                    self._state = "text"

            elif self._state == "marker":
                if char == "]":
                    if self._marker_count < _MAX_IMAGE_MARKERS:
                        self._marker_count += 1
                        events.append({"type": "image_trigger", "prompt": self._marker_buf})
                    else:
                        # Cap exceeded: emit the marker text as a plain token
                        events.append({"type": "token", "text": _PREFIX + self._marker_buf + "]"})
                    self._marker_buf = ""
                    self._state = "text"
                else:
                    self._marker_buf += char

        if pending:
            events.append({"type": "token", "text": pending})

        return events

    def flush(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if self._state == "prefix" and self._buf:
            events.append({"type": "token", "text": self._buf})
            self._buf = ""
        elif self._state == "marker":
            events.append({"type": "token", "text": _PREFIX + self._marker_buf})
            self._marker_buf = ""
        self._state = "text"
        return events


_DEFAULT_SYSTEM_PROMPT = (
    "You are {{char}}, a character in a roleplay conversation. Stay in character at all "
    "times. Write in a descriptive, immersive style. Respond naturally to what {{user}} "
    "says. Do not break character or mention that you are an AI. When a visual moment "
    "would enrich the scene and the user requests it, emit an inline image marker (see "
    "formatting rules provided)."
)

_IMAGE_MARKER_INSTRUCTION = (
    "When the user explicitly requests a visual (e.g. \"show me\", \"send a picture\"), "
    "emit an inline marker `[IMG: <short English description>]`. Do NOT emit markers "
    "unless the user asked for one. Keep the description concrete and under 200 characters. "
    "Continue your narration normally after the marker."
)


def build_prompt(
    conversation: Conversation,
    char: CharacterCard,
    user_name: str = "User",
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    system_parts: list[str] = []
    base_prompt = char.data.system_prompt if char.data.system_prompt else _DEFAULT_SYSTEM_PROMPT
    system_parts.append(resolve_macros(base_prompt, char.data.name, user_name))
    # Always append the image-marker instruction
    system_parts.append(_IMAGE_MARKER_INSTRUCTION)
    if char.data.description:
        system_parts.append(f"{char.data.name}'s description: {resolve_macros(char.data.description, char.data.name, user_name)}")
    if char.data.personality:
        system_parts.append(f"{char.data.name}'s personality: {resolve_macros(char.data.personality, char.data.name, user_name)}")
    if char.data.scenario:
        system_parts.append(f"Scenario: {resolve_macros(char.data.scenario, char.data.name, user_name)}")
    if char.data.mes_example:
        system_parts.append(f"Example dialogue:\n{resolve_macros(char.data.mes_example, char.data.name, user_name)}")
    messages.append({"role": "system", "content": "\n\n".join(system_parts)})

    for msg in conversation.messages:
        messages.append({"role": msg.role, "content": msg.content})

    if char.data.post_history_instructions:
        messages.append({
            "role": "system",
            "content": resolve_macros(char.data.post_history_instructions, char.data.name, user_name),
        })

    return messages


class ChatService:
    def __init__(
        self,
        conversation_service: ConversationService,
        character_service: CharacterService,
        connector_manager: ConnectorManager,
        images_dir: "Path | str",
        session_token: str = "",
    ) -> None:
        self._conversation_service = conversation_service
        self._character_service = character_service
        self._connector_manager = connector_manager
        self._images_dir = Path(images_dir)
        self._session_token = session_token

    async def stream_chat(
        self,
        conversation_id: str,
        content: str,
        user_name: str = "User",
    ) -> AsyncIterator[dict[str, Any]]:
        try:
            self._conversation_service.append_message(conversation_id, "user", content)
        except Exception as exc:
            yield {"type": "error", "detail": str(exc)}
            return

        try:
            conv = self._conversation_service.get_conversation(conversation_id)
            char = self._character_service.get_character(conv.character_id)
        except Exception as exc:
            yield {"type": "error", "detail": str(exc)}
            return

        text_connector = self._connector_manager.get_active_text_connector()
        if text_connector is None:
            yield {"type": "error", "detail": "No active text connector configured"}
            return

        messages = build_prompt(conv, char, user_name)
        parser = ImageMarkerParser()
        full_text = ""
        image_urls: list[str] = []

        try:
            async for chunk in text_connector.stream_chat_completion(messages):
                for event in parser.feed(chunk):
                    if event["type"] == "token":
                        full_text += event["text"]
                        yield {"type": "token", "content": event["text"]}
                    elif event["type"] == "image_trigger":
                        gen_id = str(uuid.uuid4())
                        prompt = event["prompt"]
                        yield {"type": "image_start", "generation_id": gen_id, "prompt": prompt}
                        async for img_event in self._handle_image(char, gen_id, prompt):
                            if img_event["type"] == "image_complete":
                                image_urls.append(img_event["image_url"])
                            yield img_event

            for event in parser.flush():
                if event["type"] == "token":
                    full_text += event["text"]
                    yield {"type": "token", "content": event["text"]}

            msg = self._conversation_service.append_message(
                conversation_id, "assistant", full_text, images=image_urls
            )
            yield {
                "type": "done",
                "message_id": msg.id,
                "full_content": full_text,
                "images": image_urls,
            }

        except Exception as exc:
            yield {"type": "error", "detail": str(exc)}

    async def _handle_image(
        self, char: CharacterCard, gen_id: str, prompt: str
    ) -> AsyncIterator[dict[str, Any]]:
        img_connector = self._connector_manager.get_active_image_connector()
        if img_connector is None:
            yield {"type": "image_failed", "generation_id": gen_id, "detail": "No active image connector"}
            return
        try:
            auberge = char.data.extensions.get("aubergeRP", {})
            prefix = auberge.get("image_prompt_prefix", "")
            negative = auberge.get("negative_prompt", "")
            full_prompt = f"{prefix} {prompt}".strip() if prefix else prompt
            img_bytes: bytes | None = None
            async for event in img_connector.generate_image_with_progress(full_prompt, negative_prompt=negative):
                if event["type"] == "progress":
                    yield {
                        "type": "image_progress",
                        "generation_id": gen_id,
                        "step": event["step"],
                        "total": event["total"],
                    }
                elif event["type"] == "complete":
                    img_bytes = event["bytes"]
            if img_bytes is None:
                yield {"type": "image_failed", "generation_id": gen_id, "detail": "No image returned"}
                return
            self._images_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4()}.png"
            (self._images_dir / filename).write_bytes(img_bytes)
            url = f"/api/images/{self._session_token}/{filename}"
            yield {"type": "image_complete", "generation_id": gen_id, "image_url": url}
        except Exception as exc:
            yield {"type": "image_failed", "generation_id": gen_id, "detail": str(exc)}
