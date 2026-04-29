# E2E Tests

Browser tests for aubergeRP using [Playwright](https://playwright.dev) and Node's built-in test runner.

## Running tests

```bash
# Install dependencies (once)
cd tests/e2e
npm ci
npx playwright install chromium

# Run all E2E tests
make test-e2e          # from repo root
node --test *.test.mjs # or directly
```

## Debugging

```bash
# Show the browser window while tests run (set PWDEBUG or use headed mode)
HEADED=1 node --test mobile-scroll.test.mjs

# Run a single test file
node --test chat-streaming.test.mjs
```

Screenshots of failures are saved to `tests/e2e/screenshots/` (git-ignored).

## Test files

| File | What it tests |
|---|---|
| `chat-streaming.test.mjs` | SSE image streaming UI (placeholder, progress bar, error/retry) |
| `generate-image-button.test.mjs` | Generate-image button visibility based on connector state |
| `mobile-scroll.test.mjs` | Scroll-pin behaviour + input visibility on 5 viewport sizes |

Tests use lightweight HTML harnesses in `harness/` that load only the
relevant frontend JS, so no running server is needed.

## CI

E2E tests run automatically on every pull request via `.github/workflows/e2e.yml`.
