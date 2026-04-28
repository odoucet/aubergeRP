"""Admin authentication models."""

from __future__ import annotations

from pydantic import BaseModel


class AdminLoginRequest(BaseModel):
    """Request to login to admin panel."""

    password: str


class AdminLoginResponse(BaseModel):
    """Response from admin login."""

    token: str
