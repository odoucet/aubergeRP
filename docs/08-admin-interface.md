# 08 — Admin Interface

## 1. Overview

A separate page within aubergeRP that provides:

- **Connector management** — add, configure, test, and activate connectors for text, image, (post-MVP: video, audio).
- **Character library management** — import, edit, duplicate, export, delete.
- **System health overview.**

## 2. Technology

- Pure HTML + vanilla JavaScript (same approach as the Chat UI).
- Plain CSS, sharing base styles with the Chat UI.
- No authentication in the MVP (single-user, local).
- REST only (no SSE).

## 3. Layout

```
┌──────────────────────────────────────────────────────┐
│  Header Bar                                          │
│  aubergeRP Admin                       [← Chat]      │
├──────────┬───────────────────────────────────────────┤
│ Nav Menu │            Content Area                   │
│ ┌──────┐ │  (changes based on selected section)      │
│ │Connec│ │                                           │
│ │Chars │ │                                           │
│ │Health│ │                                           │
│ └──────┘ │                                           │
├──────────┴───────────────────────────────────────────┤
│  Status bar                                          │
└──────────────────────────────────────────────────────┘
```

The nav menu highlights the active section. Sections switch via the URL hash (e.g., `/admin/#characters`) with no page reloads.

## 4. Sections

### 4.1 Connectors

Landing page. Lists all configured connectors grouped by type.

```
┌──────────────────────────────────────────────────────┐
│  Connectors                             [+ Add New]  │
├──────────────────────────────────────────────────────┤
│  ── Text Connectors ──                               │
│  ⭐ My Ollama (openai_api)              [Test] [⋮]   │
│     URL: http://localhost:11434/v1                   │
│     Model: llama3                                    │
│     Status: ✅ Connected                             │
│                                                      │
│  ── Image Connectors ──                              │
│  ⭐ OpenRouter Images (openai_api)      [Test] [⋮]   │
│     URL: https://openrouter.ai/api/v1                │
│     Model: google/gemini-2.0-flash-exp:free          │
│     Status: ✅ Connected                             │
│                                                      │
│  ── Video Connectors ──   (no backends available)    │
│  ── Audio Connectors ──   (no backends available)    │
└──────────────────────────────────────────────────────┘
```

- ⭐ marks the active connector (derived from `config.yaml:active_connectors` — see [06 § 8](06-connector-system.md)).
- `[⋮]` menu: Edit, Activate, Delete.
- `[Test]` calls `POST /api/connectors/{id}/test`.

#### Add/Edit Connector Dialog

```
┌──────────────────────────────────────────────────────┐
│  Add New Connector                                   │
├──────────────────────────────────────────────────────┤
│  Name:     [My Ollama______________________]         │
│  Type:     [text ▼]                                  │
│  Backend:  [openai_api ▼]                            │
│                                                      │
│  ── Backend Configuration ──                         │
│  (fields change based on the selected backend)       │
│                                                      │
│  Base URL:    [http://localhost:11434/v1___]         │
│  API Key:     [•••••••••••••] (placeholder if set)   │
│  Model:       [llama3_________________________]      │
│  Max Tokens:  [1024]                                 │
│  Temperature: [0.8]                                  │
│  Timeout:     [120]                                  │
│                                                      │
│                   [Cancel] [Test] [Save]             │
└──────────────────────────────────────────────────────┘
```

Behavior:

- Changing Type updates the Backend dropdown to compatible backends.
- Changing Backend updates the config fields according to that backend's schema (fetched from `GET /api/connectors/backends`).
- On edit: the API key field shows a placeholder if one is set on the server. Leaving it empty preserves the existing key (see [03 § 8](03-backend-api.md)). A dedicated "Clear API key" checkbox sends an empty string explicitly.
- `Test` validates the connection before saving.

Feedback:
- On success: green banner (e.g., "Connected. Available models: …").
- On failure: red banner with the detail string.

### 4.2 Characters

Displays all characters in the library with management actions.

```
┌──────────────────────────────────────────────────────┐
│  Characters                          [Import] [New]  │
├──────────────────────────────────────────────────────┤
│  ┌────┐                                              │
│  │ 🧝 │  Elara the Elf              [Edit] [⋮]       │
│  │    │  Fantasy tavern keeper                       │
│  └────┘  Tags: fantasy, elf                          │
│  ────────────────────────────────────────────────────│
│  ┌────┐                                              │
│  │ 🧙 │  Grimwald the Wizard        [Edit] [⋮]       │
│  └────┘  Tags: fantasy, wizard                       │
└──────────────────────────────────────────────────────┘
```

`[⋮]` menu: Duplicate, Export as JSON, Export as PNG, Delete (with confirmation).

#### Import Dialog

- File picker for `.json` and `.png`.
- Drag-and-drop zone.
- On success: character appears in the list with a success toast.
- On failure: error detail (e.g., "Invalid character card: missing 'name' field").

#### Character Edit Form

```
┌──────────────────────────────────────────────────────┐
│  Edit Character: Elara the Elf                       │
├──────────────────────────────────────────────────────┤
│  Avatar: [🧝] [Upload New]                           │
│                                                      │
│  Name:        [Elara the Elf________________]        │
│  Description: [Full character description____]       │
│  Personality: [Warm, welcoming, wise________]        │
│  First Msg:   [Welcome to the Golden Hearth_]        │
│  Examples:    [<START>______________________]        │
│  Scenario:    [A medieval fantasy tavern____]        │
│  Sys Prompt:  [Optional override___________]         │
│  Tags:        [fantasy, elf, tavern________]         │
│                                                      │
│  ── aubergeRP Extensions ──                          │
│  Image Prompt Prefix: [elf woman, fantasy___]        │
│  Negative Prompt:     [blurry, low quality__]        │
│                                                      │
│  Creator:     [Creator name________________]         │
│  Notes:       [Creator notes_______________]         │
│                                                      │
│                              [Cancel] [Save]         │
└──────────────────────────────────────────────────────┘
```

Form rules:

- All text fields are multi-line textareas except Name, Tags, Creator.
- Tags are comma-separated in the input; stored as an array.
- Avatar upload: images only, ≤ 10 MB.
- Name and Description are required; inline validation.
- Save calls `POST /api/characters` (new) or `PUT /api/characters/{id}` (edit).

### 4.3 Health

```
┌──────────────────────────────────────────────────────┐
│  System Health                          [Refresh]    │
├──────────────────────────────────────────────────────┤
│  aubergeRP Version: 0.1.0                            │
│                                                      │
│  Active Connectors:                                  │
│  Text:  ✅ My Ollama                                 │
│         http://localhost:11434/v1                    │
│         Model: llama3                                │
│  Image: ✅ OpenRouter Images                         │
│         https://openrouter.ai/api/v1                 │
│  Video: — Not available                              │
│  Audio: — Not available                              │
│                                                      │
│  Storage:                                            │
│    Characters: 5                                     │
│    Conversations: 12                                 │
│    Images: 34                                        │
│    Connectors: 2                                     │
└──────────────────────────────────────────────────────┘
```

Data is fetched from `GET /api/health`, plus character/conversation counts from their respective list endpoints.

## 5. First-Time Setup Flow

1. Open `http://localhost:8000/admin/`.
2. Connectors section is empty.
3. Click `+ Add New` → select type `text`, backend `openai_api`.
4. Enter the LLM backend URL (e.g., `http://localhost:11434/v1` for Ollama). Click Test, then Save. The connector is automatically activated (first of its type).
5. Click `+ Add New` again → select type `image`, backend `openai_api`, enter an image API URL + key. Test + Save.
6. Go to Characters, import or create a character card.
7. Click `← Chat` to start roleplaying.

## 6. API Endpoints

The Admin UI uses the endpoints defined in [03 — Backend API](03-backend-api.md). No endpoints specific to the admin UI are defined outside that document.

## 7. Error Handling

| Scenario | Display |
|---|---|
| API unreachable | Red banner: "Cannot connect to aubergeRP API" |
| Save failed | Red inline error near the Save button with the detail |
| Import failed | Error message in the import dialog |
| Delete confirmation | Modal: "Are you sure you want to delete {name}? This cannot be undone." |
| Validation error | Red inline error next to the invalid field |
