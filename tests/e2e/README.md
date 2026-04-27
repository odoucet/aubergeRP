# aubergeRP UI Autotest Robot

Iterative functional-test robot built with [Playwright](https://playwright.dev).

It reads a human-readable test dialogue from `dialogue.md`, executes every
scenario against a running aubergeRP instance, and **automatically opens a
GitHub Issue** (assigned to Copilot) for every UI bug it finds.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Node.js | ≥ 18 | `node --version` |
| `gh` CLI | any | `gh auth login` required for issue creation |
| Chromium | — | installed by the `install-browsers` script below |
| aubergeRP server | running | default `http://localhost:8123` |

---

## Quick Start

```bash
# 1. Start the aubergeRP server (in a separate terminal)
make run

# 2. Install Node deps and Chromium
cd tests/e2e
npm ci
npm run install-browsers

# 3. Authenticate the GitHub CLI (once)
gh auth login

# 4. Run the robot
node autotest.js
```

On completion the robot prints a summary and creates a GitHub Issue for every
bug found, assigning it to Copilot for automated remediation.

---

## Options

```
node autotest.js [options]

Options:
  --base-url <url>   Base URL of the server  (default: http://localhost:8123)
  --no-issues        Skip GitHub issue creation (dry-run)
  --headless false   Show the browser window

Environment variables (override CLI flags):
  BASE_URL           Server base URL
  CREATE_ISSUES      "false" to skip issue creation
  HEADLESS           "false" to show browser
  GH_REPO            "owner/repo" slug (auto-detected by default)
```

Examples:

```bash
# Run against a staging server without creating issues
node autotest.js --base-url https://staging.example.com --no-issues

# Show browser window for debugging
HEADLESS=false node autotest.js
```

---

## How It Works

```
dialogue.md  ──parse──▶  scenarios[]
                              │
                    for each scenario:
                              │
                         Playwright page
                              │
                    execute steps in order
                              │
                    ┌─ pass ──┘
                    │
                    └─ fail ──▶  screenshot + bug record
                                        │
                              gh issue create --assignee copilot
```

1. **`dialogue.md`** — the single source of truth for what to test. Add, remove,
   or edit scenarios there; no changes to `autotest.js` are needed.
2. **`autotest.js`** — parses the dialogue and drives Playwright. Each failing
   step is recorded as a bug (the scenario continues so later steps are also
   checked).
3. **GitHub Issues** — one issue per bug, with scenario name, failing step,
   error message, page URL, and JS console errors. Copilot is assigned
   automatically.

---

## Adding or Editing Scenarios

Open `dialogue.md` and add a new `## Scenario:` block.  
See the syntax table at the top of that file for available actions.

---

## Screenshots

Failure screenshots are saved in `tests/e2e/screenshots/` (git-ignored).
Named `BUG_<ScenarioName>_<ACTION>.png`.

---

## CI Integration

Add to `.github/workflows/autotest.yml`:

```yaml
name: UI Autotest

on:
  workflow_dispatch:
  schedule:
    - cron: '0 6 * * *'   # daily at 06:00 UTC

jobs:
  autotest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - name: Install Python deps
        run: pip install -r requirements.txt
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - name: Install Node deps
        run: npm ci
        working-directory: tests/e2e
      - name: Install Playwright browsers
        run: npm run install-browsers
        working-directory: tests/e2e
      - name: Start aubergeRP server
        run: uvicorn aubergeRP.main:app --host 0.0.0.0 --port 8123 &
        env:
          AUBERGE_DATA_DIR: /tmp/auberge-data
      - name: Wait for server
        run: sleep 3
      - name: Run autotest robot
        run: node autotest.js
        working-directory: tests/e2e
        env:
          BASE_URL: http://localhost:8123
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: e2e-screenshots
          path: tests/e2e/screenshots/
```
