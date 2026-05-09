from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aubergeRP.config import reset_config
from aubergeRP.utils.auth import hash_password


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUBERGE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUBERGE_ADMIN_PASSWORD_HASH", hash_password("correct horse"))
    reset_config()

    from aubergeRP.main import create_app
    from aubergeRP.routers import admin as admin_router

    admin_router._admin_login_failures.clear()
    admin_router._admin_sessions.clear()

    with TestClient(create_app()) as test_client:
        yield test_client

    admin_router._admin_login_failures.clear()
    admin_router._admin_sessions.clear()
    reset_config()


def _login(client: TestClient, password: str, headers: dict[str, str] | None = None):
    return client.post("/api/admin/login", json={"password": password}, headers=headers)


def test_admin_login_rate_limits_failed_attempts_per_ip(client: TestClient) -> None:
    for _ in range(3):
        response = _login(client, "wrong password")
        assert response.status_code == 401

    response = _login(client, "wrong password")

    assert response.status_code == 429
    assert response.json() == {"detail": "Too many login attempts. Please try again in a minute."}


def test_admin_login_uses_first_forwarded_ip(client: TestClient) -> None:
    headers = {"x-forwarded-for": "198.51.100.7, 10.0.0.1"}
    for _ in range(3):
        response = _login(client, "wrong password", headers=headers)
        assert response.status_code == 401

    blocked = _login(client, "wrong password", headers={"x-forwarded-for": "198.51.100.7, 10.0.0.2"})
    other_ip = _login(client, "wrong password", headers={"x-forwarded-for": "198.51.100.8, 10.0.0.1"})

    assert blocked.status_code == 429
    assert other_ip.status_code == 401


def test_admin_login_prefers_cloudflare_ip_over_forwarded_for(client: TestClient) -> None:
    for proxy_ip in ("10.0.0.1", "10.0.0.2", "10.0.0.3"):
        response = _login(
            client,
            "wrong password",
            headers={
                "cf-connecting-ip": "203.0.113.9",
                "x-forwarded-for": f"198.51.100.20, {proxy_ip}",
            },
        )
        assert response.status_code == 401

    blocked = _login(
        client,
        "wrong password",
        headers={
            "cf-connecting-ip": "203.0.113.9",
            "x-forwarded-for": "198.51.100.21, 10.0.0.4",
        },
    )
    other_ip = _login(
        client,
        "wrong password",
        headers={
            "cf-connecting-ip": "203.0.113.10",
            "x-forwarded-for": "198.51.100.20, 10.0.0.1",
        },
    )

    assert blocked.status_code == 429
    assert other_ip.status_code == 401


def test_successful_admin_login_resets_failed_attempt_counter(client: TestClient) -> None:
    headers = {"x-forwarded-for": "192.0.2.44"}

    for _ in range(2):
        response = _login(client, "wrong password", headers=headers)
        assert response.status_code == 401

    success = _login(client, "correct horse", headers=headers)
    assert success.status_code == 200
    assert "token" in success.json()

    for _ in range(3):
        response = _login(client, "wrong password", headers=headers)
        assert response.status_code == 401

    blocked = _login(client, "wrong password", headers=headers)
    assert blocked.status_code == 429
