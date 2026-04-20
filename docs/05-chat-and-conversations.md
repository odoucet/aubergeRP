# 05 — Chat and Conversations

## 1. Overview

The chat system is the central user-facing feature of AubergeLLM. It manages:

- Conversation lifecycle (create, list, delete).
- Message exchange between the user and a character (via LLM).
- Streaming of LLM responses via SSE.
- Image generation triggers and inline display.
- Prompt construction from character data and conversation history.

## 2. Conversation Model

### Conversation Object

```json
{
  "id": "uuid-string",
  "character_id": "uuid-string",
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

### Message Object

| Field | Type | Description |
|---|---|---|
| `id` | string (UUID) | Unique message identifier |
| `role` | string | `"user"`, `"assistant"`, or `"system"` |
| `content` | string | Message text content |
| `images` | string[] | List of image URLs (e.g., `["/api/images/uuid"]`) |
| `timestamp` | string (ISO 8601) | When the message was created |

## 3. Conversation Lifecycle

### 3.1 Creating a Conversation

1. User selects a character and starts a new conversation.
2. Backend creates a new conversation object with a UUID.
3. If the character has a `first_mes`, it is added as the first `assistant` message (with macros resolved).
4. The conversation is persisted to `data/conversations/{uuid}.json`.

### 3.2 Sending a Message

1. User sends a message via `POST /api/chat/{conversation_id}/message`.
2. Backend appends the user message to the conversation.
3. Backend builds the full LLM prompt (see Section 5).
4. Backend calls the **active text connector** with streaming enabled.
5. Tokens are streamed to the client via SSE (`event: token`).
6. When streaming completes, the full assistant message is saved to the conversation.
7. A `event: done` SSE event is sent with the complete message.

### 3.3 Deleting a Conversation

1. User requests deletion via `DELETE /api/conversations/{conversation_id}`.
2. Backend deletes the JSON file from disk.
3. Associated images are **not** deleted (they may be referenced elsewhere or kept for history).

## 4. Conversation Storage

- One JSON file per conversation in `data/conversations/`.
- File name: `{uuid}.json`.
- The entire conversation (all messages) is stored in a single file.
- File is overwritten on each new message (simple but sufficient for single-user MVP).
- No pagination of messages within a conversation for MVP.

### Storage Limits (Informational)

For MVP, there are no enforced limits. A typical conversation of 100 messages is approximately 50-100 KB in JSON, which is manageable.

## 5. Prompt Construction

The chat service builds the prompt sent to the LLM. The structure follows a conventional roleplay chat format:

### Prompt Structure

```
┌─────────────────────────────────────────────┐
│ SYSTEM MESSAGE                              │
│ ┌─────────────────────────────────────────┐ │
│ │ Character system prompt (or default)    │ │
│ │ + Character description                 │ │
│ │ + Character personality                 │ │
│ │ + Scenario                              │ │
│ │ + Example messages (if any)             │ │
│ └─────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│ CONVERSATION HISTORY                        │
│ ┌─────────────────────────────────────────┐ │
│ │ assistant: first_mes                    │ │
│ │ user: message 1                         │ │
│ │ assistant: response 1                   │ │
│ │ user: message 2                         │ │
│ │ ...                                     │ │
│ └─────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│ POST-HISTORY INSTRUCTIONS (if any)          │
│ ┌─────────────────────────────────────────┐ │
│ │ post_history_instructions as system msg │ │
│ └─────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│ LATEST USER MESSAGE                         │
│ ┌─────────────────────────────────────────┐ │
│ │ user: new message                       │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Default System Prompt

When a character does not specify a `system_prompt`, use this default:

```
You are {{char}}, a character in a roleplay conversation. Stay in character at all times. Write in a descriptive, immersive style. Respond naturally to what {{user}} says. Do not break character or mention that you are an AI.
```

### System Message Assembly

The system message is assembled as follows (parts separated by `\n\n`):

1. **System prompt** (character's `system_prompt` or the default).
2. **Description** — prefixed with `{{char}}'s description: ` if non-empty.
3. **Personality** — prefixed with `{{char}}'s personality: ` if non-empty.
4. **Scenario** — prefixed with `Scenario: ` if non-empty.
5. **Example messages** — prefixed with `Example dialogue:\n` if non-empty.

### Message Array Format (OpenAI API)

The final messages array sent to the LLM:

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

Before building the prompt, all `{{char}}` and `{{user}}` macros in character fields and messages are replaced with actual names.

## 6. LLM Client (via Text Connector)

The chat service uses the **active text connector** from the connector manager to communicate with the LLM backend. See [06 — Connector System](06-connector-system.md) for details on the connector interface.

### Configuration

Text connector configuration is stored in the connector instance (not in global config). Typical settings:

| Setting | Description | Default |
|---|---|---|
| `llm.base_url` | Base URL of the LLM API | `http://localhost:11434/v1` |
| `llm.model` | Model name to use | `llama3` |
| `llm.api_key` | API key (optional, for OpenAI or authenticated backends) | `""` |
| `llm.max_tokens` | Maximum tokens in the response | `1024` |
| `llm.temperature` | Temperature for generation | `0.8` |
| `llm.timeout` | Request timeout in seconds | `120` |

### Request Format

The text connector sends requests in the OpenAI-compatible format:

```http
POST {base_url}/chat/completions
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "model": "{model}",
  "messages": [...],
  "stream": true,
  "max_tokens": 1024,
  "temperature": 0.8
}
```

### Streaming Response Parsing

The LLM API returns SSE with JSON chunks:

```
data: {"choices": [{"delta": {"content": "token"}}]}
data: {"choices": [{"delta": {}}], "finish_reason": "stop"}
data: [DONE]
```

The text connector:
1. Reads each SSE line from the LLM.
2. Extracts the `content` delta.
3. Yields each token.

The chat service:
1. Receives tokens from the connector.
2. Forwards each token to the client as an SSE event.
3. Accumulates the full response.
4. On completion, saves the full message and sends the `done` event.

## 7. Image Generation Trigger

### MVP Approach

For the MVP, image generation is **explicitly triggered by the user**, not automatically by the LLM. The user clicks a "Generate Image" button in the chat interface, which:

1. Sends a `POST /api/generate/image` request.
2. The backend calls the **active image connector** with the prompt.
3. The prompt is either:
   - Manually entered by the user.
   - Auto-generated from the last assistant message (using the character's `image_prompt_prefix` + a summary of the scene).
4. The generated image URL is attached to the conversation and displayed inline.

### Image in Conversation

When an image is generated for a conversation, it is:
1. Saved to `data/images/{uuid}.png`.
2. A new `assistant` message is added (or the existing message is updated) with the image URL in the `images` array.
3. The client receives an SSE event or polls the generation status to display the image.

## 8. SSE Event Types

| Event | Data | Description |
|---|---|---|
| `token` | `{"content": "..."}` | A single token from the LLM response |
| `done` | `{"message_id": "...", "full_content": "..."}` | Streaming complete, full message |
| `error` | `{"detail": "..."}` | An error occurred during streaming |
| `image_status` | `{"generation_id": "...", "status": "...", "progress": N}` | Image generation progress update |
| `image_complete` | `{"generation_id": "...", "image_url": "..."}` | Image generation finished |

## 9. Conversation Service API

| Function | Description |
|---|---|
| `list_conversations(character_id=None)` | List conversations, optionally filtered |
| `get_conversation(id)` | Get full conversation with messages |
| `create_conversation(character_id)` | Create new conversation, add first_mes |
| `delete_conversation(id)` | Delete conversation file |
| `add_message(conversation_id, role, content, images=[])` | Append a message |
| `get_messages_for_prompt(conversation_id)` | Get messages formatted for LLM prompt |

## 10. Chat Service API

| Function | Description |
|---|---|
| `build_prompt(character, conversation, user_message)` | Assemble the full prompt |
| `stream_response(conversation_id, user_message)` | Send message, stream LLM response via SSE |
| `resolve_macros(text, char_name, user_name)` | Replace {{char}} and {{user}} macros |

## 11. Error Handling

| Scenario | Behavior |
|---|---|
| LLM backend unreachable | Return SSE `error` event; conversation is preserved up to the last saved message |
| LLM returns empty response | Return SSE `error` event with descriptive message |
| LLM timeout | Return SSE `error` event; partial response is NOT saved |
| No active text connector | Return 400 error: "No text connector configured" |
| Invalid conversation ID | Return 404 |
| Character deleted mid-conversation | Conversation remains accessible; character name shown from stored data |
