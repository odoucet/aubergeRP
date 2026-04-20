# 08 — Admin Interface

## 1. Overview

The Admin interface is a separate page within the AubergeLLM web application that provides:

- Configuration of external services (LLM backend, ComfyUI).
- Character library management (import, edit, duplicate, export, delete).
- Workflow management (view available workflows).
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
│  AubergeLLM Admin                       [← Chat]    │
├──────────┬───────────────────────────────────────────┤
│          │                                           │
│ Nav Menu │            Content Area                   │
│          │                                           │
│ ┌──────┐ │  (Changes based on selected section)      │
│ │Config│ │                                           │
│ │Chars │ │                                           │
│ │Wflows│ │                                           │
│ │Health│ │                                           │
│ └──────┘ │                                           │
│          │                                           │
├──────────┴───────────────────────────────────────────┤
│  Status bar                                          │
└──────────────────────────────────────────────────────┘
```

## 4. Sections

### 4.1 Configuration Section

This is the landing page of the admin interface. It allows configuring the two external services.

#### LLM Configuration

| Field | Type | Description |
|---|---|---|
| Base URL | Text input | URL of the LLM API (e.g., `http://localhost:11434/v1`) |
| Model | Dropdown / text | Model name (e.g., `llama3`). If connection is active, populate from available models |
| API Key | Password input | Optional API key |
| Max Tokens | Number input | Maximum response tokens (default: 1024) |
| Temperature | Slider / number | Generation temperature (default: 0.8, range: 0.0 - 2.0) |

**Actions:**
- "Test Connection" button → calls `POST /api/config/test-llm`.
- "Save" button → calls `PUT /api/config` with LLM fields.

**Feedback:**
- On successful test: green banner "Connected to LLM. Available models: llama3, mistral, ..."
- On failure: red banner "Cannot connect to LLM at {url}. Error: {detail}"

#### ComfyUI Configuration

| Field | Type | Description |
|---|---|---|
| Base URL | Text input | URL of ComfyUI (e.g., `http://localhost:8188`) |

**Actions:**
- "Test Connection" button → calls `POST /api/config/test-comfyui`.
- "Save" button → calls `PUT /api/config` with ComfyUI fields.

**Feedback:**
- On successful test: green banner "Connected to ComfyUI (version X.Y.Z)"
- On failure: red banner "Cannot connect to ComfyUI at {url}. Error: {detail}"

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
│  ── AubergeLLM Extensions ──                         │
│                                                      │
│  Image Prompt Prefix: [elf woman, fantasy___]        │
│  Default Workflow:    [default_t2i ▼]                │
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
- Default Workflow is a dropdown populated from `GET /api/workflows`.
- Avatar upload opens a file picker (images only, ≤ 10 MB).

**Validation:**
- Name is required.
- Description is required.
- Show inline validation errors.

**Actions:**
- "Save" → `POST /api/characters` (new) or `PUT /api/characters/{id}` (edit).
- "Cancel" → return to list view without saving.

### 4.3 Workflows Section

A read-only view of available ComfyUI workflow templates.

```
┌──────────────────────────────────────────────────────┐
│  Workflows                                           │
├──────────────────────────────────────────────────────┤
│                                                      │
│  default_t2i — Default Text-to-Image                 │
│  Generates an image from a text prompt               │
│  Inputs: prompt (string, required),                  │
│          negative_prompt (string, optional)           │
│  Output: image                                       │
│                                                      │
│  (More workflows can be added by placing files in    │
│   data/workflows/)                                   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

For MVP, workflows are not editable through the UI. They are managed by placing files in the `data/workflows/` directory.

### 4.4 Health Section

Displays system health and diagnostic information.

```
┌──────────────────────────────────────────────────────┐
│  System Health                          [Refresh]    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  AubergeLLM Version: 0.1.0                          │
│                                                      │
│  LLM Backend:                                       │
│    Status: ✅ Connected                              │
│    URL: http://localhost:11434/v1                    │
│    Model: llama3                                    │
│                                                      │
│  ComfyUI:                                           │
│    Status: ❌ Disconnected                           │
│    URL: http://localhost:8188                        │
│    Error: Connection refused                        │
│                                                      │
│  Storage:                                           │
│    Characters: 5                                    │
│    Conversations: 12                                │
│    Images: 34                                       │
│                                                      │
└──────────────────────────────────────────────────────┘
```

Data is fetched from `GET /api/health` plus `GET /api/characters` and `GET /api/conversations` counts.

## 5. User Flow — First-Time Setup

1. User opens `http://localhost:8000/admin/`.
2. Configuration section is displayed.
3. User enters LLM backend URL and clicks "Test Connection".
4. On success, the model dropdown is populated.
5. User selects a model and clicks "Save".
6. User enters ComfyUI URL and clicks "Test Connection".
7. On success, user clicks "Save".
8. User navigates to Characters section.
9. User clicks "Import" and uploads a SillyTavern character card.
10. Character appears in the list.
11. User optionally edits AubergeLLM-specific fields (image prompt prefix, etc.).
12. User clicks "← Chat" to go to the chat interface and start roleplaying.

## 6. API Integration

| Action | Endpoint | Method |
|---|---|---|
| Get config | `GET /api/config` | fetch |
| Save config | `PUT /api/config` | fetch |
| Test LLM | `POST /api/config/test-llm` | fetch |
| Test ComfyUI | `POST /api/config/test-comfyui` | fetch |
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
| List workflows | `GET /api/workflows` | fetch |
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
└── workflows.js        # Workflows section logic
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
| API unreachable | Red banner: "Cannot connect to AubergeLLM API" |
| Save failed | Red inline error near the save button with details |
| Import failed | Error message in the import dialog with details |
| Delete confirmation | Modal: "Are you sure you want to delete {name}? This cannot be undone." |
| Validation error | Red inline error next to the invalid field |
