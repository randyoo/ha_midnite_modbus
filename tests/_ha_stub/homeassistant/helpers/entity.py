"""Home Assistant entity base objects."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EntityCategory(str, Enum):
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


@dataclass
class EntityDescription:
    """Minimal entity description, enough to be subclassed by a dataclass."""

    key: str = ""
    name: Optional[str] = None
    translation_key: Optional[str] = None
    entity_category: Optional[EntityCategory] = None
    entity_registry_enabled_default: bool = True
    icon: Optional[str] = None


class Entity:
    """Attribute shim that mirrors the Home Assistant _attr_ convention."""

    _attr_should_poll = False
    _attr_available = True

    def __init_subclass__(cls, **kwargs):
        """Nothing to do; properties below resolve _attr_ values lazily."""
        super().__init_subclass__(**kwargs)

    @property
    def name(self):
        return getattr(self, "_attr_name", None)

    @property
    def unique_id(self):
        return getattr(self, "_attr_unique_id", None)

    @property
    def available(self):
        return getattr(self, "_attr_available", True)

    @property
    def entity_category(self):
        return getattr(self, "_attr_entity_category", None)

    @property
    def entity_registry_enabled_default(self):
        return getattr(self, "_attr_entity_registry_enabled_default", True)

    @property
    def device_info(self):
        return getattr(self, "_attr_device_info", None)

    @property
    def icon(self):
        return getattr(self, "_attr_icon", None)

    @property
    def translation_key(self):
        return getattr(self, "_attr_translation_key", None)

    @property
    def suggested_display_precision(self):
        return getattr(self, "_attr_suggested_display_precision", None)

    async def async_update(self):
        """No-op refresh hook."""

    def async_write_ha_state(self):
        """Push the entity's state, as Home Assistant does (no-op in the double)."""


EntityCategoryValue = Any
