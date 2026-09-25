"""Home Assistant entity platform types."""

from collections.abc import Callable
from typing import Any

AddConfigEntryEntitiesCallback = Callable[..., Any]
async_add_entities_callback = None
