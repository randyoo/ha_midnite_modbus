"""Home Assistant constants used by the integration."""

from enum import StrEnum

CONF_HOST = "host"
CONF_PORT = "port"
CONF_NAME = "name"


class UnitOfTemperature(StrEnum):
    CELSIUS = "C"


class UnitOfElectricCurrent(StrEnum):
    AMPERE = "A"


class UnitOfElectricPotential(StrEnum):
    VOLT = "V"


class UnitOfEnergy(StrEnum):
    KILO_WATT_HOUR = "kWh"


class UnitOfPower(StrEnum):
    WATT = "W"


class UnitOfTime(StrEnum):
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "h"
    DAYS = "d"
    MILLISECONDS = "ms"


class Platform(StrEnum):
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    NUMBER = "number"
    SELECT = "select"
    TEXT = "text"
    BUTTON = "button"
    SWITCH = "switch"


PERCENTAGE = "%"
