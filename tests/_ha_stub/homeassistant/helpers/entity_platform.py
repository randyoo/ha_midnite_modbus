"""Home Assistant entity platform types."""

from typing import Any, Callable

AddConfigEntryEntitiesCallback = Callable[..., Any]
async_add_entities_callback = None
