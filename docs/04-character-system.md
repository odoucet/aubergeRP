# 04 — Character System

## 1. Overview

The character system manages:

- Character definitions (storage, retrieval).
- Import from SillyTavern-compatible formats (JSON and PNG, V1 and V2).
- Export back to SillyTavern-compatible formats.
- Providing character data to the chat service for prompt construction.

## 2. Internal Character Format

The internal format **is** SillyTavern V2 (`chara_card_v2`), extended with:

- A small wrapper for aubergeRP-specific metadata (`id`, `has_avatar`, timestamps).
- Custom fields in `data.extensions.aubergeRP.*`.

No conversion is performed on export: the character file on disk is already a valid V2 card.

### Schema

```json
{
  "id": "uuid-v4-string",
  "has_avatar": true,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",

  "spec": "chara_card_v2",
  "spec_version": "2.0",
  "data": {
    "name": "Character Name",
    "description": "Full character description. Supports {{user}} and {{char}} macros.",
    "personality": "Character personality summary.",
    "first_mes": "The first message the character sends when a conversation starts.",
    "mes_example": "<START>\n{{user}}: Hello\n{{char}}: Greetings, traveler!",
    "scenario": "The setting or scenario for the roleplay.",
    "system_prompt": "Optional system prompt override. If empty, the default is used.",
    "post_history_instructions": "Optional instructions appended after conversation history.",
    "creator": "Creator name or handle.",
    "creator_notes": "Notes from the creator.",
    "character_version": "1.0",
    "tags": ["fantasy", "elf", "tavern"],
    "extensions": {
      "aubergeRP": {
        "image_prompt_prefix": "elf woman, fantasy setting, medieval tavern",
        "negative_prompt": "blurry, low quality, deformed"
      }
    }
  }
}
```

### Top-Level Wrapper Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string (UUID) | auto | Unique identifier |
| `has_avatar` | bool | auto | Whether `data/avatars/{id}.png` exists |
| `created_at` | ISO 8601 | auto | Creation timestamp |
| `updated_at` | ISO 8601 | auto | Last update timestamp |

The avatar file path is **derived** from `id`; it is never stored in the JSON.

### `data` Fields (SillyTavern V2)

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Character display name |
| `description` | string | yes | Full character description |
| `personality` | string | no | Short personality summary |
| `first_mes` | string | no | First message for new conversations |
| `mes_example` | string | no | Example dialogue for few-shot prompting |
| `scenario` | string | no | Roleplay setting/scenario |
| `system_prompt` | string | no | Overrides default system prompt if non-empty |
| `post_history_instructions` | string | no | Appended after history in the prompt |
| `creator` | string | no | Author attribution |
| `creator_notes` | string | no | Creator's notes |
| `character_version` | string | no | Version of the character definition |
| `tags` | string[] | no | Tags for categorization |
| `extensions` | object | no | V2 extensions dict (preserved untouched) |

### aubergeRP Extensions (`data.extensions.aubergeRP`)

| Field | Type | Description |
|---|---|---|
| `image_prompt_prefix` | string | Text prepended to image generation prompts for this character |
| `negative_prompt` | string | Default negative prompt for image generation |

Other extensions from third-party tools are preserved as-is (SillyTavern ignores unknown extensions).

## 3. SillyTavern Compatibility

### 3.1 Import Formats

- **JSON V2** — `spec: "chara_card_v2"` at root, content in `data.*`.
- **JSON V1 (legacy)** — flat root: `name`, `description`, `personality`, `first_mes`, `mes_example`, `scenario`.
- **PNG V1/V2** — a PNG file with a `tEXt` chunk keyed `chara` whose value is a base64-encoded JSON card (V1 or V2).

### 3.2 Import Logic

```
Input file received
  │
  ├── .json extension?
  │    ├── has "spec": "chara_card_v2"? → parse as V2
  │    └── has "name" at root level?    → parse as V1 (legacy), upgrade to V2
  │
  └── .png extension?
       ├── read tEXt chunk with key "chara"
       ├── base64-decode the value
       └── parse the resulting JSON (V1 or V2), upgrade V1 → V2 in memory
```

V1 → V2 upgrade: move flat fields into `data.*`, set `spec: "chara_card_v2"`, `spec_version: "2.0"`.

After parsing (and upgrade if needed):
1. Generate a new UUID (`id`).
2. If a PNG image is provided, save it as `data/avatars/{id}.png` and set `has_avatar: true`.
3. Ensure `data.extensions.aubergeRP` exists (create with defaults if missing). Preserve other `extensions`.
4. Write to `data/characters/{id}.json` atomically.

### 3.3 Export Logic

Because the stored format IS a V2 card with extra wrapper fields, export strips the wrapper and writes the rest.

**JSON export:**
1. Read the character file.
2. Remove the wrapper fields (`id`, `has_avatar`, `created_at`, `updated_at`).
3. Return the remaining object (`spec`, `spec_version`, `data`) as a downloadable JSON file.

**PNG export:**
1. Produce the V2 JSON as above.
2. Base64-encode the JSON.
3. Embed it in the character's avatar PNG's `tEXt` chunk (key `chara`). If the character has no avatar, use `frontend/assets/default-avatar.png` as the carrier.
4. Return as a downloadable PNG file.

## 4. Storage

- Characters live in `data/characters/{uuid}.json`.
- Avatars live in `data/avatars/{uuid}.png` (or `.jpg`, `.webp`).
- Writes are atomic (temp file + `os.rename`).

## 5. Character Service API

The `character_service.py` module exposes these functions:

| Function | Description |
|---|---|
| `list_characters()` | Return all characters (summary view) |
| `get_character(id)` | Return full character |
| `create_character(data)` | Create from a V2 `data` object |
| `update_character(id, data)` | Update an existing character |
| `delete_character(id)` | Delete character + avatar |
| `duplicate_character(id)` | Clone with a new ID |
| `import_character_json(file)` | Import from JSON (V1 or V2) |
| `import_character_png(file)` | Import from PNG |
| `export_character_json(id)` | Export as V2 JSON |
| `export_character_png(id)` | Export as SillyTavern-compatible PNG |
| `save_avatar(id, file)` | Save/replace avatar |
| `get_avatar_path(id)` | Return filesystem path to avatar or None |

## 6. Macro System

Character fields and conversation messages support two macros, resolved at prompt-building time (in the chat service, not here):

| Macro | Replaced with |
|---|---|
| `{{char}}` | Character's `data.name` |
| `{{user}}` | User's display name from `config.yaml` (`user.name`, default `"User"`) |

## 7. Validation Rules

- `data.name` required, non-empty, 1–200 characters.
- `data.description` required, non-empty.
- `data.tags` is an array of strings, each ≤ 50 characters.
- Avatar files: PNG, JPEG, or WEBP; ≤ 10 MB.
- On import, malformed JSON or missing `name`/`description` returns **400** with a clear message.
