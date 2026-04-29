# AGENTS.md — Context for AI coding agents

## Project at a glance

aubergeRP is a **self-hostable roleplay engine** built with:

- **Backend:** Python 3.12 + FastAPI + SQLModel (SQLite)
- **Frontend:** Vanilla HTML/JS/CSS — no framework, no build step
- **Connectors:** pluggable modules for text (LLM) and image generation

Architecture docs are in `docs/`, read in numeric order. Spec files are ground truth for intended behaviour.

## Instructions

- Don't assume. Surface confusion and tradeoffs.
- Minimum code that solves the problem. Nothing speculative.
- Touch only what you must. Don't refactor unrelated code.
- Success = tests pass + lint clean. Don't declare done until verified.
- Add unit tests for new features and bug fixes.
- Add E2E tests for heavy user-facing features (`make test-e2e`).
- Do not create Markdown files without asking first.

## Running tests

```bash
pip install -r requirements.txt              # once

make test                                    # full test suite
make test tests/test_api_chat.py             # single file

make test-e2e                                # browser tests (requires node + playwright)
make lint                                    # ruff check + mypy
```

Tests use `pytest-asyncio` + `respx` for mocking httpx calls. Fixtures create
a temp-dir SQLite DB — see `tests/conftest.py`.

## post-actions

After your job is done, make sure `make lint` returns no error or fix them.

