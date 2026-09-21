"""Minimal stand-in for homeassistant.util.dt (only what the integration imports)."""

from __future__ import annotations

from datetime import datetime


def now() -> datetime:
    """Return the local (naive) time, matching core's return type."""
    return datetime.now()
