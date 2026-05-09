"""Tests for installation docs, API reference, CORS behavior, and Sentry config.

Covers:
  1. Installation guide exists in docs/
  2. Auto-generated API reference — /api-docs serves Redoc HTML
  3. CORS auto-detection — Host header sets Access-Control-Allow-Origin
  4. Sentry error tracking — _init_sentry() is a no-op when no DSN is set;
     sentry_sdk.init() is called when a DSN is configured
  5. Config model includes sentry_dsn field
  6. AUBERGE_SENTRY_DSN env var overrides sentry_dsn
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from aubergeRP.config import load_config, reset_config

# ---------------------------------------------------------------------------
# Repo root helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUBERGE_DATA_DIR", str(tmp_path))
    reset_config()
    from aubergeRP.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c
    reset_config()


# ===========================================================================
# 1. Installation guide
# ===========================================================================

def test_installation_guide_exists():
    assert (_REPO_ROOT / "docs" / "installation-guide.md").exists()


def test_installation_guide_covers_platforms():
    content = (_REPO_ROOT / "docs" / "installation-guide.md").read_text()
    assert "Linux" in content
    assert "macOS" in content
    assert "Windows" in content
    assert "Docker" in content


def test_installation_guide_covers_docker():
    content = (_REPO_ROOT / "docs" / "installation-guide.md").read_text()
    assert "docker compose" in content.lower() or "docker-compose" in content.lower()


# ===========================================================================
# 2. API reference (Redoc)
# ===========================================================================

def test_api_docs_endpoint_returns_html(client):
    resp = client.get("/api-docs")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "redoc" in resp.text.lower()


def test_api_docs_references_openapi_spec(client):
    resp = client.get("/api-docs")
    assert "/openapi.json" in resp.text


def test_openapi_json_accessible(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "openapi" in schema
    assert schema["info"]["title"] == "aubergeRP"


def test_static_css_has_revalidation_cache_control_and_etag(client):
    resp = client.get("/css/main.css")
    assert resp.status_code == 200
    cache_control = resp.headers.get("cache-control", "")
    assert "no-cache" in cache_control
    assert "must-revalidate" in cache_control
    assert "etag" in resp.headers


def test_static_css_conditional_request_returns_304(client):
    first = client.get("/css/main.css")
    etag = first.headers.get("etag")
    assert etag

    second = client.get("/css/main.css", headers={"If-None-Match": etag})
    assert second.status_code == 304


def test_index_html_has_no_cache_revalidation_header(client):
    resp = client.get("/")
    assert resp.status_code == 200
    cache_control = resp.headers.get("cache-control", "")
    assert "no-cache" in cache_control
    assert "must-revalidate" in cache_control


# ===========================================================================
# 3. CORS auto-detection
# ===========================================================================

def test_cors_auto_detect_same_host(client):
    """When Origin matches Host, ACAO header should be set."""
    resp = client.get(
        "/api/health/",
        headers={"Host": "localhost:8123", "Origin": "http://localhost:8123"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:8123"


def test_cors_no_origin_header(client):
    """Requests without an Origin header should not get CORS headers."""
    resp = client.get("/api/health/")
    assert "access-control-allow-origin" not in resp.headers


def test_cors_mismatched_origin_no_header(client):
    """Requests from a different origin (not matching Host) get no ACAO header."""
    resp = client.get(
        "/api/health/",
        headers={"Host": "localhost:8123", "Origin": "http://evil.example.com"},
    )
    assert "access-control-allow-origin" not in resp.headers


# ===========================================================================
# 4. Sentry integration
# ===========================================================================


def _mock_sentry_modules() -> dict[str, types.ModuleType]:
    sentry_sdk = types.ModuleType("sentry_sdk")
    sentry_sdk.__path__ = []
    sentry_sdk.init = Mock()

    integrations = types.ModuleType("sentry_sdk.integrations")
    integrations.__path__ = []

    fastapi_integration = types.ModuleType("sentry_sdk.integrations.fastapi")
    starlette_integration = types.ModuleType("sentry_sdk.integrations.starlette")

    class FastApiIntegration:
        pass

    class StarletteIntegration:
        pass

    fastapi_integration.FastApiIntegration = FastApiIntegration
    starlette_integration.StarletteIntegration = StarletteIntegration

    integrations.fastapi = fastapi_integration
    integrations.starlette = starlette_integration
    sentry_sdk.integrations = integrations

    return {
        "sentry_sdk": sentry_sdk,
        "sentry_sdk.integrations": integrations,
        "sentry_sdk.integrations.fastapi": fastapi_integration,
        "sentry_sdk.integrations.starlette": starlette_integration,
    }


def test_init_sentry_no_op_when_no_dsn():
    """_init_sentry('') must not call sentry_sdk.init()."""
    from aubergeRP.main import _init_sentry

    mock_modules = _mock_sentry_modules()
    with patch.dict(sys.modules, mock_modules):
        mock_init = mock_modules["sentry_sdk"].init
        _init_sentry("")
        mock_init.assert_not_called()


def test_init_sentry_calls_init_when_dsn_configured():
    """_init_sentry(dsn) calls sentry_sdk.init() with the given DSN."""
    from aubergeRP.main import _init_sentry

    mock_modules = _mock_sentry_modules()
    with patch.dict(sys.modules, mock_modules):
        mock_init = mock_modules["sentry_sdk"].init
        _init_sentry("https://public@sentry.example.com/1")
        mock_init.assert_called_once()
        args, kwargs = mock_init.call_args
        assert kwargs.get("dsn") == "https://public@sentry.example.com/1"


def test_init_sentry_does_not_raise_when_sentry_missing():
    """_init_sentry() must not raise even if sentry_sdk is unavailable."""
    import builtins

    from aubergeRP.main import _init_sentry
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "sentry_sdk":
            raise ImportError("sentry_sdk not installed")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        _init_sentry("https://public@sentry.example.com/1")  # must not raise


# ===========================================================================
# 5. Config: sentry_dsn field
# ===========================================================================

def test_config_has_sentry_dsn_field():
    load_config.__wrapped__(Path("/nonexistent")) if hasattr(load_config, "__wrapped__") else load_config()
    # Just check the field exists on AppConfig
    from aubergeRP.config import AppConfig
    ac = AppConfig()
    assert hasattr(ac, "sentry_dsn")
    assert ac.sentry_dsn == ""


# ===========================================================================
# 6. AUBERGE_SENTRY_DSN env var
# ===========================================================================

def test_env_var_sentry_dsn(monkeypatch):
    monkeypatch.setenv("AUBERGE_SENTRY_DSN", "https://test@sentry.io/99")
    reset_config()
    from aubergeRP.config import load_config
    cfg = load_config()
    assert cfg.app.sentry_dsn == "https://test@sentry.io/99"
    reset_config()
