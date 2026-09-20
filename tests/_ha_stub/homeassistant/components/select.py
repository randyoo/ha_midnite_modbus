"""Home Assistant select platform objects."""

from homeassistant.helpers.entity import Entity


class SelectEntity(Entity):
    """Minimal select entity."""

    @property
    def current_option(self):
        return getattr(self, "_attr_current_option", None)

    @property
    def options(self):
        return getattr(self, "_attr_options", [])
