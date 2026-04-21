# 08 — Admin Interface

## 1. Overview

The Admin interface is a separate page within the aubergeRP web application that provides:

- **Connector management** — add, configure, test, and switch between connectors for text, image, video, and audio.
- Character library management (import, edit, duplicate, export, delete).
- System health overview.

## 2. Technology

- **Pure HTML + vanilla JavaScript** — same approach as the Chat UI.
- **CSS** — plain CSS, shares some base styles with the Chat UI.
- **No authentication** — single-user, local deployment (MVP).
- **REST API only** — no SSE needed for admin operations.

## 3. Layout

```
┌──────────────────────────────────────────────────────┐
│  Header Bar                                          │
│  aubergeRP Admin                       [← Chat]    │
├──────────┬───────────────────────────────────────────┤
│          │                                           │
│ Nav Menu │            Content Area                   │
│          │                                           │
│ ┌──────┐ │  (Changes based on selected section)      │
│ │Connec│ │                                           │
│ │Chars │ │                                           │
│ │Health│ │                                           │
│ └──────┘ │                                           │
│          │                                           │
├──────────┴───────────────────────────────────────────┤
│  Status bar                                          │
└──────────────────────────────────────────────────────┘
```

## 4. Sections

### 4.1 Connectors Section

This is the landing page of the admin interface. It shows all configured connectors organized by type, and allows adding, editing, testing, and activating connectors.

#### Layout

```
┌──────────────────────────────────────────────────────┐
│  Connectors                             [+ Add New]  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ── Text Connectors ──                               │
│                                                      │
│  ⭐ My Ollama (openai_api)              [Test] [⋮]  │
│     URL: http://localhost:11434/v1                    │
│     Model: llama3                                    │
│     Status: ✅ Connected                             │
│                                                      │
│  ── Image Connectors ──                              │
│                                                      │
│  ⭐ OpenRouter Images (openai_api)      [Test] [⋮]  │
│     URL: https://openrouter.ai/api/v1               │
│     Model: google/gemini-2.0-flash-exp:free          │
│     Status: ✅ Connected                             │
│                                                      │
│  ── Video Connectors ──                              │
│     (No connectors configured)                       │
│                                                      │
│  ── Audio Connectors ──                              │
│     (No connectors configured)                       │
│                                                      │
└──────────────────────────────────────────────────────┘
```

- ⭐ indicates the active connector for that type.
- The `[⋮]` overflow menu contains: Edit, Activate, Deactivate, Delete.
- "Test" button → calls `POST /api/connectors/{id}/test`.

#### Add/Edit Connector Dialog

```
┌──────────────────────────────────────────────────────┐
│  Add New Connector                                   │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Name:     [My Ollama______________________]         │
│  Type:     [text ▼]                                  │
│  Backend:  [openai_api ▼]                            │
│                                                      │
│  ── Backend Configuration ──                         │
│  (fields change based on selected backend)           │
│                                                      │
│  Base URL:    [http://localhost:11434/v1___]          │
│  API Key:     [________________________________]     │
│  Model:       [llama3_________________________]      │
│  Max Tokens:  [1024]                                 │
│  Temperature: [0.8]                                  │
│  Timeout:     [120]                                  │
│                                                      │
│                   [Cancel] [Test] [Save]             │
└──────────────────────────────────────────────────────┘
```

**Field behavior:**
- When "Type" changes, the "Backend" dropdown updates to show only compatible backends.
- When "Backend" changes, the configuration fields update to match the backend's schema.
- "Test" validates the connection before saving.
- For image connectors with `openai_api` backend, fields are: Base URL, API Key, Model, Size, Quality, Timeout.

**Feedback:**
- On successful test: green banner "Connected. Available models: ..."
- On failure: red banner "Cannot connect: {detail}"

### 4.2 Characters Section

Displays a table/grid of all characters in the library with management actions.

#### Character List View

```
┌──────────────────────────────────────────────────────┐
│  Characters                           [Import] [New] │
├──────────────────────────────────────────────────────┤
│  ┌────┐                                             │
│  │ 🧝 │  Elara the Elf            [Edit] [⋮]       │
│  │    │  Fantasy tavern keeper                      │
│  └────┘  Tags: fantasy, elf                         │
│  ───────────────────────────────────────────────────│
│  ┌────┐                                             │
│  │ 🧙 │  Grimwald the Wizard      [Edit] [⋮]       │
│  │    │  Ancient wizard of the tower                │
│  └────┘  Tags: fantasy, wizard                      │
│  ───────────────────────────────────────────────────│
│  (empty state: "No characters yet. Import or        │
│   create your first character!")                     │
└──────────────────────────────────────────────────────┘
```

The `[⋮]` overflow menu contains:
- Duplicate
- Export as JSON
- Export as PNG
- Delete (with confirmation)

#### Import Dialog

Triggered by the "Import" button.

- File picker accepting `.json` and `.png` files.
- Drag-and-drop zone.
- On successful import: character appears in the list, success toast.
- On failure: error message with details (e.g., "Invalid character card: missing 'name' field").

#### Character Edit Form

Triggered by "Edit" or "New" button.

```
┌──────────────────────────────────────────────────────┐
│  Edit Character: Elara the Elf                       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Avatar: [🧝] [Upload New]                           │
│                                                      │
│  Name:        [Elara the Elf________________]        │
│  Description: [Full character description____]       │
│               [_____________________________]        │
│  Personality: [Warm, welcoming, wise________]        │
│  First Msg:   [Welcome to the Golden Hearth_]        │
│               [_____________________________]        │
│  Examples:    [<START>______________________]        │
│               [_____________________________]        │
│  Scenario:    [A medieval fantasy tavern____]        │
│               [_____________________________]        │
│  Sys Prompt:  [Optional override___________]        │
│               [_____________________________]        │
│  Tags:        [fantasy, elf, tavern________]        │
│                                                      │
│  ── aubergeRP Extensions ──                         │
│                                                      │
│  Image Prompt Prefix: [elf woman, fantasy___]        │
│  Negative Prompt:     [blurry, low quality__]        │
│                                                      │
│  Creator:     [Creator name________________]        │
│  Notes:       [Creator notes_______________]        │
│                                                      │
│                              [Cancel] [Save]         │
└──────────────────────────────────────────────────────┘
```

**Fields:**
- All text fields are multi-line textareas except Name, Tags, Creator.
- Tags are comma-separated in the input, stored as an array.
- Avatar upload opens a file picker (images only, ≤ 10 MB).

**Validation:**
- Name is required.
- Description is required.
- Show inline validation errors.

**Actions:**
- "Save" → `POST /api/characters` (new) or `PUT /api/characters/{id}` (edit).
- "Cancel" → return to list view without saving.

### 4.3 Health Section

Displays system health and diagnostic information.

```
┌──────────────────────────────────────────────────────┐
│  System Health                          [Refresh]    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  aubergeRP Version: 0.1.0                          │
│                                                      │
│  Active Connectors:                                 │
│                                                      │
│  Text:  ✅ My Ollama                                │
│         http://localhost:11434/v1                    │
│         Model: llama3                               │
│                                                      │
│  Image: ✅ OpenRouter Images                        │
│         https://openrouter.ai/api/v1                │
│         Model: google/gemini-2.0-flash-exp:free     │
│                                                      │
│  Video: — Not configured                            │
│  Audio: — Not configured                            │
│                                                      │
│  Storage:                                           │
│    Characters: 5                                    │
│    Conversations: 12                                │
│    Images: 34                                       │
│    Connectors: 2                                    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

Data is fetched from `GET /api/health` plus `GET /api/characters` and `GET /api/conversations` counts.

## 5. User Flow — First-Time Setup

1. User opens `http://localhost:8000/admin/`.
2. Connectors section is displayed (empty).
3. User clicks "+ Add New" to create a text connector.
4. User selects type "text", backend "openai_api".
5. User enters the LLM backend URL (e.g., `http://localhost:11434/v1` for Ollama).
6. User clicks "Test" to verify the connection.
7. On success, user clicks "Save". The connector is automatically activated.
8. User clicks "+ Add New" again to create an image connector.
9. User selects type "image", backend "openai_api".
10. User enters the image API URL (e.g., `https://openrouter.ai/api/v1`) and API key.
11. User tests and saves.
12. User navigates to Characters section.
13. User clicks "Import" and uploads a SillyTavern character card.
14. Character appears in the list.
15. User optionally edits aubergeRP-specific fields (image prompt prefix, etc.).
16. User clicks "← Chat" to go to the chat interface and start roleplaying.

## 6. API Integration

| Action | Endpoint | Method |
|---|---|---|
| List connectors | `GET /api/connectors` | fetch |
| Get connector | `GET /api/connectors/{id}` | fetch |
| Create connector | `POST /api/connectors` | fetch |
| Update connector | `PUT /api/connectors/{id}` | fetch |
| Delete connector | `DELETE /api/connectors/{id}` | fetch |
| Test connector | `POST /api/connectors/{id}/test` | fetch |
| Activate connector | `POST /api/connectors/{id}/activate` | fetch |
| List backends | `GET /api/connectors/backends` | fetch |
| Get config | `GET /api/config` | fetch |
| Save config | `PUT /api/config` | fetch |
| List characters | `GET /api/characters` | fetch |
| Get character | `GET /api/characters/{id}` | fetch |
| Create character | `POST /api/characters` | fetch |
| Update character | `PUT /api/characters/{id}` | fetch |
| Delete character | `DELETE /api/characters/{id}` | fetch |
| Duplicate character | `POST /api/characters/{id}/duplicate` | fetch |
| Import character | `POST /api/characters/import` | fetch (multipart) |
| Export JSON | `GET /api/characters/{id}/export/json` | fetch (download) |
| Export PNG | `GET /api/characters/{id}/export/png` | fetch (download) |
| Upload avatar | `POST /api/characters/{id}/avatar` | fetch (multipart) |
| Health check | `GET /api/health` | fetch |

## 7. File Structure

```
frontend/admin/
└── index.html          # Admin page (single page with JS sections)

frontend/css/
└── admin.css           # Admin-specific styles

frontend/js/admin/
├── config.js           # Configuration section logic
├── characters.js       # Character management logic
└── connectors.js       # Connector management logic
```

## 8. Navigation

- The Admin UI is a single HTML page (`/admin/index.html`).
- Sections are shown/hidden via JavaScript (no page reloads).
- The nav menu highlights the active section.
- URL hash is used for direct linking (e.g., `/admin/#characters`).
- "← Chat" link navigates to `/index.html`.

## 9. Error Handling

| Scenario | Display |
|---|---|
| API unreachable | Red banner: "Cannot connect to aubergeRP API" |
| Save failed | Red inline error near the save button with details |
| Import failed | Error message in the import dialog with details |
| Delete confirmation | Modal: "Are you sure you want to delete {name}? This cannot be undone." |
| Validation error | Red inline error next to the invalid field |
