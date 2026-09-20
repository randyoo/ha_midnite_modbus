"""Support for Midnite Solar number platform."""

from __future__ import annotations

import logging
from typing import Any

from .base import MidniteBaseEntityDescription

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfElectricCurrent, UnitOfTemperature, UnitOfTime
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, EE_BACKED_REGISTERS, FORCE_FLAGS, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator
from .register_values import force_flag_write, scaled_register, scaled_value

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
        # Wind power curve voltage settings
        WindPowerCurveV0Number(coordinator, entry),
        WindPowerCurveV1Number(coordinator, entry),
        WindPowerCurveV2Number(coordinator, entry),
        WindPowerCurveV3Number(coordinator, entry),
        WindPowerCurveV4Number(coordinator, entry),
        WindPowerCurveV5Number(coordinator, entry),
        WindPowerCurveV6Number(coordinator, entry),
        WindPowerCurveV7Number(coordinator, entry),
        # Wind power curve current settings
        WindPowerCurveI0Number(coordinator, entry),
        WindPowerCurveI1Number(coordinator, entry),
        WindPowerCurveI2Number(coordinator, entry),
        WindPowerCurveI3Number(coordinator, entry),
        WindPowerCurveI4Number(coordinator, entry),
        WindPowerCurveI5Number(coordinator, entry),
        WindPowerCurveI6Number(coordinator, entry),
        WindPowerCurveI7Number(coordinator, entry),
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
        """Set the value on the device."""
        register_value = self._to_register_value(value)

        _LOGGER.debug(f"Writing value {value} to register {self.register_address} (raw value: {register_value})")

        try:
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.write_register, self.register_address, register_value
            )
        except Exception as e:
            _LOGGER.error(f"Error writing to register {self.register_address}: {e}")
            raise HomeAssistantError(
                f"Could not write {self.name}: {e}"
            ) from e
        if result is None or result.isError():
            _LOGGER.error(f"Failed to write value {value} to register {self.register_address}")
            raise HomeAssistantError(
                f"The Classic rejected the write of {value} to {self.name}"
            )

        await self._async_commit_to_eeprom()

        # Request a refresh after writing
        await self.coordinator.async_request_refresh()

    async def _async_commit_to_eeprom(self) -> None:
        """Tell the Classic to store the settings it just received.

        Registers the register map marks (EE) are applied straight away but only
        written to EEPROM when ForceEEpromUpdateWriteF is sent, so without this
        the new value reverts to the old one at the next restart. The map also
        notes the commit stores every (EE) register at once, which is why it is
        done per user action and not on every poll.
        """
        if self.register_address not in EE_BACKED_REGISTERS:
            return

        flag_value = 1 << FORCE_FLAGS["ForceEEpromUpdate"]
        register, word = force_flag_write(flag_value)
        _LOGGER.debug(f"Committing {self.name} to EEPROM: 0x{word:x} to register {register}")
        try:
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.write_register, register, word
            )
        except Exception as e:
            _LOGGER.error(f"Error committing {self.name} to EEPROM: {e}")
            raise HomeAssistantError(
                f"{self.name} is active but was not saved to EEPROM: {e}"
            ) from e
        if result is None or result.isError():
            _LOGGER.error(f"Failed to commit {self.name} to EEPROM")
            raise HomeAssistantError(
                f"{self.name} is active but the Classic did not accept the EEPROM commit"
            )


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

class WindPowerCurveV0Number(MidniteSolarNumber):
    """Number to set wind power curve voltage step 0 (cut-in)."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve V0 (Cut-in)"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_v0"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_V_0_EEPA"]
        # Voltage range for wind power curve (typical: 1-200V)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 200.0
        self._attr_native_step = 1.0
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveV1Number(MidniteSolarNumber):
    """Number to set wind power curve voltage step 1."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve V1"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_v1"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_V_1_EEPA"]
        # Voltage range for wind power curve (typical: 1-200V)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 200.0
        self._attr_native_step = 1.0
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveV2Number(MidniteSolarNumber):
    """Number to set wind power curve voltage step 2."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve V2"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_v2"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_V_2_EEPA"]
        # Voltage range for wind power curve (typical: 1-200V)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 200.0
        self._attr_native_step = 1.0
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveV3Number(MidniteSolarNumber):
    """Number to set wind power curve voltage step 3."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve V3"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_v3"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_V_3_EEPA"]
        # Voltage range for wind power curve (typical: 1-200V)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 200.0
        self._attr_native_step = 1.0
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveV4Number(MidniteSolarNumber):
    """Number to set wind power curve voltage step 4."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve V4"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_v4"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_V_4_EEPA"]
        # Voltage range for wind power curve (typical: 1-200V)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 200.0
        self._attr_native_step = 1.0
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveV5Number(MidniteSolarNumber):
    """Number to set wind power curve voltage step 5."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve V5"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_v5"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_V_5_EEPA"]
        # Voltage range for wind power curve (typical: 1-200V)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 200.0
        self._attr_native_step = 1.0
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveV6Number(MidniteSolarNumber):
    """Number to set wind power curve voltage step 6."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve V6"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_v6"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_V_6_EEPA"]
        # Voltage range for wind power curve (typical: 1-200V)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 200.0
        self._attr_native_step = 1.0
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveV7Number(MidniteSolarNumber):
    """Number to set wind power curve voltage step 7."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve V7"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_v7"
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_V_7_EEPA"]
        # Voltage range for wind power curve (typical: 1-200V)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 200.0
        self._attr_native_step = 1.0
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveI0Number(MidniteSolarNumber):
    """Number to set wind power curve current step 0 (cut-in)."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve I0 (Cut-in)"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_i0"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_I_0_EEPA"]
        # Current range for wind power curve (typical: 1-100A)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self.is_raw_value = True  # Don't divide by 10 for current values in wind table
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveI1Number(MidniteSolarNumber):
    """Number to set wind power curve current step 1."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve I1"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_i1"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_I_1_EEPA"]
        # Current range for wind power curve (typical: 1-100A)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self.is_raw_value = True  # Don't divide by 10 for current values in wind table
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveI2Number(MidniteSolarNumber):
    """Number to set wind power curve current step 2."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve I2"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_i2"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_I_2_EEPA"]
        # Current range for wind power curve (typical: 1-100A)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self.is_raw_value = True  # Don't divide by 10 for current values in wind table
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveI3Number(MidniteSolarNumber):
    """Number to set wind power curve current step 3."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve I3"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_i3"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_I_3_EEPA"]
        # Current range for wind power curve (typical: 1-100A)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self.is_raw_value = True  # Don't divide by 10 for current values in wind table
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveI4Number(MidniteSolarNumber):
    """Number to set wind power curve current step 4."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve I4"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_i4"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_I_4_EEPA"]
        # Current range for wind power curve (typical: 1-100A)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self.is_raw_value = True  # Don't divide by 10 for current values in wind table
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveI5Number(MidniteSolarNumber):
    """Number to set wind power curve current step 5."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve I5"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_i5"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_I_5_EEPA"]
        # Current range for wind power curve (typical: 1-100A)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self.is_raw_value = True  # Don't divide by 10 for current values in wind table
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveI6Number(MidniteSolarNumber):
    """Number to set wind power curve current step 6."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve I6"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_i6"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_I_6_EEPA"]
        # Current range for wind power curve (typical: 1-100A)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self.is_raw_value = True  # Don't divide by 10 for current values in wind table
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

class WindPowerCurveI7Number(MidniteSolarNumber):
    """Number to set wind power curve current step 7."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Wind Power Curve I7"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_curve_i7"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["WIND_POWER_TABLE_I_7_EEPA"]
        # Current range for wind power curve (typical: 1-100A)
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self.is_raw_value = True  # Don't divide by 10 for current values in wind table
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

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