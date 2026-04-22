import json
import pytest
from pathlib import Path

from aubergeRP.utils.file_storage import read_json, write_json


def test_write_and_read_roundtrip(tmp_path):
    path = tmp_path / "data.json"
    data = {"key": "value", "number": 42, "nested": {"a": [1, 2, 3]}}
    write_json(path, data)
    assert read_json(path) == data


def test_write_creates_parent_dirs(tmp_path):
    path = tmp_path / "a" / "b" / "c.json"
    write_json(path, {"x": 1})
    assert path.exists()


def test_write_is_atomic(tmp_path):
    path = tmp_path / "out.json"
    write_json(path, {"v": 1})
    write_json(path, {"v": 2})
    assert read_json(path) == {"v": 2}


def test_read_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_json(tmp_path / "missing.json")


def test_write_unicode(tmp_path):
    path = tmp_path / "unicode.json"
    data = {"msg": "こんにちは 🌸"}
    write_json(path, data)
    assert read_json(path)["msg"] == "こんにちは 🌸"


def test_no_leftover_tmp_on_success(tmp_path):
    path = tmp_path / "clean.json"
    write_json(path, {"ok": True})
    tmp_files = list(tmp_path.glob(".tmp_*"))
    assert tmp_files == []
