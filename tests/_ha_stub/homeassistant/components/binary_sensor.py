"""Home Assistant binary sensor platform objects."""

from enum import StrEnum

from homeassistant.helpers.entity import Entity


class BinarySensorDeviceClass(StrEnum):
    PROBLEM = "problem"
    RUNNING = "running"
    CONNECTIVITY = "connectivity"


class BinarySensorEntity(Entity):
    """Minimal binary sensor entity."""

    @property
    def is_on(self):
        return getattr(self, "_attr_is_on", None)
