from __future__ import annotations

from pathlib import Path

from aubergeRP.config import reset_config
from aubergeRP.database import reset_engine
from aubergeRP.main import create_app


def test_create_app_continues_when_example_seed_fails(monkeypatch, tmp_path: Path, caplog) -> None:
    reset_config()
    reset_engine()
    monkeypatch.setenv("AUBERGE_DATA_DIR", str(tmp_path))

    def _boom(data_dir: str) -> None:
        raise RuntimeError("seed failure")

    monkeypatch.setattr("aubergeRP.main.seed_example_characters", _boom)

    app = create_app()
    assert app is not None
    assert "Example character seeding failed at startup" in caplog.text
