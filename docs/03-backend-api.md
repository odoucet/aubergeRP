# 03 — Backend API Specification

## 1. General Conventions

- **Base URL:** `http://localhost:8000`
- **API prefix:** `/api`
- **Content-Type:** `application/json` for JSON endpoints.
- **File uploads:** `multipart/form-data`.
- **Streaming responses:** SSE (`text/event-stream`). Note: the Chat UI reads SSE over a **POST** body via `fetch` + `ReadableStream`, because the native `EventSource` API does not support POST or custom headers.
- **IDs:** UUID v4 strings.
- **Error responses:** JSON body `{"detail": "Human-readable error message"}` + appropriate HTTP status code.

## 2. Authentication

**No authentication.** aubergeRP is a single-user local deployment. All endpoints are open.

Multi-user session handling is specified in [POST-MVP.md](POST-MVP.md).

The constant `SESSION_TOKEN = "00000000-0000-0000-0000-000000000000"` is used internally wherever a per-user identifier will later plug in (e.g., image folder path). See [00 § 9](00-architecture-overview.md). This constant is **never exposed in the API**.

### API Reference

An interactive API reference (Redoc) is served at **`GET /api-docs`** and the raw OpenAPI schema at **`GET /openapi.json`**.

## 3. Health

### `GET /api/health`

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

`connected` reflects the last successful test; it is refreshed on `POST /api/connectors/{id}/test`.

---

## 4. Characters

### `GET /api/characters`

List all characters (summary view).

**Response: 200 OK**
```json
[
  {
    "id": "uuid-string",
    "name": "Character Name",
    "description": "Short description",
    "avatar_url": "/api/characters/uuid-string/avatar",
    "has_avatar": true,
    "tags": ["fantasy", "elf"],
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
]
```

### `GET /api/characters/{character_id}`

Full character details. Response shape is the internal character format (see [04 § 2](04-character-system.md)).

### `POST /api/characters`

Create a character manually.

**Request body** — `data` object as defined in [04 § 2](04-character-system.md) (no `id`, no timestamps).

**Response: 201 Created** — full character object.

### `PUT /api/characters/{character_id}`

Update an existing character. Full replacement of the `data` object.

**Response: 200 OK** — updated character object.

### `DELETE /api/characters/{character_id}`

Delete a character and its avatar.

**Response: 204 No Content**

### `GET /api/characters/{character_id}/avatar`

Return the character's avatar image.

- **200 OK** — `image/png` or `image/jpeg`.
- **404 Not Found** — no avatar set.

### `POST /api/characters/{character_id}/avatar`

Upload or replace the avatar. `multipart/form-data`, field `file`.

**Response: 200 OK**
```json
{"avatar_url": "/api/characters/uuid-string/avatar"}
```

### `POST /api/characters/import`

Import a character from a SillyTavern-compatible JSON or PNG file. `multipart/form-data`, field `file`.

**Response: 201 Created** — created character.

### `GET /api/characters/{character_id}/export/json`

Export as a SillyTavern-compatible JSON file (the internal format IS a V2 superset; see [04 § 3](04-character-system.md)).

**Response: 200 OK** — file download, `Content-Disposition: attachment`.

### `GET /api/characters/{character_id}/export/png`

Export as a PNG file with embedded metadata.

**Response: 200 OK** — file download.

### `POST /api/characters/{character_id}/duplicate`

Clone a character (new ID, avatar duplicated if present).

**Response: 201 Created** — new character.

---

## 5. Conversations

### `GET /api/conversations`

List all conversations, optionally filtered by character.

**Query parameters:** `character_id` (optional).

**Response: 200 OK**
```json
[
  {
    "id": "uuid-string",
    "character_id": "uuid-string",
    "character_name": "Character Name",
    "title": "Character Name — 2025-01-15 10:30",
    "message_count": 12,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T12:00:00Z"
  }
]
```

Titles are `"{character_name} — {YYYY-MM-DD HH:mm}"`, generated at creation time; not user-editable in MVP.

### `GET /api/conversations/{conversation_id}`

Full conversation with all messages. See [05 § 2](05-chat-and-conversations.md) for the message model.

### `POST /api/conversations`

Create a new conversation. The character's `first_mes` is automatically added as the first `assistant` message.

**Request body:**
```json
{"character_id": "uuid-string"}
```

**Response: 201 Created** — conversation object with the first message.

### `DELETE /api/conversations/{conversation_id}`

**Response: 204 No Content**

Images referenced by the conversation are **not** deleted (see [06 § 10](06-connector-system.md)).

---

## 6. Chat

### `POST /api/chat/{conversation_id}/message`

Send a user message and stream the assistant response (and any generated images) as SSE.

**Request body:**
```json
{"content": "Tell me about the enchanted forest."}
```

**Response: 200 OK** — `text/event-stream`

SSE events:

| Event | Data | Meaning |
|---|---|---|
| `token` | `{"content": "..."}` | One token of assistant text |
| `image_start` | `{"generation_id": "...", "prompt": "..."}` | Image generation has begun |
| `image_complete` | `{"generation_id": "...", "image_url": "/api/images/{session-token}/{uuid}"}` | Image generation finished successfully |
| `image_failed` | `{"generation_id": "...", "detail": "..."}` | Image generation failed; chat continues |
| `done` | `{"message_id": "...", "full_content": "...", "images": ["..."]}` | Assistant message complete and saved |
| `error` | `{"detail": "..."}` | Fatal error during streaming; partial response is **not** saved |

For each remote text-LLM call, the backend also stores usage telemetry in SQLite
(`llm_call_stats`): prompt token estimate, completion token estimate, latency,
connector metadata, success/failure, and optional error detail.

Image events are emitted inline as the backend parses image markers from the LLM output. See [05 § 7](05-chat-and-conversations.md) for the marker format and trigger mechanism.

---

## 7. Images

### `GET /api/images/{session_token}/{image_id}`

Retrieve a generated image file.

**Response:**
- **200 OK** — `image/png`.
- **404 Not Found** — image does not exist.

In the current single-user setup, `session_token` is always the constant `00000000-0000-0000-0000-000000000000`.

> Note: there is no public HTTP endpoint for triggering image generation. Image generation is invoked by `chat_service` as an in-process Python call to the active image connector. See [06 § 7](06-connector-system.md).

### `POST /api/images/cleanup`

Manually trigger deletion of old generated images.

**Request body:**
```json
{"older_than_days": 30}
```

**Response: 200 OK**
```json
{"deleted": 5}
```

`older_than_days` must be ≥ 1. Returns the count of files deleted. A background scheduler can also run this automatically (see [09 § 1](09-configuration-and-setup.md)).

---

## 8. Connectors

### `GET /api/connectors`

List all configured connectors.

**Query parameters:** `type` (optional) — `text`, `image`, `video`, `audio`.

**Response: 200 OK**
```json
[
  {
    "id": "uuid-string",
    "name": "My Ollama",
    "type": "text",
    "backend": "openai_api",
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

**Sensitive-field redaction rule:** API responses never include `api_key`. They include `api_key_set: bool` instead. The active connector for a type is derived from `config.yaml` (`active_connectors.{type}`), not stored per-connector.

### `GET /api/connectors/{connector_id}`

Full connector details (with the same redaction rule).

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

**Response: 201 Created** — the created connector (redacted).

### `PUT /api/connectors/{connector_id}`

Update a connector. Same body as POST.

If `api_key` is **omitted** from the body, the existing key is preserved. If `api_key` is included as an empty string, the key is cleared.

**Response: 200 OK** — updated connector.

### `DELETE /api/connectors/{connector_id}`

**Response: 204 No Content**

If the deleted connector was the active one for its type, `active_connectors.{type}` is cleared in `config.yaml`.

### `POST /api/connectors/{connector_id}/test`

Test the connector's connection to its backend.

**Response: 200 OK**
```json
{
  "connected": true,
  "details": {"models_available": ["llama3", "mistral"]}
}
```

Test failures return **200 OK** with `connected: false` and a `detail` string. Network or internal errors return **502 Bad Gateway**.

### `POST /api/connectors/{connector_id}/activate`

Set a connector as the active one for its type. Writes `active_connectors.{type}` in `config.yaml`.

**Response: 200 OK**
```json
{"id": "uuid-string", "type": "text", "is_active": true}
```

### `GET /api/connectors/backends`

List available connector backend types and their config schemas.

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

Return the current configuration (sensitive fields redacted).

**Response: 200 OK**
```json
{
  "app": {"host": "0.0.0.0", "port": 8000, "log_level": "INFO"},
  "user": {"name": "User"},
  "active_connectors": {"text": "uuid-string", "image": "uuid-string"}
}
```

### `PUT /api/config`

Partial update. Only provided fields are written.

**Response: 200 OK** — updated config (same shape as GET).

---

## 10. Marketplace

### `GET /api/marketplace/search`

Fetch and filter community character cards from the configured marketplace index.

**Query parameters:** `q` (optional) — search query (matches name, description, tags).

**Response: 200 OK**
```json
{
  "cards": [
    {
      "id": "string",
      "name": "Elara the Elf",
      "description": "A fantasy tavern keeper",
      "tags": ["fantasy", "elf"],
      "creator": "someone",
      "download_url": "https://...",
      "preview_url": "https://..."
    }
  ],
  "total": 1
}
```

The index URL is configured via `marketplace.index_url` in `config.yaml`. Only `http` and `https` schemes are accepted. After browsing, import a card by fetching its `download_url` and posting the result to `POST /api/characters/import`.

---

## 11. Statistics

### `GET /api/statistics`

Return aggregated usage analytics for the admin dashboard.

**Query parameters:**

- `days` (optional, default `14`, range `1..90`) — rolling window for timeline points.
- `top` (optional, default `15`, range `1..100`) — max rows returned for connector and conversation ranking tables.

**Response: 200 OK**
```json
{
  "summary": {
    "total_conversations": 12,
    "total_messages": 248,
    "llm_calls": 97,
    "successful_calls": 95,
    "failed_calls": 2,
    "success_rate": 97.9,
    "tokens_in": 184220,
    "tokens_out": 79210,
    "total_tokens": 263430,
    "avg_latency_ms": 812.4
  },
  "timeline": [
    {"date": "2026-04-20", "llm_calls": 11, "tokens_in": 22100, "tokens_out": 9400}
  ],
  "by_connector": [
    {
      "connector_id": "uuid-string",
      "name": "OpenAI Main",
      "backend": "openai_api",
      "llm_calls": 54,
      "success": 53,
      "failed": 1,
      "tokens_in": 103300,
      "tokens_out": 42100,
      "total_tokens": 145400,
      "avg_latency_ms": 745.2
    }
  ],
  "by_conversation": [
    {
      "conversation_id": "uuid-string",
      "title": "Elara — 2026-04-27 10:43",
      "message_count": 28,
      "llm_calls": 14,
      "tokens_in": 24220,
      "tokens_out": 11450,
      "total_tokens": 35670,
      "avg_latency_ms": 689.7
    }
  ],
  "generated_at": "2026-04-27T14:23:00+00:00",
  "range_days": 14
}
```

This endpoint is read-only. It does not trigger generation calls.

---

## 12. Error Response Format

All error responses:

```json
{"detail": "Human-readable error message"}
```

| Status | Usage |
|---|---|
| 400 | Bad request (invalid input, missing fields, no active connector of required type) |
| 404 | Resource not found |
| 409 | Conflict (duplicate resource) |
| 422 | Validation error (Pydantic) |
| 500 | Internal server error |
| 502 | Upstream error (LLM or image backend unreachable) |
| 504 | Upstream timeout |
