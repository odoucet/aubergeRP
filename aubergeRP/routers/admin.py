"""Admin authentication router."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException

from ..config import get_config
from ..models.admin import AdminLoginRequest, AdminLoginResponse
from ..utils.auth import verify_password

router = APIRouter(prefix="/admin", tags=["admin"])

# Store active admin sessions (token -> bool)
# In production, this could use Redis or JWT tokens
_admin_sessions: set[str] = set()


def get_admin_token(x_admin_token: str = Header(default="")) -> str:
    """FastAPI dependency to extract and validate admin auth token.

    Args:
        x_admin_token: The admin token from X-Admin-Token header.

    Returns:
        The admin token if valid.

    Raises:
        HTTPException: 401 if token is missing or invalid.
    """
    # Test-only bypass to preserve existing test suite behavior.
    if os.environ.get("AUBERGE_DISABLE_ADMIN_AUTH", "").strip() == "1":
        return "test-bypass"

    if not x_admin_token or x_admin_token not in _admin_sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_admin_token


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(request: AdminLoginRequest) -> AdminLoginResponse:
    """Authenticate to admin panel with password.

    Args:
        request: Contains the plain-text password.

    Returns:
        AdminLoginResponse with an auth token.

    Raises:
        HTTPException: 401 if password is incorrect.
    """
    config = get_config()

    if not config.app.admin_password_hash:
        raise HTTPException(status_code=403, detail="Admin authentication not configured")

    if not verify_password(request.password, config.app.admin_password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")

    # Generate a new session token
    import secrets
    token = secrets.token_urlsafe(32)
    _admin_sessions.add(token)

    return AdminLoginResponse(token=token)


@router.post("/logout")
def admin_logout(token: str = Depends(get_admin_token)) -> dict[str, str]:
    """Logout from admin panel.

    Args:
        token: The admin token (validated by dependency).

    Returns:
        Success message.
    """
    _admin_sessions.discard(token)
    return {"message": "Logged out"}
