"""Home Assistant sensor platform objects."""

from enum import Enum

from homeassistant.helpers.entity import Entity


class SensorDeviceClass(str, Enum):
    VOLTAGE = "voltage"
    CURRENT = "current"
    POWER = "power"
    ENERGY = "energy"
    TEMPERATURE = "temperature"
    DURATION = "duration"
    TIMESTAMP = "timestamp"
    ENUM = "enum"
    DATA_SIZE = "data_size"


class SensorStateClass(str, Enum):
    MEASUREMENT = "measurement"
    TOTAL = "total"
    TOTAL_INCREASING = "total_increasing"


class SensorEntity(Entity):
    """Minimal sensor entity."""

    @property
    def native_value(self):
        return getattr(self, "_attr_native_value", None)

    @property
    def device_class(self):
        return getattr(self, "_attr_device_class", None)

    @property
    def state_class(self):
        return getattr(self, "_attr_state_class", None)

    @property
    def native_unit_of_measurement(self):
        return getattr(self, "_attr_native_unit_of_measurement", None)
