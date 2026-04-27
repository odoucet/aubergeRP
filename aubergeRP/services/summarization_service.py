"""Automatic conversation summarization.

When the messages that would be sent to the LLM approach a configurable
fraction of the model's context window the oldest non-system messages are
summarized into a single system message.  This keeps the prompt within budget
without losing the narrative thread.

Token counting uses a simple four-characters-per-token heuristic so that no
extra dependency (tiktoken etc.) is required.
"""
from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..connectors.base import TextConnector

# Each message carries a small fixed overhead beyond its content.
_MSG_OVERHEAD_TOKENS = 4
# Reserve some tokens for the new user turn and the assistant's reply.
_REPLY_RESERVE_TOKENS = 256
# Keep at least this many recent messages intact even after summarization.
_MIN_RECENT_MESSAGES = 4


def _count_tokens(text: str) -> int:
    """Approximate token count: ~4 characters per token.

    This heuristic is intentionally model-agnostic and avoids external
    dependencies.  It may be less accurate for non-English text or
    code-heavy content; when in doubt, use a lower summarization_threshold.
    """
    return max(1, len(text) // 4)


def _count_message_tokens(msg: dict[str, Any]) -> int:
    return _count_tokens(msg.get("content") or "") + _MSG_OVERHEAD_TOKENS


def count_prompt_tokens(messages: list[dict[str, Any]]) -> int:
    """Return an approximate total token count for a list of chat messages."""
    return sum(_count_message_tokens(m) for m in messages)


def _build_summary_prompt(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Construct a prompt that asks the LLM to summarize a conversation excerpt."""
    excerpt_lines: list[str] = []
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content") or ""
        excerpt_lines.append(f"{role.upper()}: {content}")
    excerpt = "\n\n".join(excerpt_lines)
    return [
        {
            "role": "system",
            "content": (
                "You are a neutral summarizer. Read the roleplay conversation excerpt below "
                "and write a concise third-person summary (≤ 150 words) that captures the "
                "key narrative events, character actions, and any important details. "
                "Do NOT continue the story; just summarize what happened."
            ),
        },
        {
            "role": "user",
            "content": f"Summarize this conversation excerpt:\n\n{excerpt}",
        },
    ]


async def maybe_summarize(
    messages: list[dict[str, Any]],
    connector: TextConnector,
    context_window: int,
    threshold: float,
) -> list[dict[str, Any]]:
    """Return *messages* (possibly with older turns replaced by a summary).

    If the estimated token count is below *threshold* × *context_window* the
    list is returned unchanged.  Otherwise the oldest non-system messages (all
    but the *_MIN_RECENT_MESSAGES* most recent) are summarised into a single
    system message that is inserted right after the initial system block.
    """
    budget = int(context_window * threshold) - _REPLY_RESERVE_TOKENS
    if count_prompt_tokens(messages) <= budget:
        return messages

    # Split into system-header, candidates-to-summarize, and tail-to-keep.
    # The leading block of system messages is always preserved verbatim.
    system_head: list[dict[str, Any]] = []
    remainder: list[dict[str, Any]] = []
    in_head = True
    for msg in messages:
        if in_head and msg.get("role") == "system":
            system_head.append(msg)
        else:
            in_head = False
            remainder.append(msg)

    # Keep the most recent messages intact.
    cutoff = max(0, len(remainder) - _MIN_RECENT_MESSAGES)
    if cutoff == 0:
        # Nothing to summarize — return as-is to avoid infinite calls.
        return messages

    to_summarize = remainder[:cutoff]
    to_keep = remainder[cutoff:]

    # Call the LLM to produce a summary (non-streaming, collected).
    summary_text = ""
    try:
        summary_prompt = _build_summary_prompt(to_summarize)
        async for chunk in connector.stream_chat_completion(summary_prompt):
            summary_text += chunk
    except Exception:
        # If the summarization call fails, fall back to the original messages.
        return messages

    summary_msg: dict[str, Any] = {
        "role": "system",
        "content": f"[Summary of earlier conversation]\n{summary_text.strip()}",
    }
    return [*system_head, summary_msg, *to_keep]


def summarized_content_from_messages(messages: list[dict[str, Any]]) -> str | None:
    """Return the summary content if the first non-system message is a summary marker."""
    for msg in messages:
        if msg.get("role") == "system" and str(msg.get("content", "")).startswith(
            "[Summary of earlier conversation]"
        ):
            return msg["content"]
    return None


def pack_summary_into_conversation(
    conversation_messages: list[Any],
    summary_text: str,
    kept_count: int,
) -> list[Any]:
    """Replace the oldest messages in the stored conversation with a summary.

    *conversation_messages* is the list of :class:`Message` model objects.
    *kept_count* is the number of recent messages to preserve.
    Returns a new list where the summarized messages are replaced by a single
    summary message.
    """
    # This helper is intentionally thin — callers supply the Message factory.
    # It returns a plain dict so the caller can wrap it in Message as needed.
    import uuid
    from datetime import datetime

    cutoff = max(0, len(conversation_messages) - kept_count)
    kept = conversation_messages[cutoff:]
    now = datetime.now(UTC)
    summary_entry = {
        "id": str(uuid.uuid4()),
        "role": "system",
        "content": f"[Summary of earlier conversation]\n{summary_text}",
        "images": [],
        "timestamp": now.isoformat(),
    }
    return [summary_entry] + [m.model_dump(mode="json") if hasattr(m, "model_dump") else m for m in kept]


def to_json_safe(obj: Any) -> Any:
    """Minimal JSON serialisation helper for datetime objects."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
