# 07 — Frontend Chat UI

## 1. Overview

The Chat UI is the primary user-facing interface of aubergeRP. It provides:

- Character selection from the library.
- Conversation management (create, switch, delete).
- Real-time chat with streamed LLM responses.
- Image generation (triggered automatically by the LLM) and inline display.
- A clean, responsive layout.

## 1.1 Multi-User Isolation

The Chat UI supports multiple concurrent users from different browsers — there is no login, but users are isolated by their session token:

- Each browser session has its own **unique session token** (stored in `localStorage` and tied to a session file on the server — see [03 — Backend API](03-backend-api.md) § 2).
- Each user's conversation list is stored in `localStorage` — the frontend only shows conversations belonging to the current session token.
- **Shareable conversation links:** A user can share a conversation URL (e.g., `http://localhost:8000/?conversation=<uuid>`) with another user. The recipient can view the conversation in **read-only** mode without needing the original session token — this is intentional for sharing purposes.

## 2. Technology

- **Pure HTML + vanilla JavaScript** — no framework, no build step.
- **CSS** — plain CSS, responsive design with media queries.
- **Libraries** — `marked.js` (vendored) for Markdown rendering in messages.
- **APIs** — `fetch` for REST calls, `EventSource` for SSE streaming.

## 3. Layout

```
┌──────────────────────────────────────────────────────┐
│  Header Bar                                    [⚙]  │
│  aubergeRP                              [Admin]     │
├──────────┬───────────────────────────────────────────┤
│          │                                           │
│ Sidebar  │            Chat Area                      │
│          │                                           │
│ [Chars]  │  ┌─────────────────────────────────────┐  │
│          │  │ Character avatar + name              │  │
│ ┌──────┐ │  ├─────────────────────────────────────┤  │
│ │Char 1│ │  │                                     │  │
│ │Char 2│ │  │ Message bubbles                     │  │
│ │Char 3│ │  │ (scrollable)                        │  │
│ │      │ │  │                                     │  │
│ │      │ │  │  [User message]                     │  │
│ │      │ │  │        [Assistant message]           │  │
│ │      │ │  │  [User message]                     │  │
│ │      │ │  │        [Assistant message + image]   │  │
│ │      │ │  │                                     │  │
│ └──────┘ │  └─────────────────────────────────────┘  │
│          │  ┌─────────────────────────────────────┐  │
│ [Convs]  │  │ Message input                  [Send]  │  │
│          │  └─────────────────────────────────────┘  │
│ ┌──────┐ │                                           │
│ │Conv 1│ │                                           │
│ │Conv 2│ │                                           │
│ │+ New │ │                                           │
│ └──────┘ │                                           │
├──────────┴───────────────────────────────────────────┤
│  Status bar: Text ✓ | Image ✓ | Video — | Audio —  │
└──────────────────────────────────────────────────────┘
```

## 4. Components

### 4.1 Header Bar

- Application name/logo on the left.
- Link to Admin UI on the right.
- Settings gear icon (optional, links to admin).

### 4.2 Sidebar

The sidebar has two sections, togglable:

#### Characters Section
- List of all available characters with avatars and names.
- Clicking a character shows their conversations or starts a new one.
- Visual indicator for the currently selected character.

#### Conversations Section
- List of conversations for the selected character.
- Each item shows: conversation title (or date), message count.
- "New Conversation" button at the top.
- Click to switch conversations.
- Delete button (with confirmation) on each conversation.

### 4.3 Chat Area

#### Chat Header
- Character avatar (small) and name.
- Current conversation title or "New Conversation".

#### Message List
- Scrollable container for messages.
- Auto-scrolls to bottom on new messages.
- User messages aligned right, assistant messages aligned left.
- Messages are rendered as Markdown (using `marked.js`).
- Images displayed inline within assistant messages.
- Timestamps shown on hover (optional).
- Typing indicator (animated dots) while LLM is generating.

#### Input Area
- Multi-line text input (textarea, auto-expanding).
- "Send" button.
- Send on Enter (Shift+Enter for new line).
- Disabled while LLM is generating.

> **Note:** Image generation is triggered automatically by the LLM when the user requests it conversationally (e.g., "please send me a picture"). There is no dedicated "Generate Image" button — the backend handles generation as part of the normal chat flow.

### 4.4 Status Bar

- Shows connection status for each active connector type (text, image, video, audio).
- Green checkmark if connected, red X if disconnected, dash if no connector configured.
- Polls `/api/health` periodically (every 30 seconds).

## 5. User Flows

### 5.1 First-Time User

1. User opens `http://localhost:8000`.
2. Sidebar shows available characters (empty if none imported).
3. Status bar shows connection status (may show disconnected).
4. If no characters exist, a message in the chat area says: "No characters available. Import characters in the Admin panel."
5. A prominent link to the Admin UI is shown.

### 5.2 Starting a Conversation

1. User clicks a character in the sidebar.
2. If no conversations exist for this character, a new one is created automatically.
3. The character's `first_mes` appears as the first message.
4. User can type and send a message.

### 5.3 Sending a Message

1. User types a message and clicks Send (or presses Enter).
2. The user message appears immediately in the chat (optimistic UI).
3. A typing indicator appears for the assistant.
4. SSE connection is opened to stream the response.
5. Tokens appear in real-time in the assistant message bubble.
6. On `done` event, the typing indicator is removed and the message is finalized.
7. On `error` event, an error message is displayed below the last message.

### 5.4 Image Generation (LLM-Triggered)

Image generation is **not** triggered by a dedicated button. Instead, it happens automatically when the user makes a conversational request:

1. User sends a message like "please send me a picture of the forest" via the normal chat input.
2. The backend sends the message to the LLM, which interprets the request.
3. The backend detects that image generation is needed and triggers it internally using the internal token.
4. A progress indicator appears in the chat (e.g., "Generating image... 45%").
5. Progress is updated via polling `GET /api/generate/image/{id}/status`.
6. When complete, the image is displayed inline in the chat as part of the assistant's response.
7. The image message is saved to the conversation.

> **Note:** The frontend never calls `POST /api/generate/image` directly — that endpoint requires an internal-only token. All generation is mediated by the backend through the standard chat endpoint.

### 5.5 Switching Conversations

1. User clicks a different conversation in the sidebar.
2. The chat area loads the selected conversation's messages.
3. All messages (including images) are displayed.

## 6. API Integration

### REST Calls (via `api.js`)

| Action | Endpoint | Method |
|---|---|---|
| List characters | `GET /api/characters` | fetch |
| List conversations | `GET /api/conversations?character_id=...` | fetch |
| Get conversation | `GET /api/conversations/{id}` | fetch |
| Create conversation | `POST /api/conversations` | fetch |
| Delete conversation | `DELETE /api/conversations/{id}` | fetch |
| Generate image | `POST /api/chat/{id}/generate-image` | fetch |
| Check generation status | `GET /api/generate/image/{id}/status` | fetch (polling) |
| Health check | `GET /api/health` | fetch (periodic) |

### SSE Streaming (via `chat.js`)

For sending a chat message:

```javascript
const eventSource = new EventSource(/* not applicable for POST */);
```

Since `EventSource` only supports GET, the chat message is sent via a POST request, and the response is read as a streaming response using `fetch` with a `ReadableStream`:

```javascript
const response = await fetch(`/api/chat/${conversationId}/message`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ content: message })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
// Read SSE events from the stream...
```

## 7. Responsive Design

### Desktop (≥ 1024px)
- Sidebar visible, 280px wide.
- Chat area fills remaining width.

### Tablet (768px - 1023px)
- Sidebar collapsible, toggled via hamburger menu.
- Chat area fills full width when sidebar is hidden.

### Mobile (< 768px)
- Sidebar is an overlay/drawer.
- Chat area is full width.
- Input area is fixed to bottom.

## 8. Accessibility

- Semantic HTML (`<main>`, `<nav>`, `<article>`, `<section>`).
- ARIA labels for buttons and interactive elements.
- Keyboard navigation: Tab between sidebar and chat, Enter to send.
- Sufficient color contrast (WCAG AA).
- Alt text for character avatars and generated images.

## 9. Error States

| State | Display |
|---|---|
| No characters | "No characters available. Go to Admin to import characters." |
| Text connector disconnected | Status bar red; sending a message shows inline error |
| No image connector | Status bar dash; image generation button disabled with tooltip |
| Image connector disconnected | Status bar red; image generation button disabled with tooltip |
| LLM error during streaming | Error message below the last message, option to retry |
| Image generation failed | Error message where the image would appear |
| Network error | Toast/banner notification at the top |

## 10. File Structure

```
frontend/
├── index.html          # Main chat page
├── css/
│   └── main.css        # All chat UI styles
├── js/
│   ├── api.js          # API client wrapper
│   ├── chat.js         # Chat logic, SSE handling, message rendering
│   ├── characters.js   # Character list logic
│   ├── images.js       # Image generation UI logic
│   └── vendor/
│       └── marked.min.js
└── assets/
    ├── logo.svg
    └── default-avatar.png
```
