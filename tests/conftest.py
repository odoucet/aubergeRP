import pytest


@pytest.fixture(autouse=True)
def disable_admin_auth_for_tests(monkeypatch):
    monkeypatch.delenv("AUBERGE_DATA_DIR", raising=False)
    monkeypatch.delenv("AUBERGE_HOST", raising=False)
    monkeypatch.delenv("AUBERGE_PORT", raising=False)
    monkeypatch.delenv("AUBERGE_LOG_LEVEL", raising=False)
    monkeypatch.delenv("AUBERGE_USER_NAME", raising=False)
    monkeypatch.delenv("AUBERGE_SENTRY_DSN", raising=False)
    monkeypatch.delenv("AUBERGE_ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("AUBERGE_DISABLE_ADMIN_AUTH", "1")
    yield


@pytest.fixture(autouse=True)
def reset_config_singleton():
    from aubergeRP.config import reset_config
    from aubergeRP.database import reset_engine
    reset_config()
    reset_engine()
    yield
    reset_config()
    reset_engine()
