"""Home Assistant text platform objects."""

from homeassistant.helpers.entity import Entity


class TextEntity(Entity):
    """Minimal text entity."""

    @property
    def max_length(self):
        return getattr(self, "_attr_max_length", None)

    @property
    def pattern(self):
        return getattr(self, "_attr_pattern", None)
