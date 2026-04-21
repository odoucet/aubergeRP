import pytest
import yaml
from pathlib import Path

from aubergeRP.config import load_config, Config


def test_load_defaults_when_no_file(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.yaml")
    assert isinstance(cfg, Config)
    assert cfg.app.host == "0.0.0.0"
    assert cfg.app.port == 8000
    assert cfg.app.log_level == "INFO"
    assert cfg.app.data_dir == "data"
    assert cfg.active_connectors.text == ""
    assert cfg.active_connectors.image == ""
    assert cfg.user.name == "User"


def test_load_valid_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "app": {"host": "127.0.0.1", "port": 9000, "log_level": "DEBUG", "data_dir": "/tmp/data"},
        "active_connectors": {"text": "abc-123", "image": "def-456"},
        "user": {"name": "Alice"},
    }))
    cfg = load_config(config_file)
    assert cfg.app.host == "127.0.0.1"
    assert cfg.app.port == 9000
    assert cfg.app.log_level == "DEBUG"
    assert cfg.app.data_dir == "/tmp/data"
    assert cfg.active_connectors.text == "abc-123"
    assert cfg.active_connectors.image == "def-456"
    assert cfg.user.name == "Alice"


def test_load_partial_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"user": {"name": "Bob"}}))
    cfg = load_config(config_file)
    assert cfg.user.name == "Bob"
    assert cfg.app.port == 8000


def test_invalid_log_level_raises(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"app": {"log_level": "INVALID"}}))
    with pytest.raises(Exception):
        load_config(config_file)


def test_invalid_port_type_raises(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"app": {"port": "not-a-number"}}))
    with pytest.raises(Exception):
        load_config(config_file)
