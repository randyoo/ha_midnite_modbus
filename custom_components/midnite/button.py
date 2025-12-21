"""Support for Midnite Solar button platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPES, DOMAIN, FORCE_FLAGS, REGISTER_MAP
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
        
        # Create device info - will be updated dynamically when data becomes available
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def device_info(self):
        """Return dynamic device info with device ID and model if available."""
        # Try to get device ID from coordinator data (registers 4111-4112)
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                device_id_lsw = device_info_data.get(REGISTER_MAP["DEVICE_ID_LSW"])
                device_id_msw = device_info_data.get(REGISTER_MAP["DEVICE_ID_MSW"])
                if device_id_lsw is not None and device_id_msw is not None:
                    device_id = (device_id_msw << 16) | device_id_lsw
                    # Try to get device model from UNIT_ID register
                    unit_id_value = device_info_data.get(REGISTER_MAP["UNIT_ID"])
                    if unit_id_value is not None:
                        device_type = unit_id_value & 0xFF  # Get LSB (unit type)
                        model = DEVICE_TYPES.get(device_type, f"Unknown ({device_type})")
                    else:
                        model = "Midnite Solar Device"
                    
                    return {
                        "identifiers": {(DOMAIN, str(device_id))},
                        "name": f"{model} ({device_id})",
                        "manufacturer": "Midnite Solar",
                        "model": model,
                    }
        
        # Fallback to entry_id if serial number not available
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Midnite Solar",
        }


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
