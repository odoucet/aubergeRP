# 05 — Chat and Conversations

## 1. Overview

The chat system is the central user-facing feature. It handles:

- Conversation lifecycle (create, list, delete).
- Message exchange between the user and a character via the active text connector.
- Streaming of assistant tokens and image lifecycle events over a single SSE response.
- **LLM-triggered** image generation via inline markers in the assistant's output.
- Prompt construction from character data + conversation history.
- **Automatic conversation summarization** — when the prompt approaches the configured context-window limit, older messages are compressed into a summary (configurable via `chat.context_window` and `chat.summarization_threshold`).
- **OOC (out-of-character) protection** — detects attempts to break character and injects system-level guardrails when `chat.ooc_protection` is enabled.

## 2. Conversation Model

```json
{
  "id": "uuid-string",
  "character_id": "uuid-string",
  "character_name": "Character Name",
  "title": "Character Name — 2025-01-15 10:30",
  "messages": [
    {
      "id": "uuid-string",
      "role": "assistant",
      "content": "Greetings, traveler!",
      "images": [],
      "timestamp": "2025-01-15T10:31:00Z"
    }
  ],
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:31:00Z"
}
```

### Message

| Field | Type | Description |
|---|---|---|
| `id` | string (UUID) | Unique message identifier |
| `role` | string | `"user"`, `"assistant"`, or `"system"` |
| `content` | string | Message text (markers stripped — see § 7) |
| `images` | string[] | Image URLs (e.g. `/api/images/{session-token}/{uuid}`) |
| `timestamp` | ISO 8601 | Creation time |

## 3. Conversation Lifecycle

### 3.1 Create

1. User selects a character and starts a new conversation.
2. Backend creates a new conversation object with a UUID.
3. `title` is set to `"{character_name} — {YYYY-MM-DD HH:mm}"` (not editable in MVP).
4. If the character has a `first_mes`, it becomes the first `assistant` message (with macros resolved).
5. The conversation is persisted atomically to `data/conversations/{uuid}.json`.

### 3.2 Send a Message

See § 6 for prompt construction and § 7 for image triggering. Summary:

1. User posts to `POST /api/chat/{conversation_id}/message`.
2. Backend appends the user message in memory (not yet persisted).
3. Backend builds the LLM prompt and calls the **active text connector** with streaming.
4. As tokens stream, the backend forwards `token` SSE events to the client and scans the text for image markers (§ 7).
5. When a complete marker is detected, the backend calls the **active image connector** in-process, emitting `image_start` → `image_complete`/`image_failed` events on the same SSE stream.
6. When the LLM finishes, the backend persists the user message and the assistant message (with `images` populated) atomically, and emits `done`.
7. On fatal error, `error` is emitted; **no partial content is saved**.

### 3.3 Delete

- `DELETE /api/conversations/{id}` removes the JSON file.
- Referenced images are **not** deleted.

## 4. Conversation Storage

- One JSON file per conversation: `data/conversations/{uuid}.json`.
- Entire conversation stored in a single file (no message pagination in MVP).
- Writes are **atomic** (write to `{uuid}.json.tmp`, then `os.rename`). No partial files on crash.

## 5. Prompt Construction

### Structure

```
[ SYSTEM ]              system prompt + description + personality + scenario + example
[ HISTORY ]             assistant/user turns in order, starting with first_mes
[ POST-HISTORY ]        system message with post_history_instructions (if any)
[ NEW USER MESSAGE ]
```

### Default System Prompt

When the character's `data.system_prompt` is empty:

```
You are {{char}}, a character in a roleplay conversation. Stay in character at all
times. Write in a descriptive, immersive style. Respond naturally to what {{user}}
says. Do not break character or mention that you are an AI. When a visual moment
would enrich the scene and the user requests it, emit an inline image marker (see
formatting rules provided).
```

The image-marker instruction (§ 7) is **always** appended to the effective system prompt, whether or not the character overrides it. The appended instruction is short and deterministic so the LLM produces parseable output.

### System Message Assembly

Parts are joined with `\n\n` in this order, skipping empty parts:

1. Effective system prompt (character's override if non-empty, else default) + image-marker instruction.
2. `{{char}}'s description: <description>`
3. `{{char}}'s personality: <personality>`
4. `Scenario: <scenario>`
5. `Example dialogue:\n<mes_example>`

### Final Messages Array

```json
[
  {"role": "system", "content": "<assembled system message>"},
  {"role": "assistant", "content": "<first_mes>"},
  {"role": "user", "content": "<message 1>"},
  {"role": "assistant", "content": "<response 1>"},
  ...
  {"role": "system", "content": "<post_history_instructions>"},
  {"role": "user", "content": "<new message>"}
]
```

### Macro Resolution

Before building the prompt, all `{{char}}` and `{{user}}` macros in character fields and prior messages are replaced with actual names.

## 6. LLM Client (via Text Connector)

The chat service uses the active text connector; see [06 — Connector System](06-connector-system.md) for the interface and request/response format. MVP requires streaming (`stream: true`).

### Streaming Response Parsing

The text connector yields tokens one at a time. The chat service:

1. Maintains a rolling **scan buffer** for image-marker detection (§ 7).
2. Forwards safe (non-marker) text to the client as `token` SSE events.
3. Accumulates the full assistant content (markers stripped).
4. On upstream completion, persists the conversation and emits `done`.

## 7. Image Generation Trigger (LLM Marker)

### Marker Format

The assistant emits images by writing a marker inline in its response:

```
[IMG: <image prompt>]
```

- Single-line.
- Brackets are literal `[` and `]`.
- Square brackets may not appear inside the prompt.
- One marker = one image.
- Maximum of 3 markers per assistant message (MVP hard cap — further markers are ignored).

The appended system instruction for the LLM (verbatim):

> When the user explicitly requests a visual (e.g. "show me", "send a picture"), emit an inline marker `[IMG: <short English description>]`. Do NOT emit markers unless the user asked for one. Keep the description concrete and under 200 characters. Continue your narration normally after the marker.

### Detection

The chat service runs a state machine over streamed tokens:

- Accumulates into a scan buffer.
- Recognises the prefix `[IMG:` across token boundaries.
- On match, buffers until `]` is seen, extracts the prompt, and emits nothing to the client for that span.
- On `]`, triggers image generation (see below) and resumes forwarding.

The literal marker text **never** reaches the frontend or the stored message.

### Image Generation Call

For each detected marker, the chat service:

1. Builds the full image prompt:
   `{character.extensions.aubergeRP.image_prompt_prefix} + ", " + <marker prompt>`
   (prefix is omitted if empty).
2. Calls `connector_manager.get_active_image_connector().generate_image(prompt, negative_prompt=character.extensions.aubergeRP.negative_prompt)` — a plain Python function call, no HTTP self-call.
3. On success: saves the bytes to `data/images/{SESSION_TOKEN}/{uuid}.png`, appends the URL to the assistant message's `images`, and emits `image_complete`.
4. On failure: emits `image_failed` with the error detail. Chat continues.

Markers trigger generation **sequentially** within a single message (MVP). The text stream is not paused while waiting — image events interleave naturally on the SSE channel.

### Error Handling

| Scenario | Behavior |
|---|---|
| No active image connector | Emit `image_failed` with `"No image connector configured"`. Strip the marker from the saved message. |
| Image connector backend unreachable | Emit `image_failed`. Continue chat. |
| Generation timeout | Emit `image_failed`. Continue chat. |

## 8. SSE Event Types

See [03 § 6](03-backend-api.md) for the canonical list of events emitted by `POST /api/chat/{id}/message`. Events are: `token`, `image_start`, `image_complete`, `image_failed`, `done`, `error`.

## 9. Service APIs

### Conversation Service

| Function | Description |
|---|---|
| `list_conversations(character_id=None)` | List conversations |
| `get_conversation(id)` | Full conversation |
| `create_conversation(character_id)` | Create and add first_mes |
| `delete_conversation(id)` | Delete conversation file |
| `append_message(conversation_id, message)` | Append a message, atomic save |

### Chat Service

| Function | Description |
|---|---|
| `build_prompt(character, conversation, user_message)` | Assemble the LLM prompt |
| `stream_response(conversation_id, user_message)` | Send + stream + image trigger (yields SSE events) |
| `resolve_macros(text, char_name, user_name)` | Replace `{{char}}` and `{{user}}` |
| `parse_image_markers(stream)` | State machine splitting tokens from `[IMG:...]` prompts |

## 10. Error Handling (Chat)

| Scenario | Behavior |
|---|---|
| LLM backend unreachable | SSE `error`; conversation preserved up to the previous message |
| LLM returns empty response | SSE `error` with descriptive message; nothing saved |
| LLM timeout | SSE `error`; nothing saved |
| No active text connector | HTTP 400: `"No text connector configured"` (before opening SSE) |
| Invalid conversation ID | HTTP 404 |
| Character deleted mid-conversation | Conversation still accessible; character name shown from stored `character_name` |
