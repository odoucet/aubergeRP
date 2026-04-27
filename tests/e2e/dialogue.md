# aubergeRP UI Test Dialogue

This file is the single source of truth for the iterative UI autotest robot.
Each **Scenario** block is parsed and executed sequentially by `autotest.js`.

## Syntax

Each scenario is delimited by a `## Scenario:` heading.
Steps are bullet points with the form `- ACTION: args`.

| Action | Arguments | Description |
|---|---|---|
| `NAVIGATE` | `<url>` | Go to a URL (relative or absolute) |
| `EXPECT_TITLE` | `<text>` | Assert page title contains text |
| `EXPECT_VISIBLE` | `<selector>` | Assert element is visible |
| `EXPECT_NOT_VISIBLE` | `<selector>` | Assert element does not exist or is hidden |
| `EXPECT_TEXT` | `<selector> \| <text>` | Assert element contains text |
| `EXPECT_ATTR` | `<selector> \| <attr> \| <value>` | Assert element attribute value |
| `CLICK` | `<selector>` | Click an element |
| `FILL` | `<selector> \| <text>` | Fill an input or textarea |
| `PRESS` | `<selector> \| <key>` | Press a key while focused on element |
| `WAIT_FOR` | `<selector>` | Wait until element appears (up to 8 s) |
| `SET_VIEWPORT` | `WIDTHxHEIGHT` | Resize the browser viewport (e.g. `375x812` for mobile) |
| `WAIT_MS` | `<ms>` | Pause for a fixed duration |
| `SCREENSHOT` | `<label>` | Capture a screenshot (for reference) |

---

## Scenario: Home Page Loads

The main chat page should render all structural elements even with no data.

- NAVIGATE: /
- EXPECT_TITLE: aubergeRP
- EXPECT_VISIBLE: #header
- EXPECT_VISIBLE: #sidebar
- EXPECT_VISIBLE: #chat-area
- EXPECT_VISIBLE: #statusbar
- EXPECT_VISIBLE: #empty-state
- EXPECT_NOT_VISIBLE: #char-header
- EXPECT_NOT_VISIBLE: #message-list
- EXPECT_NOT_VISIBLE: #input-area
- SCREENSHOT: home-initial-state

---

## Scenario: Sidebar Has Characters and Conversations Sections

The sidebar must always show both sections with their headings.

- NAVIGATE: /
- EXPECT_VISIBLE: #sidebar
- EXPECT_TEXT: #sidebar | Characters
- EXPECT_TEXT: #sidebar | Conversations
- EXPECT_VISIBLE: #new-conv-btn

---

## Scenario: Status Bar Connector Indicators

The footer status bar should show all four connector status items.

- NAVIGATE: /
- EXPECT_VISIBLE: #status-text
- EXPECT_VISIBLE: #status-image
- EXPECT_VISIBLE: #status-video
- EXPECT_VISIBLE: #status-audio
- SCREENSHOT: statusbar

---

## Scenario: Admin Page Loads

The admin panel must be reachable from the main page and render its sections.

- NAVIGATE: /admin/
- EXPECT_TITLE: aubergeRP — Admin
- EXPECT_VISIBLE: #admin-nav
- EXPECT_VISIBLE: #admin-content
- EXPECT_VISIBLE: #statusbar
- SCREENSHOT: admin-initial

---

## Scenario: Admin Navigation Tabs

Clicking each nav tab must show the correct section and hide others.

- NAVIGATE: /admin/
- CLICK: .nav-btn[data-section="connectors"]
- EXPECT_VISIBLE: #section-connectors
- EXPECT_NOT_VISIBLE: #section-characters
- EXPECT_NOT_VISIBLE: #section-health
- CLICK: .nav-btn[data-section="characters"]
- EXPECT_VISIBLE: #section-characters
- EXPECT_NOT_VISIBLE: #section-connectors
- CLICK: .nav-btn[data-section="health"]
- EXPECT_VISIBLE: #section-health
- EXPECT_NOT_VISIBLE: #section-connectors
- SCREENSHOT: admin-health-section

---

## Scenario: Admin Connectors List Renders

The Connectors section must load without a JS crash (even if list is empty).

- NAVIGATE: /admin/#connectors
- WAIT_FOR: #connector-list
- EXPECT_VISIBLE: #connector-list
- EXPECT_VISIBLE: #add-connector-btn
- SCREENSHOT: admin-connectors

---

## Scenario: Add Connector Dialog Opens and Closes

Clicking "Add New" must open the connector dialog; Cancel must close it.

- NAVIGATE: /admin/#connectors
- WAIT_FOR: #add-connector-btn
- CLICK: #add-connector-btn
- WAIT_FOR: #connector-dialog
- EXPECT_VISIBLE: #connector-dialog
- EXPECT_VISIBLE: #conn-name
- EXPECT_VISIBLE: #conn-type
- EXPECT_VISIBLE: #conn-backend
- SCREENSHOT: connector-dialog-open
- CLICK: #connector-dialog-cancel
- EXPECT_NOT_VISIBLE: #connector-dialog

---

## Scenario: Add Connector Dialog Close Button Works

The ✕ button on the dialog header must also close the dialog.

- NAVIGATE: /admin/#connectors
- WAIT_FOR: #add-connector-btn
- CLICK: #add-connector-btn
- WAIT_FOR: #connector-dialog
- CLICK: #connector-dialog-close
- EXPECT_NOT_VISIBLE: #connector-dialog

---

## Scenario: Admin Characters Section Renders

The Characters section must load with Import and New buttons.

- NAVIGATE: /admin/#characters
- WAIT_FOR: #character-list
- EXPECT_VISIBLE: #character-list
- EXPECT_VISIBLE: #import-char-btn
- EXPECT_VISIBLE: #new-char-btn
- SCREENSHOT: admin-characters

---

## Scenario: New Character Dialog Opens

Clicking "New" in the Characters section must open the character edit dialog.

- NAVIGATE: /admin/#characters
- WAIT_FOR: #new-char-btn
- CLICK: #new-char-btn
- WAIT_FOR: #char-dialog
- EXPECT_VISIBLE: #char-dialog
- EXPECT_VISIBLE: #char-name
- EXPECT_VISIBLE: #char-description
- EXPECT_VISIBLE: #char-dialog-save
- SCREENSHOT: new-character-dialog

---

## Scenario: New Character Form Validation — Empty Name

Saving a character without a name must show a validation error, not crash.

- NAVIGATE: /admin/#characters
- WAIT_FOR: #new-char-btn
- CLICK: #new-char-btn
- WAIT_FOR: #char-dialog
- CLICK: #char-dialog-save
- EXPECT_VISIBLE: #char-name-error

---

## Scenario: New Character Dialog Closes on Cancel

The Cancel button must close the character dialog.

- NAVIGATE: /admin/#characters
- WAIT_FOR: #new-char-btn
- CLICK: #new-char-btn
- WAIT_FOR: #char-dialog
- CLICK: #char-dialog-cancel
- EXPECT_NOT_VISIBLE: #char-dialog

---

## Scenario: Import Character Dialog Opens

Clicking "Import" in Characters must open the import dialog with a drop zone.

- NAVIGATE: /admin/#characters
- WAIT_FOR: #import-char-btn
- CLICK: #import-char-btn
- WAIT_FOR: #import-dialog
- EXPECT_VISIBLE: #import-dialog
- EXPECT_VISIBLE: #import-drop-zone
- SCREENSHOT: import-dialog

---

## Scenario: Import Dialog Closes on Cancel

The Cancel button must close the import dialog.

- NAVIGATE: /admin/#characters
- WAIT_FOR: #import-char-btn
- CLICK: #import-char-btn
- WAIT_FOR: #import-dialog
- CLICK: #import-dialog-cancel
- EXPECT_NOT_VISIBLE: #import-dialog

---

## Scenario: Admin Health Section Loads

The Health section must render without a JS crash (API may not be available).

- NAVIGATE: /admin/#health
- WAIT_FOR: #section-health
- CLICK: .nav-btn[data-section="health"]
- WAIT_FOR: #health-content
- EXPECT_VISIBLE: #health-content
- SCREENSHOT: admin-health

---

## Scenario: Create Character and Chat Flow

End-to-end flow: create a character, select it in the chat, start a conversation,
send a message, and verify the UI handles the result (error expected if no LLM
connector is configured).

- NAVIGATE: /admin/#characters
- WAIT_FOR: #new-char-btn
- CLICK: #new-char-btn
- WAIT_FOR: #char-dialog
- FILL: #char-name | TestBot
- FILL: #char-description | A test character created by the autotest robot.
- CLICK: #char-dialog-save
- WAIT_FOR: .char-card
- SCREENSHOT: character-created
- NAVIGATE: /
- WAIT_FOR: #char-list li[role="button"]
- CLICK: #char-list li[role="button"]
- WAIT_FOR: #input-area
- EXPECT_VISIBLE: #char-header
- EXPECT_VISIBLE: #message-list
- EXPECT_VISIBLE: #input-area
- SCREENSHOT: chat-with-character
- FILL: #msg-input | Hello, how are you?
- CLICK: #send-btn
- WAIT_FOR: .msg.user
- EXPECT_VISIBLE: .msg.user
- WAIT_MS: 5000
- SCREENSHOT: after-send

---

## Scenario: Hamburger Menu Toggles Sidebar (Mobile View)

At narrow viewport the hamburger button must open/close the sidebar.

- SET_VIEWPORT: 375x812
- NAVIGATE: /
- EXPECT_VISIBLE: #hamburger-btn
- CLICK: #hamburger-btn
- WAIT_MS: 300
- SCREENSHOT: sidebar-open
- CLICK: #hamburger-btn
- WAIT_MS: 300
- SCREENSHOT: sidebar-closed

---

## Scenario: Admin Link in Header

The Admin link in the chat header must navigate to the admin page.

- NAVIGATE: /
- CLICK: a.admin-link
- EXPECT_TITLE: aubergeRP — Admin
- SCREENSHOT: navigate-to-admin

---

## Scenario: Back to Chat Link in Admin Header

The "← Chat" link in the admin header must navigate back to the chat page.

- NAVIGATE: /admin/
- CLICK: a.chat-link
- EXPECT_TITLE: aubergeRP
- SCREENSHOT: navigate-back-to-chat

---

## Scenario: First Connector Auto-Activates (Sprint 12)

Adding the first connector of a type should automatically make it active
without requiring an explicit "Activate" click.

- NAVIGATE: /admin/#connectors
- WAIT_FOR: #add-connector-btn
- CLICK: #add-connector-btn
- WAIT_FOR: #connector-dialog
- FILL: #conn-name | Sprint12 TextBot
- CLICK: #connector-dialog-save
- WAIT_FOR: .connector-card
- EXPECT_TEXT: .connector-card | Active
- SCREENSHOT: first-connector-auto-activated

---

## Scenario: Health Connector Status Null Before Test (Sprint 12)

Before any connection test is run the health panel must not show "Connected"
or "Disconnected" — the status must be absent or shown as unknown.

- NAVIGATE: /admin/#health
- WAIT_FOR: #section-health
- CLICK: .nav-btn[data-section="health"]
- WAIT_FOR: #health-content
- EXPECT_NOT_VISIBLE: .health-status-connected
- SCREENSHOT: health-status-null-before-test
