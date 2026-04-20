# 04 — Character System

## 1. Overview

The character system is the core content management layer of AubergeLLM. It handles:

- Storing and retrieving character definitions.
- Importing characters from SillyTavern-compatible formats (JSON and PNG).
- Exporting characters back to SillyTavern-compatible formats.
- Providing character data to the chat system for prompt construction.

## 2. Internal Character Format

AubergeLLM uses its own internal JSON format which is a **superset** of the SillyTavern Tavern Character Card V2 format. The internal format includes all standard V2 fields plus AubergeLLM-specific extensions.

### Internal Character Schema

```json
{
  "id": "uuid-v4-string",
  "spec": "aubergellm-v1",
  "spec_version": "1.0",
  "data": {
    "name": "Character Name",
    "description": "Full character description. Supports {{user}} and {{char}} macros.",
    "personality": "Character personality summary.",
    "first_mes": "The first message the character sends when a conversation starts.",
    "mes_example": "Example dialogue in SillyTavern format:\n<START>\n{{user}}: Hello\n{{char}}: Greetings, traveler!",
    "scenario": "The setting or scenario for the roleplay.",
    "system_prompt": "Optional system prompt override. If empty, the default system prompt is used.",
    "post_history_instructions": "Optional instructions appended after conversation history.",
    "creator": "Creator name or handle.",
    "creator_notes": "Notes from the creator about the character.",
    "character_version": "1.0",
    "tags": ["fantasy", "elf", "tavern"],
    "extensions": {
      "aubergellm": {
        "image_prompt_prefix": "elf woman, fantasy setting, medieval tavern",
        "default_workflow": "default_t2i",
        "negative_prompt": "blurry, low quality, deformed"
      }
    }
  },
  "avatar_path": "avatars/uuid-string.png",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string (UUID) | Auto-generated | Unique identifier |
| `spec` | string | Auto | Always `"aubergellm-v1"` |
| `spec_version` | string | Auto | Format version |
| `data.name` | string | Yes | Character display name |
| `data.description` | string | Yes | Full character description, used in the prompt |
| `data.personality` | string | No | Short personality summary |
| `data.first_mes` | string | No | First message for new conversations |
| `data.mes_example` | string | No | Example dialogue for few-shot prompting |
| `data.scenario` | string | No | Roleplay setting/scenario |
| `data.system_prompt` | string | No | Overrides default system prompt if non-empty |
| `data.post_history_instructions` | string | No | Appended after history in prompt |
| `data.creator` | string | No | Author attribution |
| `data.creator_notes` | string | No | Creator's notes |
| `data.character_version` | string | No | Version of the character definition |
| `data.tags` | string[] | No | Tags for categorization |
| `data.extensions` | object | No | Extensions object (SillyTavern-compatible) |
| `data.extensions.aubergellm` | object | No | AubergeLLM-specific fields |
| `avatar_path` | string | No | Relative path to avatar image in `data/avatars/` |
| `created_at` | string (ISO 8601) | Auto | Creation timestamp |
| `updated_at` | string (ISO 8601) | Auto | Last update timestamp |

### AubergeLLM Extensions

| Field | Type | Description |
|---|---|---|
| `image_prompt_prefix` | string | Text prepended to image generation prompts for this character |
| `default_workflow` | string | ID of the default ComfyUI workflow for this character |
| `negative_prompt` | string | Default negative prompt for image generation |

## 3. SillyTavern Compatibility

### 3.1 Supported Import Formats

#### JSON Character Card (V2)

SillyTavern V2 character cards are JSON files with this structure:

```json
{
  "spec": "chara_card_v2",
  "spec_version": "2.0",
  "data": {
    "name": "...",
    "description": "...",
    "personality": "...",
    "first_mes": "...",
    "mes_example": "...",
    "scenario": "...",
    "system_prompt": "...",
    "post_history_instructions": "...",
    "creator": "...",
    "creator_notes": "...",
    "character_version": "...",
    "tags": [],
    "extensions": {}
  }
}
```

#### JSON Character Card (V1 / Legacy)

Older cards may have a flat structure:

```json
{
  "name": "...",
  "description": "...",
  "personality": "...",
  "first_mes": "...",
  "mes_example": "...",
  "scenario": "..."
}
```

#### PNG Character Card

PNG files with character data embedded in the `tEXt` chunk with keyword `chara`. The value is a **Base64-encoded JSON string** containing the character card in V1 or V2 format.

### 3.2 Import Logic

```
Input file received
    │
    ├── .json extension?
    │   ├── Has "spec": "chara_card_v2"? → Parse as V2
    │   └── Has "name" at root level? → Parse as V1 (legacy)
    │
    └── .png extension?
        ├── Read tEXt chunk with key "chara"
        ├── Base64 decode the value
        └── Parse the resulting JSON (V1 or V2)
```

For both V1 and V2 imports:
1. Map all recognized fields to the internal format.
2. Generate a new UUID.
3. If the PNG has an image, save it as the avatar.
4. Set `spec` to `"aubergellm-v1"`.
5. Preserve any existing `extensions` (including non-AubergeLLM ones).
6. Add default `extensions.aubergellm` fields if not present.
7. Save to `data/characters/{uuid}.json`.

### 3.3 Export Logic

#### JSON Export

1. Convert internal format to SillyTavern V2 format.
2. Remove AubergeLLM-specific metadata (`id`, `avatar_path`, `created_at`, `updated_at`).
3. Set `spec` to `"chara_card_v2"` and `spec_version` to `"2.0"`.
4. Preserve `extensions` including `aubergellm` (SillyTavern ignores unknown extensions).
5. Return as downloadable JSON file.

#### PNG Export

1. Generate the V2 JSON (same as JSON export).
2. Base64-encode the JSON.
3. Embed it in the avatar PNG's `tEXt` chunk with key `chara`.
4. If no avatar exists, use a default placeholder image.
5. Return as downloadable PNG file.

## 4. Storage

- Characters are stored as individual JSON files in `data/characters/`.
- File name: `{uuid}.json`.
- Avatars are stored in `data/avatars/` as `{uuid}.png` (or `.jpg`).
- The character JSON references its avatar via the `avatar_path` field.

## 5. Character Service API

The `character_service.py` module exposes these functions:

| Function | Description |
|---|---|
| `list_characters()` | Return all characters (summary view) |
| `get_character(id)` | Return full character by ID |
| `create_character(data)` | Create a new character from provided data |
| `update_character(id, data)` | Update an existing character |
| `delete_character(id)` | Delete a character and its avatar |
| `duplicate_character(id)` | Clone a character with a new ID |
| `import_character_json(file)` | Import from JSON file |
| `import_character_png(file)` | Import from PNG file |
| `export_character_json(id)` | Export as SillyTavern V2 JSON |
| `export_character_png(id)` | Export as SillyTavern-compatible PNG |
| `save_avatar(id, file)` | Save/replace avatar image |
| `get_avatar_path(id)` | Get filesystem path to avatar |

## 6. Macro System

Character fields support the following macros, which are resolved at prompt-building time:

| Macro | Replaced with |
|---|---|
| `{{char}}` | Character's `name` |
| `{{user}}` | User's display name (from config, default: `"User"`) |

Macro replacement happens in the chat service, not in the character service.

## 7. Validation Rules

- `name` is required and must be non-empty (1-200 characters).
- `description` is required and must be non-empty.
- `tags` must be an array of strings, each ≤ 50 characters.
- All text fields have a maximum length of 50,000 characters.
- Avatar files must be valid images (PNG, JPEG, WEBP) and ≤ 10 MB.
- On import, malformed JSON or missing required fields result in a 400 error with a clear message.
