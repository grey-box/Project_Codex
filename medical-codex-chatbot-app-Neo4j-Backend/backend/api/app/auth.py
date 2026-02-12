"""Placeholder auth-token validation used by FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status


def _dummy_token_validator(token: str | None) -> bool:
    """Todo: replace with real validation logic."""
    return True


def require_auth_token(
    x_auth_token: str | None = Header(default=None, alias="X-Auth-Token"),
) -> str | None:
    """
    Optional auth token dependency.

    If a token is provided it must pass validation, otherwise the request is rejected.
    Missing tokens are allowed for now so routes can opt-in gradually.
    """
    if x_auth_token is None:
        return None
    if not _dummy_token_validator(x_auth_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )
    return x_auth_token
