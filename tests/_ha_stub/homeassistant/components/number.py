"""Home Assistant number platform objects."""

from enum import Enum

from homeassistant.helpers.entity import Entity


class NumberMode(str, Enum):
    AUTO = "auto"
    BOX = "box"
    SLIDER = "slider"


class NumberEntity(Entity):
    """Minimal number entity."""

    @property
    def native_value(self):
        return getattr(self, "_attr_native_value", None)

    @property
    def native_min_value(self):
        return getattr(self, "_attr_native_min_value", None)

    @property
    def native_max_value(self):
        return getattr(self, "_attr_native_max_value", None)

    @property
    def native_step(self):
        return getattr(self, "_attr_native_step", None)

    @property
    def step(self):
        """Read-only in real Home Assistant (2026.x): no setter on purpose.

        Assigning self.step = ... in an integration must blow up here too, or
        the double hides the collision the dev bench caught.
        """
        return getattr(self, "_attr_step", 1.0)

    @property
    def native_unit_of_measurement(self):
        return getattr(self, "_attr_native_unit_of_measurement", None)

    @property
    def mode(self):
        return getattr(self, "_attr_mode", NumberMode.AUTO)
