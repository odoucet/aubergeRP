# Contributing to aubergeRP

Thank you for your interest in contributing! This guide will help you get started quickly.

---

## Table of contents

1. [Project overview](#project-overview)
2. [Getting started](#getting-started)
3. [Development workflow](#development-workflow)
4. [Coding standards](#coding-standards)
5. [Architecture rules](#architecture-rules)
6. [Testing](#testing)
7. [Submitting a pull request](#submitting-a-pull-request)
8. [Reporting bugs & requesting features](#reporting-bugs--requesting-features)

---

## Project overview

aubergeRP is a self-hostable roleplay engine built with **Python 3.12 + FastAPI + SQLite** on the backend and **vanilla HTML/JS/CSS** (no bundler) on the frontend. Please read `AGENTS.md` and the `docs/` folder for full architecture context before contributing.

---

## Getting started

```bash
# 1. Clone
git clone https://github.com/odoucet/aubergeRP.git
cd aubergeRP

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example config
cp config.example.yaml config.yaml
# Edit config.yaml to add your connector credentials

# 5. Run the dev server
make run
```

---

## Development workflow

```bash
make run    # start dev server with hot-reload
make test   # run the test suite (must pass before any PR)
make lint   # ruff + mypy (must pass before any PR)
```

All three commands must succeed on your branch before opening a pull request — CI will enforce this automatically.

---

## Coding standards

| Tool | Config |
|---|---|
| **ruff** | `pyproject.toml` — `select = ["E","F","W","I","N","UP","B","A","SIM"]`, line length 120 |
| **mypy** | `pyproject.toml` — `strict = true` |
| **pytest** | `pyproject.toml` — `asyncio_mode = "auto"` |

- Keep routers thin — no business logic in `aubergeRP/routers/`.
- All business logic lives in `aubergeRP/services/`.
- Connectors are isolated — one file per backend in `aubergeRP/connectors/`.
- Every DB schema change requires a numbered migration in `aubergeRP/migrations/`.
- Use atomic file writes (`write-to-temp + os.rename`) for any file stored on disk.
- Prefer existing libraries over adding new dependencies.

---

## Architecture rules

See `AGENTS.md` for the full set of architecture rules. The key ones:

1. **Routers are thin.** Delegate to services.
2. **Services own logic.** No imports from `routers/`.
3. **Connectors are isolated.** Register in `connectors/manager.py`.
4. **Every schema change needs a migration.**
5. **Atomic writes for files.**

---

## Testing

Tests live in `tests/`. They use `pytest-asyncio` for async test functions and `respx` for mocking HTTP calls.

```bash
make test                              # all tests
python -m pytest tests/test_api_chat.py   # single file
python -m pytest -x                   # stop on first failure
```

- Write tests for every new feature or bug fix.
- The test DB is created in-memory or in a temp directory — never touch `data/auberge.db` from tests.
- Use `respx` to mock connector HTTP calls; do not make real network requests in tests.

---

## Submitting a pull request

1. Fork the repository and create a branch from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
2. Make your changes following the coding standards above.
3. Run `make lint` and `make test` — both must pass.
4. Open a pull request against `main`. Fill in the PR template.
5. CI will run lint and tests automatically. The PR cannot be merged until both pass.

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) style:

```
feat: add ComfyUI LoRA support
fix: handle missing session token in SSE endpoint
docs: update connector quick-reference
chore: bump ruff to 0.4
```

---

## Reporting bugs & requesting features

Use the GitHub issue templates:

- **Bug report** — for something broken or behaving unexpectedly.
- **Feature request** — for new features or improvements.

Please search existing issues before opening a new one.
