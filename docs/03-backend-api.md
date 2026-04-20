# 03 — Backend API Specification

## 1. General Conventions

- **Base URL:** `http://localhost:8000`
- **API prefix:** `/api`
- **Content-Type:** `application/json` for all JSON endpoints.
- **File uploads:** `multipart/form-data`.
- **Streaming responses:** `text/event-stream` (SSE).
- **IDs:** UUID v4 strings (e.g., `"a1b2c3d4-e5f6-7890-abcd-ef1234567890"`).
- **Error responses:** All errors return a JSON body with `{ "detail": "Human-readable error message" }` and an appropriate HTTP status code.

## 2. Health

### `GET /api/health`

Returns the server status and connectivity information.

**Response: 200 OK**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "llm_connected": true,
  "comfyui_connected": false
}
```

---

## 3. Characters

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
      "default_workflow": "default_t2i"
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
      "default_workflow": "default_t2i"
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

## 4. Conversations

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

## 5. Chat

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

## 6. Image Generation

### `POST /api/generate/image`

Trigger an image generation for a conversation.

**Request body:**
```json
{
  "conversation_id": "uuid-string",
  "prompt": "A beautiful elf woman standing in an enchanted forest",
  "workflow": "default_t2i",
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

## 7. ComfyUI Workflows

### `GET /api/workflows`

List available workflow templates.

**Response: 200 OK**
```json
[
  {
    "id": "default_t2i",
    "name": "Default Text-to-Image",
    "description": "Generates an image from a text prompt",
    "inputs": [
      {"name": "prompt", "type": "string", "required": true},
      {"name": "negative_prompt", "type": "string", "required": false}
    ],
    "outputs": [
      {"name": "image", "type": "image"}
    ]
  }
]
```

### `GET /api/workflows/{workflow_id}`

Get details of a specific workflow template.

**Response: 200 OK** — Same structure as list item.

---

## 8. Configuration

### `GET /api/config`

Get current configuration (sensitive fields redacted).

**Response: 200 OK**
```json
{
  "llm": {
    "base_url": "http://localhost:11434/v1",
    "model": "llama3",
    "api_key_set": true
  },
  "comfyui": {
    "base_url": "http://localhost:8188",
    "connected": true
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
  "llm": {
    "base_url": "http://localhost:11434/v1",
    "model": "llama3",
    "api_key": "optional-api-key"
  },
  "comfyui": {
    "base_url": "http://localhost:8188"
  }
}
```

**Response: 200 OK** — Updated config (same as GET).

### `POST /api/config/test-llm`

Test connectivity to the configured LLM backend.

**Response: 200 OK**
```json
{
  "connected": true,
  "model": "llama3",
  "models_available": ["llama3", "mistral"]
}
```

### `POST /api/config/test-comfyui`

Test connectivity to the configured ComfyUI instance.

**Response: 200 OK**
```json
{
  "connected": true,
  "version": "0.2.3"
}
```

---

## 9. Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

| Status Code | Usage |
|---|---|
| 400 | Bad request (invalid input, missing fields) |
| 404 | Resource not found (character, conversation, image) |
| 409 | Conflict (duplicate resource) |
| 422 | Validation error (Pydantic) |
| 500 | Internal server error |
| 502 | Upstream error (LLM or ComfyUI unreachable) |
| 504 | Upstream timeout |
