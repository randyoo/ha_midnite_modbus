"""Support for Midnite Solar number platform."""

from __future__ import annotations

import logging
from typing import Any

from .base import MidniteBaseEntityDescription

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfElectricCurrent, UnitOfTemperature, UnitOfTime
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPES, DOMAIN, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator

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
        EqualizeTimeNumber(coordinator, entry),
        EqualizeIntervalDaysNumber(coordinator, entry),
        ModbusAddressNumber(coordinator, entry),
    ]
    
    async_add_entities(numbers)


class MidniteSolarNumber(CoordinatorEntity[MidniteSolarUpdateCoordinator], NumberEntity):
    """Base class for all Midnite Solar numbers."""

    _attr_native_min_value: float | None = None
    _attr_native_max_value: float | None = None
    _attr_native_step: float | None = None

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

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            # Convert from register value (divide by 10 for voltage/current)
            # Time values should NOT be divided by 10
            if hasattr(self, 'is_time_value') and self.is_time_value:
                return float(value)
            else:
                return float(value) / 10.0
        else:
            _LOGGER.debug(f"Modbus address value is None for register {self.register_address}")
            # Check if coordinator has data at all
            if self.coordinator.data and "data" in self.coordinator.data:
                _LOGGER.debug(f"Coordinator data keys: {list(self.coordinator.data['data'].keys())}")
        return None

    async def _async_set_value(self, value: float) -> None:
        """Set the value on the device."""
        # Convert to register value (multiply by 10 for voltage/current)
        # Time values should NOT be multiplied by 10
        if hasattr(self, 'is_time_value') and self.is_time_value:
            register_value = int(value)
        else:
            register_value = int(value * 10)
        
        _LOGGER.debug(f"Writing Modbus address {value} to register {self.register_address} (raw value: {register_value})")
        
        try:
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.write_register, self.register_address, register_value
            )
            if not result or result.isError():
                _LOGGER.error(f"Failed to write value {value} to register {self.register_address}")
                return False
        except Exception as e:
            _LOGGER.error(f"Error writing to register {self.register_address}: {e}")
            return False
        
        # Request a refresh after writing
        await self.coordinator.async_request_refresh()
        return True


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

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


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
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Disable by default

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


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

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


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

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class BatteryCurrentLimitNumber(MidniteSolarNumber):
    """Number to set battery output current limit."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Max Battery Amps"
        self._attr_unique_id = f"{entry.entry_id}_current_limit"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["BATTERY_OUTPUT_CURRENT_LIMIT"]
        # Typical current limits
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class AbsorbTimeNumber(MidniteSolarNumber):
    """Number to set absorb time."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Absorb Time"
        self._attr_unique_id = f"{entry.entry_id}_absorb_time"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["ABSORB_TIME_EEPROM"]
        # Typical absorb times (0 = disabled)
        self._attr_native_min_value = 0
        self._attr_native_max_value = 7200  # 2 hours
        self._attr_native_step = 60  # 1 minute increments
        self.is_time_value = True  # Don't divide by 10

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class EqualizeTimeNumber(MidniteSolarNumber):
    """Number to set equalize time."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQ Time"
        self._attr_unique_id = f"{entry.entry_id}_equalize_time"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_mode = NumberMode.BOX
        self.register_address = REGISTER_MAP["EQUALIZE_TIME_EEPROM"]
        # Typical equalize times (0 = disabled)
        self._attr_native_min_value = 0
        self._attr_native_max_value = 7200  # 2 hours
        self._attr_native_step = 60  # 1 minute increments
        self.is_time_value = True  # Don't divide by 10

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


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

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)
