"""Support for Midnite Solar number platform."""

from __future__ import annotations

import logging
from typing import Any

from .base import MidniteBaseEntityDescription

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    AUX_THRESHOLD_SETTINGS,
    DOMAIN,
    EE_BACKED_REGISTERS,
    FORCE_FLAGS,
    REGISTER_MAP,
)
from .coordinator import MidniteSolarUpdateCoordinator
from .entity_writes import async_store_settings, async_verify_write, async_write_setting
from .register_values import (
    byte_of,
    force_flag_write,
    pack_byte_pair,
    scaled_register,
    scaled_value,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar numbers."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    numbers = [
        AbsorbVoltageNumber(coordinator, entry),
        FloatVoltageNumber(coordinator, entry),
        EqualizeVoltageNumber(coordinator, entry),
        BatteryCurrentLimitNumber(coordinator, entry),
        AbsorbTimeNumber(coordinator, entry),
        MinAbsorbTimeNumber(coordinator, entry),
        EqualizeTimeNumber(coordinator, entry),
        EqualizeIntervalDaysNumber(coordinator, entry),
        ModbusAddressNumber(coordinator, entry),
        MaxBatteryTempCompVoltageNumber(coordinator, entry),
        MinBatteryTempCompVoltageNumber(coordinator, entry),
        BatteryTempCompValueNumber(coordinator, entry),
        EqualizeRetryDaysNumber(coordinator, entry),
        # The Aux thresholds are read every interval and had no entity at all.
        *(
            AuxThresholdNumber(coordinator, entry, setting)
            for setting in AUX_THRESHOLD_SETTINGS
        ),
        # The wind tables are 16 steps each, packed two steps per register.
        *(WindPowerCurveVNumber(coordinator, entry, step) for step in range(16)),
        *(WindPowerCurveINumber(coordinator, entry, step) for step in range(16)),
    ]
    
    async_add_entities(numbers)


class MidniteSolarNumber(CoordinatorEntity[MidniteSolarUpdateCoordinator], NumberEntity):
    """Base class for all Midnite Solar numbers."""

    _attr_native_min_value: float | None = None
    _attr_native_max_value: float | None = None
    _attr_native_step: float | None = None

    # How the entity's units differ from the register's own units. Most set
    # points are tenths ("([4149] /10) Volts"); times are plain seconds, and the
    # temperature compensation value is stored as a negative.
    is_time_value = False
    is_raw_value = False
    is_negative = False
    seconds_in_register = False

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator)
        self._entry = entry
        
        # Create device info - use serial number if available, otherwise use entry_id
        # We'll update this dynamically when data becomes available via property override
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def device_info(self):
        """Return dynamic device info with device ID and model if available."""
        return MidniteBaseEntityDescription.get_device_info(
            self.coordinator, self._entry, DOMAIN
        )

    def _to_register_value(self, value: float) -> int:
        """Convert the user-facing value to the integer the register holds."""
        if self.seconds_in_register:
            return int(round(value * 60))
        if self.is_negative:
            return scaled_register(-value)
        if self.is_time_value or self.is_raw_value:
            return int(value)
        return scaled_register(value)

    def _from_register_value(self, raw: int) -> float:
        """Convert the register integer to the user-facing value."""
        if self.seconds_in_register:
            minutes = raw / 60.0
            return int(minutes) if minutes.is_integer() else minutes
        if self.is_negative:
            return -scaled_value(raw)
        if self.is_time_value or self.is_raw_value:
            return float(raw)
        return scaled_value(raw)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        raw = self.coordinator.get_register_value(self.register_address)
        if raw is None:
            _LOGGER.debug("Register %s has no value yet", self.register_address)
            return None
        return self._from_register_value(raw)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)

    async def _async_set_value(self, value: float) -> None:
        """Set the value on the device and store it."""
        register_value = self._to_register_value(value)
        _LOGGER.debug(
            "Writing %s to register %s (raw value %s)",
            value,
            self.register_address,
            register_value,
        )
        await async_write_setting(
            self.hass, self.coordinator.api, self.register_address, register_value, self.name
        )
        if self.register_address in EE_BACKED_REGISTERS:
            await async_store_settings(self.hass, self.coordinator.api, self.name)
        await async_verify_write(
            self.hass,
            self.coordinator.api,
            self.register_address,
            register_value,
            self.name,
            lambda raw: f"{self._from_register_value(raw)} {self.native_unit_of_measurement or ''}".strip(),
        )
        await self.coordinator.async_request_refresh()


class AbsorbVoltageNumber(MidniteSolarNumber):
    """Number to set absorb voltage."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Absorb Voltage"
        self._attr_unique_id = f"{entry.entry_id}_absorb_voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"]
        # Voltage range: 10V to 65V (typical for 12V, 24V, and 48V systems)
        # Register can theoretically go up to 655.3V but practical max is 65V
        self._attr_native_min_value = 10.0
        self._attr_native_max_value = 65.0
        self._attr_native_step = 0.1
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerTableNumber(MidniteSolarNumber):
    """One voltage or current step of a wind power table.

    Section 1.3.3 gives each table as "16 Bytes" of "0 to 255 volts" or
    "0 to 255 amps" - one count is one volt or one amp - and the register map
    packs two steps into every register, "4301 R/W WindPowerTableV +0 (EE)
    WindPowerTableV(stp 1) << 8) + WindPowerTableV(stp 0)". So a step is neither
    scaled by ten nor alone in its register: writing one has to leave the step
    sharing that register intact.
    """

    _table_first_register: int = 0
    _id_suffix: str = ""
    _attr_native_min_value = 0
    _attr_native_max_value = 255
    _attr_native_step = 1

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any, step: int = 0):
        """Initialize the number for one table step."""
        super().__init__(coordinator, entry)
        self.step = step
        self._attr_name = f"Wind Power Curve {self._id_suffix.upper()}{step}"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_{self._id_suffix}{step}"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def register_address(self) -> int:
        """Return the register holding this step, shared with its neighbour."""
        return self._table_first_register + (self.step >> 1)

    def _from_register_value(self, raw: int) -> float:
        """Return this step's byte out of the shared register."""
        return float(byte_of(raw, self.step & 1))

    def _to_register_value(self, value: float) -> int:
        """Return the register value that changes only this step."""
        current = self.coordinator.get_register_value(self.register_address) or 0
        try:
            return pack_byte_pair(current, self.step & 1, int(value))
        except ValueError as e:
            raise HomeAssistantError(
                f"Wind power table steps are 0 to 255, got {value}"
            ) from e


class WindPowerCurveVNumber(WindPowerTableNumber):
    """Voltage steps of the wind power table, registers 4301-4308."""

    _table_first_register = REGISTER_MAP["WIND_POWER_TABLE_V_REG_0"]
    _id_suffix = "v"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any, step: int = 0):
        """Initialize the number."""
        super().__init__(coordinator, entry, step)
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT


class WindPowerCurveINumber(WindPowerTableNumber):
    """Current steps of the wind power table, registers 4309-4316."""

    _table_first_register = REGISTER_MAP["WIND_POWER_TABLE_I_REG_0"]
    _id_suffix = "i"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any, step: int = 0):
        """Initialize the number."""
        super().__init__(coordinator, entry, step)
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE


class MinAbsorbTimeNumber(MidniteSolarNumber):
    """Number to set minimum absorb time."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Minimum Absorb Time"
        self._attr_unique_id = f"{entry.entry_id}_min_absorb_time"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["MIN_ABSORB_TIME"]
        # Typical minimum absorb times (0 = disabled)
        # Values are stored in seconds for display, but register stores seconds
        self._attr_native_min_value = 0
        self._attr_native_max_value = 3600  # 1 hour in seconds
        self._attr_native_step = 1  # 1 second increments
        self.is_time_value = True  # Don't divide by 10
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default
class MaxBatteryTempCompVoltageNumber(MidniteSolarNumber):
    """Number to set maximum battery temperature compensation voltage."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Max Battery Temp Comp Voltage"
        self._attr_unique_id = f"{entry.entry_id}_max_batt_temp_comp_voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["MAX_BATTERY_TEMP_COMP_VOLTAGE"]
        # Voltage range: 10V to 65V (typical for 12V, 24V, and 48V systems)
        self._attr_native_min_value = 10.0
        self._attr_native_max_value = 65.0
        self._attr_native_step = 0.1
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class MinBatteryTempCompVoltageNumber(MidniteSolarNumber):
    """Number to set minimum battery temperature compensation voltage."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Min Battery Temp Comp Voltage"
        self._attr_unique_id = f"{entry.entry_id}_min_batt_temp_comp_voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["MIN_BATTERY_TEMP_COMP_VOLTAGE"]
        # Voltage range: 10V to 65V (typical for 12V, 24V, and 48V systems)
        self._attr_native_min_value = 10.0
        self._attr_native_max_value = 65.0
        self._attr_native_step = 0.1
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class BatteryTempCompValueNumber(MidniteSolarNumber):
    """Number to set battery temperature compensation value per 2V cell."""

    # The register unit differs from the entity unit; see the base class hooks.
    is_negative = True

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Battery Temp Comp Value"
        self._attr_unique_id = f"{entry.entry_id}_batt_temp_comp_value"
        # Formula: -([4157]/10) - negative value representing mV/°C per 2V cell
        self._attr_native_unit_of_measurement = "mV/°C per 2V cell"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["BATTERY_TEMP_COMP_VALUE"]
        # Typical temperature compensation range: -1 to -5 mV/°C per 2V cell (negative values)
        self._attr_native_min_value = -10.0
        self._attr_native_max_value = 0.0
        self._attr_native_step = 0.1
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default
class EqualizeRetryDaysNumber(MidniteSolarNumber):
    """Number to set equalize retry days until giving up."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQ Retry Days"
        self._attr_unique_id = f"{entry.entry_id}_equalize_retry_days"
        self._attr_native_unit_of_measurement = UnitOfTime.DAYS
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["EQUALIZE_RETRY_DAYS"]
        # Typical retry days: 0 to 365 (0 = disabled)
        self._attr_native_min_value = 0
        self._attr_native_max_value = 365
        self._attr_native_step = 1
        self.is_raw_value = True  # Don't divide by 10 for days
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class ModbusAddressNumber(MidniteSolarNumber):
    """Number to set Modbus address."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Modbus Address"
        self._attr_unique_id = f"{entry.entry_id}_modbus_address"
        self.register_address = REGISTER_MAP["CLASSIC_MODBUS_ADDR_EEPROM"]
        # Modbus address range: 1-255 (0 is invalid)
        self._attr_native_min_value = 1
        self._attr_native_max_value = 255
        self._attr_native_step = 1
        self._attr_mode = NumberMode.BOX  # Use text box instead of slider
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Disable by default
        self.is_raw_value = True  # Don't divide by 10 for Modbus address
        self._attr_native_unit_of_measurement = None  # No unit for Modbus address

class FloatVoltageNumber(MidniteSolarNumber):
    """Number to set float voltage."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Float Voltage"
        self._attr_unique_id = f"{entry.entry_id}_float_voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["FLOAT_VOLTAGE_SETPOINT"]
        # Voltage range: 10V to 65V (typical for 12V, 24V, and 48V systems)
        # Register can theoretically go up to 655.3V but practical max is 65V
        self._attr_native_min_value = 10.0
        self._attr_native_max_value = 65.0
        self._attr_native_step = 0.1

class EqualizeVoltageNumber(MidniteSolarNumber):
    """Number to set equalize voltage."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQ Voltage"
        self._attr_unique_id = f"{entry.entry_id}_equalize_voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["EQUALIZE_VOLTAGE_SETPOINT"]
        # Voltage range: 10V to 65V (typical for 12V, 24V, and 48V systems)
        # Register can theoretically go up to 655.3V but practical max is 65V
        self._attr_native_min_value = 10.0
        self._attr_native_max_value = 65.0
        self._attr_native_step = 0.1

class BatteryCurrentLimitNumber(MidniteSolarNumber):
    """Number to set battery output current limit."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Current Limit"
        self._attr_unique_id = f"{entry.entry_id}_current_limit"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["BATTERY_OUTPUT_CURRENT_LIMIT"]
        # Typical current limits
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self._attr_entity_category = EntityCategory.CONFIG

class AbsorbTimeNumber(MidniteSolarNumber):
    """Number to set absorb time."""

    # The register unit differs from the entity unit; see the base class hooks.
    seconds_in_register = True

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Absorb Time"
        self._attr_unique_id = f"{entry.entry_id}_absorb_time"
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["ABSORB_TIME_EEPROM"]
        # Typical absorb times (0 = disabled)
        # Values are stored in minutes for display, but register stores seconds
        self._attr_native_min_value = 0
        self._attr_native_max_value = 300  # 5 hours in minutes
        self._attr_native_step = 1  # 1 minute increments
        self.is_time_value = True  # Don't divide by 10
        self._attr_has_entity_name = True
        self._attr_precision = 0  # Display whole numbers only
        self._attr_entity_category = EntityCategory.CONFIG
class EqualizeTimeNumber(MidniteSolarNumber):
    """Number to set equalize time."""

    # The register unit differs from the entity unit; see the base class hooks.
    seconds_in_register = True

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQ Time"
        self._attr_unique_id = f"{entry.entry_id}_equalize_time"
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["EQUALIZE_TIME_EEPROM"]
        # Typical equalize times (0 = disabled)
        # Values are stored in minutes for display, but register stores seconds
        self._attr_native_min_value = 0
        self._attr_native_max_value = 300  # 5 hours in minutes
        self._attr_native_step = 1  # 1 minute increments
        self.is_time_value = True  # Don't divide by 10
        self._attr_has_entity_name = True
        self._attr_precision = 0  # Display whole numbers only
        self._attr_entity_category = EntityCategory.CONFIG
class EqualizeIntervalDaysNumber(MidniteSolarNumber):
    """Number to set equalize interval in days."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQ Interval"
        self._attr_unique_id = f"{entry.entry_id}_equalize_interval"
        self._attr_native_unit_of_measurement = UnitOfTime.DAYS
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["EQUALIZE_INTERVAL_DAYS_EEPROM"]
        # Typical equalize intervals
        self._attr_native_min_value = 0
        self._attr_native_max_value = 365  # 1 year
        self._attr_native_step = 1
        self._attr_entity_category = EntityCategory.CONFIG

class AuxThresholdNumber(MidniteSolarNumber):
    """One Aux 1 / Aux 2 threshold: a set point in tenths of a volt or milliseconds.

    These are the levels an Aux output switches on: absolute battery voltage,
    voltage relative to the charge stage target (waste-not), or PV voltage, plus
    the delay and hold times that debounce the switching.
    """

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any, setting):
        """Initialize the number for one threshold."""
        super().__init__(coordinator, entry)
        key, name, units, tenths, minimum, maximum, step = setting
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key.lower()}"
        self._attr_native_unit_of_measurement = units
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG
        self.register_address = REGISTER_MAP[key]
        # A millisecond register holds plain counts; a volt register holds tenths.
        self.is_raw_value = not tenths
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
