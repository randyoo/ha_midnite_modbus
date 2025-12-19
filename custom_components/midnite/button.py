"""Support for Midnite Solar button platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FORCE_FLAGS, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    buttons = [
        ForceFloatButton(coordinator, entry),
        ForceBulkButton(coordinator, entry),
        ForceEqualizeButton(coordinator, entry),
        ForceEEpromUpdateButton(coordinator, entry),
        ResetFaultsButton(coordinator, entry),
        ResetFlagsButton(coordinator, entry),
    ]
    
    async_add_entities(buttons)


class MidniteSolarButton(CoordinatorEntity[MidniteSolarUpdateCoordinator], ButtonEntity):
    """Base class for all Midnite Solar buttons."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        
        # Create device info based on available data
        if coordinator.data and "data" in coordinator.data:
            # Try to extract serial number from device_info registers
            device_info_data = coordinator.data["data"].get("device_info")
            if device_info_data:
                # Check for serial number (32-bit value)
                serial_msb = device_info_data.get(REGISTER_MAP["SERIAL_NUMBER_MSB"])
                serial_lsb = device_info_data.get(REGISTER_MAP["SERIAL_NUMBER_LSB"])
                if serial_msb is not None and serial_lsb is not None:
                    serial_number = (serial_msb << 16) | serial_lsb
                    self._attr_device_info = {
                        "identifiers": {(DOMAIN, str(serial_number))},
                        "name": f"Midnite Solar ({serial_number})",
                        "manufacturer": "Midnite Solar",
                    }
                else:
                    # Fallback to hostname
                    self._attr_device_info = {
                        "identifiers": {(DOMAIN, entry.entry_id)},
                        "name": entry.title,
                        "manufacturer": "Midnite Solar",
                    }
            else:
                self._attr_device_info = {
                    "identifiers": {(DOMAIN, entry.entry_id)},
                    "name": entry.title,
                    "manufacturer": "Midnite Solar",
                }
        else:
            self._attr_device_info = {
                "identifiers": {(DOMAIN, entry.entry_id)},
                "name": entry.title,
                "manufacturer": "Midnite Solar",
            }


class ForceFloatButton(MidniteSolarButton):
    """Button to force the device into float mode."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Force Float"
        self._attr_unique_id = f"{entry.entry_id}_force_float"

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ForceFloat"]
        _LOGGER.info(f"Forcing Float mode with value: {flag_value} (0x{flag_value:x})")
        try:
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.write_register, REGISTER_MAP["FORCE_FLAG_BITS"], flag_value
            )
            if not result or result.isError():
                _LOGGER.error("Failed to write to force register")
        except Exception as e:
            _LOGGER.error(f"Error writing to force register: {e}")


class ForceBulkButton(MidniteSolarButton):
    """Button to force the device into bulk mode."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Force Bulk"
        self._attr_unique_id = f"{entry.entry_id}_force_bulk"

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ForceBulk"]
        _LOGGER.info(f"Forcing Bulk mode with value: {flag_value} (0x{flag_value:x})")
        try:
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.write_register, REGISTER_MAP["FORCE_FLAG_BITS"], flag_value
            )
            if not result or result.isError():
                _LOGGER.error("Failed to write to force register")
        except Exception as e:
            _LOGGER.error(f"Error writing to force register: {e}")


class ForceEqualizeButton(MidniteSolarButton):
    """Button to force the device into equalize mode."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Force Equalize"
        self._attr_unique_id = f"{entry.entry_id}_force_equalize"

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ForceEqualize"]
        _LOGGER.info(f"Forcing Equalize mode with value: {flag_value} (0x{flag_value:x})")
        try:
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.write_register, REGISTER_MAP["FORCE_FLAG_BITS"], flag_value
            )
            if not result or result.isError():
                _LOGGER.error("Failed to write to force register")
        except Exception as e:
            _LOGGER.error(f"Error writing to force register: {e}")


class ForceEEpromUpdateButton(MidniteSolarButton):
    """Button to force an EEPROM update."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Force EEPROM Update"
        self._attr_unique_id = f"{entry.entry_id}_force_eeprom_update"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ForceEEpromUpdate"]
        _LOGGER.info(f"Forcing EEPROM update with value: {flag_value} (0x{flag_value:x})")
        try:
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.write_register, REGISTER_MAP["FORCE_FLAG_BITS"], flag_value
            )
            if not result or result.isError():
                _LOGGER.error("Failed to write to force register")
        except Exception as e:
            _LOGGER.error(f"Error writing to force register: {e}")


class ResetFaultsButton(MidniteSolarButton):
    """Button to reset faults."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Reset Faults"
        self._attr_unique_id = f"{entry.entry_id}_reset_faults"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ForceResetFaults"]
        _LOGGER.info(f"Resetting faults with value: {flag_value} (0x{flag_value:x})")
        try:
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.write_register, REGISTER_MAP["FORCE_FLAG_BITS"], flag_value
            )
            if not result or result.isError():
                _LOGGER.error("Failed to write to force register")
        except Exception as e:
            _LOGGER.error(f"Error writing to force register: {e}")


class ResetFlagsButton(MidniteSolarButton):
    """Button to reset flags."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Reset Flags"
        self._attr_unique_id = f"{entry.entry_id}_reset_flags"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ResetFlags"]
        _LOGGER.info(f"Resetting flags with value: {flag_value} (0x{flag_value:x})")
        try:
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.write_register, REGISTER_MAP["FORCE_FLAG_BITS"], flag_value
            )
            if not result or result.isError():
                _LOGGER.error("Failed to write to force register")
        except Exception as e:
            _LOGGER.error(f"Error writing to force register: {e}")
