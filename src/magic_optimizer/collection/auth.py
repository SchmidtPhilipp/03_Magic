"""Resolve current user from Authelia / proxy headers."""

from __future__ import annotations

import os

from flask import request


def current_username() -> str:
    """Return authenticated username from reverse proxy or env fallback."""
    for header in (
        "Remote-User",
        "X-Authelia-Username",
        "X-Forwarded-User",
    ):
        value = request.headers.get(header)
        if value:
            return value.strip()
    return os.environ.get("MTG_DEFAULT_USER", "philipp")
