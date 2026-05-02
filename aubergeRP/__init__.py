from __future__ import annotations

import tomllib
from pathlib import Path


def _read_version() -> str:
    """Read the application version from pyproject.toml.

    pyproject.toml is the single source of truth for the version.
    Falls back to "dev" if the file cannot be read (e.g. unexpected layout).
    """
    try:
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject.open("rb") as f:
            return str(tomllib.load(f)["project"]["version"])
    except Exception:
        return "dev"


__version__: str = _read_version()
