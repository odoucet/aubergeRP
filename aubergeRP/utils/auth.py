"""Admin authentication utilities."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time


def generate_random_password(length: int = 16) -> str:
    """Generate a random secure password.

    Args:
        length: The length of the password to generate.

    Returns:
        A random password string.
    """
    # Use URL-safe characters for easy copy-paste
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str) -> str:
    """Hash a password using SHA-256.

    Args:
        password: The plain-text password to hash.

    Returns:
        The hashed password as a hex string.
    """
    # SHA-256 without a salt is used intentionally here.
    # The risk is low because the admin password is always a 16-character
    # randomly generated string (64^16 ≈ 2^96 possible values), making
    # pre-computed rainbow-table attacks computationally infeasible.
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a stored hash.

    Args:
        password: The plain-text password to verify.
        password_hash: The stored hash to verify against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return hmac.compare_digest(hash_password(password), password_hash)


def get_or_create_admin_password_hash(
    current_hash: str | None,
) -> tuple[str, str | None]:
    """Get or create an admin password hash.

    If a hash is provided, it is returned as-is. If not provided or empty,
    a new password is generated and hashed.

    Args:
        current_hash: The current admin password hash (if any).

    Returns:
        A tuple of (password_hash, plain_password_to_log_or_none).
        If a new password was generated, the second value contains the plain
        password that should be logged. If using an existing hash, the second
        value is None (no password to log).
    """
    if current_hash:
        return current_hash, None

    plain_password = generate_random_password()
    password_hash = hash_password(plain_password)
    return password_hash, plain_password


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(f"{data}{padding}")
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid JWT encoding") from exc


def _json_encode(data: object) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")


def create_admin_jwt(secret: str, expires_in_seconds: int) -> str:
    """Create an HS256 JWT for admin authentication."""
    if expires_in_seconds <= 0:
        raise ValueError("JWT expiry must be > 0")

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": "admin", "iat": now, "exp": now + expires_in_seconds}
    header_b64 = _b64url_encode(_json_encode(header))
    payload_b64 = _b64url_encode(_json_encode(payload))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def verify_admin_jwt(token: str, secret: str) -> dict[str, int | str]:
    """Verify an HS256 JWT for admin authentication."""
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("Invalid JWT format") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    provided_sig = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise ValueError("Invalid JWT signature")

    header = json.loads(_b64url_decode(header_b64))
    if not isinstance(header, dict) or header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise ValueError("Invalid JWT header")

    payload = json.loads(_b64url_decode(payload_b64))
    if not isinstance(payload, dict):
        raise ValueError("Invalid JWT payload")
    if not all(isinstance(k, str) for k in payload):
        raise ValueError("Invalid JWT payload keys")
    if payload.get("sub") != "admin":
        raise ValueError("Invalid JWT subject")

    exp = payload.get("exp")
    if not isinstance(exp, int) or int(time.time()) >= exp:
        raise ValueError("JWT expired")

    return payload
