"""Tests for admin GUI customization and plugin-system behaviors.

Covers:
  1. GUI customization
     - GET /api/config/gui returns default empty strings
     - PUT /api/config/gui persists and returns updated values
  2. Plugin system skeleton
     - BasePlugin subclass can be instantiated
     - PluginManager.load_plugin registers the plugin and calls on_load()
     - PluginManager.call_hook dispatches to the plugin
     - PluginManager.discover ignores missing directories
     - PluginManager.discover loads plugins from .py files
     - PluginManager.list_plugins returns metadata
     - PluginManager.unload_all calls on_unload()
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from aubergeRP.config import reset_config
from aubergeRP.plugins.base import BasePlugin
from aubergeRP.plugins.manager import PluginManager

# ---------------------------------------------------------------------------
# App fixture — fresh config per test, save path redirected to tmp_path
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUBERGE_DATA_DIR", str(tmp_path))
    reset_config()
    from aubergeRP.main import create_app
    from aubergeRP.routers.config import get_config_save_path
    app = create_app()
    config_file = tmp_path / "config.yaml"
    app.dependency_overrides[get_config_save_path] = lambda: config_file
    with TestClient(app) as c:
        yield c
    reset_config()


# ===========================================================================
# 1. GUI customization
# ===========================================================================

def test_gui_config_defaults(client):
    """GET /api/config/gui returns default empty strings."""
    resp = client.get("/api/config/gui")
    assert resp.status_code == 200
    data = resp.json()
    assert data["custom_css"] == ""
    assert data["custom_header_html"] == ""
    assert data["custom_footer_html"] == ""


def test_gui_config_update_and_retrieve(client):
    """PUT /api/config/gui persists values and GET returns them."""
    payload = {
        "custom_css": "body { background: red; }",
        "custom_header_html": "<marquee>Hello</marquee>",
        "custom_footer_html": "<p>Custom footer</p>",
    }
    put_resp = client.put("/api/config/gui", json=payload)
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data["custom_css"] == payload["custom_css"]
    assert data["custom_header_html"] == payload["custom_header_html"]
    assert data["custom_footer_html"] == payload["custom_footer_html"]

    # Re-fetch to verify in-memory persistence
    get_resp = client.get("/api/config/gui")
    assert get_resp.status_code == 200
    assert get_resp.json() == data


def test_gui_config_partial_update(client):
    """Updating only one field works; others default to empty string."""
    payload = {"custom_css": "a { color: blue; }", "custom_header_html": "", "custom_footer_html": ""}
    resp = client.put("/api/config/gui", json=payload)
    assert resp.status_code == 200
    assert resp.json()["custom_css"] == "a { color: blue; }"
    assert resp.json()["custom_header_html"] == ""


# ===========================================================================
# 2. Plugin system skeleton
# ===========================================================================

class _NullPlugin(BasePlugin):
    name = "null_plugin"
    version = "1.0.0"

    loaded: bool = False
    unloaded: bool = False
    received_hook: dict | None = None

    def on_load(self) -> None:
        _NullPlugin.loaded = True

    def on_unload(self) -> None:
        _NullPlugin.unloaded = True

    def on_message_received(self, context: dict[str, Any]) -> None:
        _NullPlugin.received_hook = context


def test_plugin_instantiation():
    p = _NullPlugin()
    assert p.name == "null_plugin"
    assert p.version == "1.0.0"


def test_plugin_manager_load_and_hook():
    _NullPlugin.loaded = False
    _NullPlugin.received_hook = None
    mgr = PluginManager()
    mgr.load_plugin(_NullPlugin)
    assert _NullPlugin.loaded is True

    ctx = {"conversation_id": "c1", "message": "hello"}
    mgr.call_hook("on_message_received", ctx)
    assert _NullPlugin.received_hook == ctx


def test_plugin_manager_list_plugins():
    mgr = PluginManager()
    mgr.load_plugin(_NullPlugin)
    plugins = mgr.list_plugins()
    assert any(p["name"] == "null_plugin" for p in plugins)


def test_plugin_manager_unload_all():
    _NullPlugin.unloaded = False
    mgr = PluginManager()
    mgr.load_plugin(_NullPlugin)
    mgr.unload_all()
    assert _NullPlugin.unloaded is True
    assert mgr.list_plugins() == []


def test_plugin_manager_discover_missing_dir():
    """discover() on a missing directory should not raise."""
    mgr = PluginManager()
    mgr.discover("/nonexistent/path/xyz")
    assert mgr.list_plugins() == []


def test_plugin_manager_discover_loads_file(tmp_path):
    """discover() loads BasePlugin subclasses from .py files."""
    plugin_file = tmp_path / "myplugin.py"
    plugin_file.write_text(
        "from aubergeRP.plugins.base import BasePlugin\n"
        "class MyDiscoveredPlugin(BasePlugin):\n"
        "    name = 'discovered'\n"
        "    version = '0.1.0'\n"
    )
    mgr = PluginManager()
    mgr.discover(tmp_path)
    assert any(p["name"] == "discovered" for p in mgr.list_plugins())


def test_plugin_manager_call_hook_unknown_name():
    """Calling a hook that the plugin doesn't implement should not raise."""
    mgr = PluginManager()
    mgr.load_plugin(_NullPlugin)
    mgr.call_hook("on_nonexistent_hook", {})  # must not raise
