"""Home Assistant constants used by the integration."""

from enum import Enum

CONF_HOST = "host"
CONF_PORT = "port"
CONF_NAME = "name"


class UnitOfTemperature(str, Enum):
    CELSIUS = "C"


class UnitOfElectricCurrent(str, Enum):
    AMPERE = "A"


class UnitOfElectricPotential(str, Enum):
    VOLT = "V"


class UnitOfEnergy(str, Enum):
    KILO_WATT_HOUR = "kWh"


class UnitOfPower(str, Enum):
    WATT = "W"


class UnitOfTime(str, Enum):
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "h"
    DAYS = "d"
    MILLISECONDS = "ms"


class Platform(str, Enum):
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    NUMBER = "number"
    SELECT = "select"
    TEXT = "text"
    BUTTON = "button"
    SWITCH = "switch"


PERCENTAGE = "%"
