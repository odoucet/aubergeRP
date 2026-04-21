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

Additionally, even the legitimate frontend user should not be able to call generation endpoints directly (e.g., image generation), since these consume expensive API credits. Generation must be mediated by the backend through controlled flows (chat, admin connector tests).

### Solution: Two-Tier Token Architecture

AubergeLLM uses **two separate auto-generated tokens** at startup, with distinct scopes:

#### Tier 1 — Session Token (frontend-facing, per-user)

1. **On startup**, the backend generates a session token mechanism. Each connecting client gets a **unique session token** — the session token IS the session ID.
2. **Sessions are stored on disk** as `data/sessions/{uuid}.json`, where the UUID is the session token. On startup, if no session exists for a connecting client (identified by a cookie or browser fingerprint), a new session file is created.
3. **The frontend HTML** pages served by FastAPI include this token as a `<meta>` tag:
   ```html
   <meta name="aubergellm-session-token" content="a1b2c3...random-hex...">
   ```
4. **The frontend JS** reads this token and includes it in all API requests as a header:
   ```
   X-Session-Token: a1b2c3...random-hex...
   ```
5. **The backend validates** this token on all write endpoints. Requests without a valid token receive `403 Forbidden`.

This token protects against **external/network-level abuse**: bots, port scanners, or other devices on the local network cannot call write endpoints.

⚠️ **This token is visible to the frontend user** (via browser dev tools). It intentionally does **not** protect against the user themselves — only against external callers.

#### Tier 2 — Internal Token (backend-only, never exposed)

1. **On startup**, the backend generates a **second** random 256-bit token, also stored in memory only.
2. **This token is never injected into HTML pages** and is never sent to the frontend.
3. It is used exclusively for **backend-internal calls** to expensive generation endpoints (`POST /api/generate/image`, etc.).
4. When the backend needs to trigger image generation (e.g., from the chat flow or admin connector test), it calls the generation endpoint internally, passing this token as `X-Internal-Token`.
5. Direct calls to generation endpoints without this token receive `403 Forbidden` — even if the caller has the session token.

This ensures that **even a frontend user who inspects the HTML source cannot trigger image generation directly**. Generation is always mediated by the backend through controlled endpoints.

### Why Two Tiers?

| Approach | Problem |
|---|---|
| No auth at all | Anyone on the network can burn API credits |
| Single token in HTML | Protects against external attackers, but frontend user can extract it and call generation endpoints directly |
| User-configured API key | Adds setup friction, breaks the "time-to-first-roleplay < 1 hour" goal |
| **Two-tier tokens (chosen)** | **Zero config, blocks both external attackers AND direct user abuse of generation routes** |

### Route Protection Table

| Route | Protection | Reason |
|---|---|---|
| `GET /api/health` | 🔓 Public | Health checks should be accessible |
| `GET /api/characters/*` | 🔓 Public | Read-only, no cost |
| `GET /api/conversations/*` | 🔓 Public | Read-only, no cost |
| `GET /api/images/*` | 🔓 Public | Read-only, serves stored files |
| `GET /api/connectors/*` | 🔓 Public | Read-only config display |
| `GET /api/config` | 🔓 Public | Read-only (sensitive fields redacted) |
| `POST /api/chat/*/message` | 🔒 Session token | Triggers LLM generation (costs credits/GPU) |
| `POST /api/chat/*/generate-image` | 🔒 Session token | Requests image generation via chat flow (backend mediates) |
| `POST /api/characters` | 🔒 Session token | Write operation |
| `PUT /api/characters/*` | 🔒 Session token | Write operation |
| `DELETE /api/characters/*` | 🔒 Session token | Write operation |
| `POST /api/characters/import` | 🔒 Session token | Write operation |
| `POST /api/conversations` | 🔒 Session token | Write operation |
| `DELETE /api/conversations/*` | 🔒 Session token | Write operation |
| `POST /api/connectors` | 🔒 Session token | Admin write operation |
| `PUT /api/connectors/*` | 🔒 Session token | Admin write operation |
| `DELETE /api/connectors/*` | 🔒 Session token | Admin write operation |
| `POST /api/connectors/*/test` | 🔒 Session token | Admin test operation |
| `POST /api/connectors/*/activate` | 🔒 Session token | Admin write operation |
| `PUT /api/config` | 🔒 Session token | Admin write operation |
| `POST /api/generate/image` | 🔐 Internal token | Direct generation — backend-only, never called by frontend |
| `GET /api/generate/image/*/status` | 🔒 Session token | Polls generation progress |

### How Image Generation Works with Two Tiers

```
User sends a message like "please send me a picture"
        │
        ▼
POST /api/chat/{id}/message   ← requires X-Session-Token (in HTML)
        │
        ▼
   Backend validates session token
   LLM processes the message and signals that image generation is needed
   Backend builds image prompt from conversation context
        │
        ▼
   Backend internally calls image connector   ← uses X-Internal-Token (never in HTML)
   (or calls POST /api/generate/image with internal token)
        │
        ▼
   Image connector calls external API (OpenRouter, OpenAI, etc.)
        │
        ▼
   Image saved to data/images/{uuid}.png
   Image URL returned to frontend via SSE or response
```

### Error Responses

```json
// 403 Forbidden — missing or invalid session token
{
  "detail": "Invalid or missing session token"
}

// 403 Forbidden — missing or invalid internal token (direct generation call)
{
  "detail": "This endpoint is restricted to internal backend calls"
}
```

### Implementation Notes

- Both tokens are generated using Python's `secrets.token_hex(32)` (256 bits each).
- The **session token** is injected into HTML at serve time via a simple string replacement or template variable — no build step.
- The **internal token** is stored in a module-level variable, accessible only within the backend process. It is never serialized, logged, or exposed in any response.
- Both tokens change on every server restart, which is acceptable for a single-user local app.
- This is **not** a substitute for full authentication (which is post-MVP). It prevents unauthorized API access from the local network and prevents frontend users from directly triggering expensive generation operations.

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

### `POST /api/chat/{conversation_id}/generate-image`

Request image generation within a conversation context. This is the **frontend-facing endpoint** for image generation — it requires only the session token (Tier 1). The backend internally calls the image connector using the internal token (Tier 2).

**Request body:**
```json
{
  "prompt": "A beautiful elf woman standing in an enchanted forest",
  "negative_prompt": "blurry, low quality"
}
```

If `prompt` is omitted or empty, the backend auto-generates one from the last assistant message combined with the character's `image_prompt_prefix`.

**Response: 202 Accepted**
```json
{
  "generation_id": "uuid-string",
  "status": "queued"
}
```

The backend:
1. Validates the session token.
2. Builds the image prompt from the provided prompt or the conversation context.
3. Calls the active image connector internally (with the internal token).
4. Returns a `generation_id` for polling.

The frontend polls `GET /api/generate/image/{generation_id}/status` to track progress.

---

## 7. Image Generation (Backend-Internal)

> ⚠️ **These routes are protected by the internal token (Tier 2)**. They are **not callable from the frontend**. The frontend uses `POST /api/chat/{conversation_id}/generate-image` instead.

### `POST /api/generate/image`

Trigger an image generation using the active image connector. **Requires `X-Internal-Token` header** (backend-only, never exposed to frontend).

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
| 403 | Forbidden (missing or invalid session token, or missing internal token on backend-only routes) |
| 404 | Resource not found (character, conversation, image) |
| 409 | Conflict (duplicate resource) |
| 422 | Validation error (Pydantic) |
| 500 | Internal server error |
| 502 | Upstream error (LLM or ComfyUI unreachable) |
| 504 | Upstream timeout |
