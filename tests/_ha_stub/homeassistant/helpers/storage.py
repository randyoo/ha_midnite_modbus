"""Test double for Home Assistant's JSON storage helper.

The real `Store` reads and writes `.storage/<key>` JSON through the executor.
This double keeps the SAME constructor and the two coroutines the
integration calls - `async_load()` answering `None` when nothing was saved,
`async_save(data)` persisting it - and files live in a plain dict on the
double Hass (`hass.stored_files`), so a test can assert what the collected
history file would contain without a filesystem. Signatures mirror the real
thing (2026.9.3 `homeassistant/helpers/storage.py`); do not widen them.
"""

from __future__ import annotations

from typing import Any


class Store:
    """Records saves; answers loads from `hass.stored_files`."""

    def __init__(
        self,
        hass: Any,
        version: int,
        key: str,
        *,
        minor_version: int = 1,
        private: bool = False,
        **kwargs: Any,
    ) -> None:
        """Hold what the real Store holds; fake only where the bytes live."""
        self.hass = hass
        self.version = version
        self.key = key
        self.minor_version = minor_version
        self.private = private

    async def async_load(self) -> Any:
        """The stored object, or None when nothing was ever saved."""
        return getattr(self.hass, "stored_files", {}).get(self.key)

    async def async_save(self, data: Any) -> None:
        """Store the object under the key, the way the real file would."""
        self.hass.stored_files[self.key] = data
