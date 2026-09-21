"""Home Assistant switch platform objects."""

from homeassistant.helpers.entity import Entity


class SwitchEntity(Entity):
    """Minimal switch entity."""

    @property
    def is_on(self):
        return getattr(self, "_attr_is_on", False)

    async def async_turn_on(self, **kwargs):
        raise NotImplementedError

    async def async_turn_off(self, **kwargs):
        raise NotImplementedError
