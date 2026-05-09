# Contributing to aubergeRP

**Stack:** Python 3.12 + FastAPI + SQLite · vanilla HTML/JS/CSS (no bundler).

Read `AGENTS.md` and `docs/` before anything else — they describe the architecture and the rules that CI enforces.

## Number one rule

This project is the 99th priority in my life. I work on it on my (small) free time, and I try to keep it as simple and maintainable as possible for the long term, so I can keep improving it for years to come without it becoming a burden.
If you want to contribute, please maintain this philosophy in mind and try to keep things simple, well documented and well tested.

---

## Setup

```bash
python -m pip install -r requirements-dev.txt
cp config.example.yaml config.yaml   # add your connector credentials
make run    # dev server with hot-reload
make test   # must pass before any PR
make lint   # ruff + mypy, must pass before any PR
make doc    # generate markdown docs from docstrings (for maintainers)
```

---

## Key rules

- **Routers are thin** — all business logic lives in `services/`.
- **Connectors are isolated** — one file per backend, registered in `connectors/manager.py`.
- **Every DB schema change** needs a numbered migration in `migrations/`.
- **Atomic file writes** — write-to-temp + `os.rename`.
- **No new dependencies** unless strictly necessary.
- Tests use `respx` to mock HTTP — no real network calls.

---

## Pull requests

Branch from `main`, run `make lint && make test`, open a PR. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

Please keep things **simple and maintainable** — this project is maintained in limited free time and must stay manageable for the long term (Did I already mentioned this ? :p).
