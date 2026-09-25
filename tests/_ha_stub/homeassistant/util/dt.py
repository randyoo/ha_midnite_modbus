"""Minimal stand-in for homeassistant.util.dt (only what the integration imports)."""

from __future__ import annotations

from datetime import UTC, datetime


def now() -> datetime:
    """Return the local (naive) time, matching core's return type."""
    return datetime.now()


def utcnow() -> datetime:
    """Return the current UTC time, tz-aware, matching core's return type."""
    return datetime.now(UTC)


def as_local(value: datetime) -> datetime:
    """Strip the timezone the way core's local conversion ends up presenting.

    The double has no zone info; the bridge only needs a naive local wall
    clock after conversion, and dropping tzinfo is the naive stand-in for
    "convert to HA's zone and drop it".
    """
    return value.replace(tzinfo=None)
