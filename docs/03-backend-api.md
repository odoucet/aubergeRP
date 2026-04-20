# 03 — Backend API Specification

## 1. General Conventions

- **Base URL:** `http://localhost:8000`
- **API prefix:** `/api`
- **Content-Type:** `application/json` for all JSON endpoints.
- **File uploads:** `multipart/form-data`.
- **Streaming responses:** `text/event-stream` (SSE).
- **IDs:** UUID v4 strings (e.g., `"a1b2c3d4-e5f6-7890-abcd-ef1234567890"`).
- **Error responses:** All errors return a JSON body with `{ "detail": "Human-readable error message" }` and an appropriate HTTP status code.

## 2. Internal API Security

### Problem

AubergeLLM exposes REST endpoints for resource-intensive operations (LLM chat, image generation). Even in a single-user deployment, the API should not allow arbitrary external callers to trigger generation — an attacker or bot scanning the local network could abuse these endpoints, consuming API credits or GPU resources.

### Solution: Auto-Generated Session Token

AubergeLLM uses a **zero-configuration internal token** mechanism:

1. **On startup**, the backend generates a random 256-bit token (hex-encoded) and stores it in memory only (never persisted to disk).
2. **The frontend HTML** pages served by FastAPI include this token as a `<meta>` tag:
   ```html
   <meta name="aubergellm-token" content="a1b2c3...random-hex...">
   ```
3. **The frontend JS** reads this token and includes it in all API requests as a header:
   ```
   X-Internal-Token: a1b2c3...random-hex...
   ```
4. **The backend validates** this token on every protected endpoint. Requests without a valid token receive `403 Forbidden`.

### Why This Approach?

| Alternative | Problem |
|---|---|
| No auth at all | External callers can freely use expensive generation routes |
| User-configured API key | Adds setup friction, breaks the "time-to-first-roleplay < 1 hour" goal |
| Session cookies | Adds state management complexity, CSRF concerns |
| **Auto-generated token (chosen)** | **Zero config, effective against network-level abuse, simple to implement** |

### Protected vs. Public Routes

| Route | Protection | Reason |
|---|---|---|
| `GET /api/health` | 🔓 Public | Health checks should be accessible |
| `GET /api/characters/*` | 🔓 Public | Read-only, no cost |
| `GET /api/conversations/*` | 🔓 Public | Read-only, no cost |
| `GET /api/images/*` | 🔓 Public | Read-only, serves stored files |
| `POST /api/chat/*/message` | 🔒 Token required | Triggers LLM generation (costs credits/GPU) |
| `POST /api/generate/image` | 🔒 Token required | Triggers image generation (costs credits/GPU) |
| `POST /api/characters` | 🔒 Token required | Write operation |
| `PUT /api/characters/*` | 🔒 Token required | Write operation |
| `DELETE /api/characters/*` | 🔒 Token required | Write operation |
| `POST /api/characters/import` | 🔒 Token required | Write operation |
| `POST /api/conversations` | 🔒 Token required | Write operation |
| `DELETE /api/conversations/*` | 🔒 Token required | Write operation |
| `POST /api/connectors` | 🔒 Token required | Admin write operation |
| `PUT /api/connectors/*` | 🔒 Token required | Admin write operation |
| `DELETE /api/connectors/*` | 🔒 Token required | Admin write operation |
| `POST /api/connectors/*/test` | 🔒 Token required | Triggers external call |
| `POST /api/connectors/*/activate` | 🔒 Token required | Admin write operation |
| `PUT /api/config` | 🔒 Token required | Admin write operation |
| `GET /api/connectors/*` | 🔓 Public | Read-only config display |
| `GET /api/config` | 🔓 Public | Read-only (sensitive fields redacted) |

### Error Response

```json
// 403 Forbidden — missing or invalid token
{
  "detail": "Invalid or missing internal token"
}
```

### Implementation Notes

- The token is generated using Python's `secrets.token_hex(32)` (256 bits).
- The token is injected into the HTML at serve time via a simple string replacement or template variable — no build step.
- The token changes on every server restart, which is acceptable for a single-user local app.
- This is **not** a substitute for full authentication (which is post-MVP). It prevents unauthorized API access from the local network.

---

## 3. Health

### `GET /api/health`

Returns the server status and connectivity information.

**Response: 200 OK**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "connectors": {
    "text": {"id": "uuid", "name": "My Ollama", "connected": true},
    "image": {"id": "uuid", "name": "OpenRouter Images", "connected": true},
    "video": null,
    "audio": null
  }
}
```

---

## 4. Characters

### `GET /api/characters`

List all characters in the library.

**Response: 200 OK**
```json
[
  {
    "id": "uuid-string",
    "name": "Character Name",
    "description": "Short description",
    "avatar_url": "/api/characters/uuid-string/avatar",
    "tags": ["fantasy", "elf"],
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
]
```

### `GET /api/characters/{character_id}`

Get full character details.

**Response: 200 OK**
```json
{
  "id": "uuid-string",
  "name": "Character Name",
  "description": "Full character description...",
  "personality": "Character personality traits...",
  "first_mes": "The character's first message...",
  "mes_example": "Example dialogue...",
  "scenario": "The scenario or setting...",
  "system_prompt": "Optional system prompt override...",
  "creator_notes": "Notes from the creator...",
  "tags": ["fantasy", "elf"],
  "avatar_url": "/api/characters/uuid-string/avatar",
  "extensions": {
    "aubergellm": {
      "image_prompt_prefix": "elf woman, fantasy setting",
      "negative_prompt": "blurry, low quality"
    }
  },
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### `POST /api/characters`

Create a new character manually.

**Request body:**
```json
{
  "name": "Character Name",
  "description": "Full character description...",
  "personality": "Traits...",
  "first_mes": "Hello, traveler...",
  "mes_example": "<START>\n{{user}}: Hi\n{{char}}: Hello!",
  "scenario": "A fantasy tavern...",
  "system_prompt": "",
  "creator_notes": "",
  "tags": ["fantasy"],
  "extensions": {
    "aubergellm": {
      "image_prompt_prefix": "",
      "negative_prompt": ""
    }
  }
}
```

**Response: 201 Created**
```json
{
  "id": "uuid-string",
  "name": "Character Name",
  ...
}
```

### `PUT /api/characters/{character_id}`

Update an existing character. Full replacement of editable fields.

**Request body:** Same as POST (without `id`).

**Response: 200 OK** — Updated character object.

### `DELETE /api/characters/{character_id}`

Delete a character and its avatar.

**Response: 204 No Content**

### `GET /api/characters/{character_id}/avatar`

Get the character's avatar image.

**Response: 200 OK** — Image file (`image/png` or `image/jpeg`).
**Response: 404 Not Found** — No avatar set.

### `POST /api/characters/{character_id}/avatar`

Upload or replace the character's avatar.

**Request:** `multipart/form-data` with field `file` (image file).

**Response: 200 OK**
```json
{
  "avatar_url": "/api/characters/uuid-string/avatar"
}
```

### `POST /api/characters/import`

Import a character from a SillyTavern-compatible JSON or PNG file.

**Request:** `multipart/form-data` with field `file` (`.json` or `.png`).

**Response: 201 Created** — The created character object (same as GET).

### `GET /api/characters/{character_id}/export/json`

Export a character as a SillyTavern-compatible JSON file.

**Response: 200 OK** — JSON file download (`Content-Disposition: attachment`).

### `GET /api/characters/{character_id}/export/png`

Export a character as a PNG file with embedded metadata (SillyTavern-compatible).

**Response: 200 OK** — PNG file download (`Content-Disposition: attachment`).

### `POST /api/characters/{character_id}/duplicate`

Duplicate an existing character (creates a new character with a new ID).

**Response: 201 Created** — The new character object.

---

## 5. Conversations

### `GET /api/conversations`

List all conversations, optionally filtered by character.

**Query parameters:**
- `character_id` (optional): Filter by character ID.

**Response: 200 OK**
```json
[
  {
    "id": "uuid-string",
    "character_id": "uuid-string",
    "character_name": "Character Name",
    "title": "Conversation with Character",
    "message_count": 12,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T12:00:00Z"
  }
]
```

### `GET /api/conversations/{conversation_id}`

Get full conversation with all messages.

**Response: 200 OK**
```json
{
  "id": "uuid-string",
  "character_id": "uuid-string",
  "character_name": "Character Name",
  "messages": [
    {
      "id": "uuid-string",
      "role": "assistant",
      "content": "Hello, traveler! Welcome to the tavern.",
      "images": [],
      "timestamp": "2025-01-15T10:31:00Z"
    },
    {
      "id": "uuid-string",
      "role": "user",
      "content": "Tell me about this place.",
      "images": [],
      "timestamp": "2025-01-15T10:31:30Z"
    },
    {
      "id": "uuid-string",
      "role": "assistant",
      "content": "This is the Golden Hearth, the finest inn in the realm.",
      "images": ["/api/images/uuid-string"],
      "timestamp": "2025-01-15T10:32:00Z"
    }
  ],
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:32:00Z"
}
```

### `POST /api/conversations`

Create a new conversation with a character. The character's `first_mes` is automatically added as the first message.

**Request body:**
```json
{
  "character_id": "uuid-string"
}
```

**Response: 201 Created** — The conversation object with the first message.

### `DELETE /api/conversations/{conversation_id}`

Delete a conversation and all its messages.

**Response: 204 No Content**

---

## 6. Chat

### `POST /api/chat/{conversation_id}/message`

Send a user message and stream the LLM response via SSE.

**Request body:**
```json
{
  "content": "Tell me about the enchanted forest."
}
```

**Response: 200 OK** — `text/event-stream`

SSE events:

```
event: token
data: {"content": "The"}

event: token
data: {"content": " enchanted"}

event: token
data: {"content": " forest"}

event: done
data: {"message_id": "uuid-string", "full_content": "The enchanted forest..."}

event: error
data: {"detail": "LLM backend unreachable"}
```

The full assistant message is saved to the conversation after streaming completes.

---

## 7. Image Generation

### `POST /api/generate/image`

Trigger an image generation using the active image connector.

**Request body:**
```json
{
  "conversation_id": "uuid-string",
  "prompt": "A beautiful elf woman standing in an enchanted forest",
  "negative_prompt": "blurry, low quality"
}
```

**Response: 202 Accepted**
```json
{
  "generation_id": "uuid-string",
  "status": "queued"
}
```

### `GET /api/generate/image/{generation_id}/status`

Check the status of an image generation.

**Response: 200 OK**
```json
{
  "generation_id": "uuid-string",
  "status": "completed",
  "image_url": "/api/images/uuid-string",
  "progress": 100
}
```

Status values: `queued`, `running`, `completed`, `failed`.

### `GET /api/images/{image_id}`

Retrieve a generated image file.

**Response: 200 OK** — Image file (`image/png`).

---

## 8. Connectors

### `GET /api/connectors`

List all configured connectors.

**Query parameters:**
- `type` (optional): Filter by type (`text`, `image`, `video`, `audio`).

**Response: 200 OK**
```json
[
  {
    "id": "uuid-string",
    "name": "My Ollama",
    "type": "text",
    "backend": "openai_api",
    "enabled": true,
    "is_active": true,
    "config": {
      "base_url": "http://localhost:11434/v1",
      "model": "llama3",
      "api_key_set": false
    },
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
]
```

### `GET /api/connectors/{connector_id}`

Get full connector details.

**Response: 200 OK** — Full connector object (API key redacted).

### `POST /api/connectors`

Create a new connector.

**Request body:**
```json
{
  "name": "OpenRouter Images",
  "type": "image",
  "backend": "openai_api",
  "config": {
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "sk-or-...",
    "model": "google/gemini-2.0-flash-exp:free"
  }
}
```

**Response: 201 Created** — The created connector object.

### `PUT /api/connectors/{connector_id}`

Update connector configuration.

**Request body:** Same as POST (without `id`).

**Response: 200 OK** — Updated connector object.

### `DELETE /api/connectors/{connector_id}`

Delete a connector.

**Response: 204 No Content**

### `POST /api/connectors/{connector_id}/test`

Test a connector's connection to its backend.

**Response: 200 OK**
```json
{
  "connected": true,
  "details": {
    "models_available": ["llama3", "mistral"]
  }
}
```

### `POST /api/connectors/{connector_id}/activate`

Set a connector as the active one for its type.

**Response: 200 OK**
```json
{
  "id": "uuid-string",
  "type": "text",
  "is_active": true
}
```

### `GET /api/connectors/backends`

List available connector backend types and their supported modalities.

**Response: 200 OK**
```json
[
  {
    "id": "openai_api",
    "name": "OpenAI-Compatible API",
    "supported_types": ["text", "image"],
    "config_schema": {
      "base_url": {"type": "string", "required": true},
      "api_key": {"type": "string", "required": false},
      "model": {"type": "string", "required": true}
    }
  }
]
```

---

## 9. Configuration

### `GET /api/config`

Get current configuration (sensitive fields redacted).

**Response: 200 OK**
```json
{
  "connectors": {
    "text": {"id": "uuid", "name": "My Ollama", "connected": true},
    "image": {"id": "uuid", "name": "OpenRouter Images", "connected": true}
  },
  "app": {
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

### `PUT /api/config`

Update configuration. Only provided fields are updated.

**Request body:**
```json
{
  "app": {
    "host": "0.0.0.0",
    "port": 8000
  },
  "user": {
    "name": "Alice"
  }
}
```

**Response: 200 OK** — Updated config (same as GET).

---

## 10. Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

| Status Code | Usage |
|---|---|
| 400 | Bad request (invalid input, missing fields) |
| 403 | Forbidden (missing or invalid internal token) |
| 404 | Resource not found (character, conversation, image) |
| 409 | Conflict (duplicate resource) |
| 422 | Validation error (Pydantic) |
| 500 | Internal server error |
| 502 | Upstream error (LLM or ComfyUI unreachable) |
| 504 | Upstream timeout |
