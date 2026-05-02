"""Admin authentication utilities."""

from __future__ import annotations

import hashlib
import secrets


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
    return hash_password(password) == password_hash


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
