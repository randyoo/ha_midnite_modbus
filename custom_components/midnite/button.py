"""Support for Midnite Solar button platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, FORCE_FLAGS, REGISTER_MAP
from . import MidniteAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar buttons."""
    api = entry.runtime_data
    
    buttons = [
        ForceFloatButton(api, entry),
        ForceBulkButton(api, entry),
        ForceEqualizeButton(api, entry),
        ForceEEpromUpdateButton(api, entry),
        ResetFaultsButton(api, entry),
        ResetFlagsButton(api, entry),
    ]
    
    async_add_entities(buttons)


class MidniteSolarButton(ButtonEntity):
    """Base class for all Midnite Solar buttons."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the button."""
        self._api = api
        self._entry = entry
        # Use device_info from API if available, otherwise create basic one
        if hasattr(api, 'device_info') and api.device_info.get('identifiers'):
            self._attr_device_info = api.device_info
        else:
            self._attr_device_info = {
                "identifiers": {(DOMAIN, entry.entry_id)},
                "name": entry.title,
                "manufacturer": "Midnite Solar",
            }


class ForceFloatButton(MidniteSolarButton):
    """Button to force the device into float mode."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the button."""
        super().__init__(api, entry)
        self._attr_name = "Force Float"
        self._attr_unique_id = f"{entry.entry_id}_force_float"

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ForceFloat"]
        _LOGGER.info(f"Forcing Float mode with value: {flag_value} (0x{flag_value:x})")
        success = await self._api.write_register(REGISTER_MAP["FORCE_FLAG_BITS"], flag_value)
        if not success:
            _LOGGER.error("Failed to write to force register")


class ForceBulkButton(MidniteSolarButton):
    """Button to force the device into bulk mode."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the button."""
        super().__init__(api, entry)
        self._attr_name = "Force Bulk"
        self._attr_unique_id = f"{entry.entry_id}_force_bulk"

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ForceBulk"]
        _LOGGER.info(f"Forcing Bulk mode with value: {flag_value} (0x{flag_value:x})")
        success = await self._api.write_register(REGISTER_MAP["FORCE_FLAG_BITS"], flag_value)
        if not success:
            _LOGGER.error("Failed to write to force register")


class ForceEqualizeButton(MidniteSolarButton):
    """Button to force the device into equalize mode."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the button."""
        super().__init__(api, entry)
        self._attr_name = "Force Equalize"
        self._attr_unique_id = f"{entry.entry_id}_force_equalize"

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ForceEqualize"]
        _LOGGER.info(f"Forcing Equalize mode with value: {flag_value} (0x{flag_value:x})")
        success = await self._api.write_register(REGISTER_MAP["FORCE_FLAG_BITS"], flag_value)
        if not success:
            _LOGGER.error("Failed to write to force register")


class ForceEEpromUpdateButton(MidniteSolarButton):
    """Button to force an EEPROM update."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the button."""
        super().__init__(api, entry)
        self._attr_name = "Force EEPROM Update"
        self._attr_unique_id = f"{entry.entry_id}_force_eeprom_update"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ForceEEpromUpdate"]
        _LOGGER.info(f"Forcing EEPROM update with value: {flag_value} (0x{flag_value:x})")
        success = await self._api.write_register(REGISTER_MAP["FORCE_FLAG_BITS"], flag_value)
        if not success:
            _LOGGER.error("Failed to write to force register")


class ResetFaultsButton(MidniteSolarButton):
    """Button to reset faults."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the button."""
        super().__init__(api, entry)
        self._attr_name = "Reset Faults"
        self._attr_unique_id = f"{entry.entry_id}_reset_faults"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ForceResetFaults"]
        _LOGGER.info(f"Resetting faults with value: {flag_value} (0x{flag_value:x})")
        success = await self._api.write_register(REGISTER_MAP["FORCE_FLAG_BITS"], flag_value)
        if not success:
            _LOGGER.error("Failed to write to force register")


class ResetFlagsButton(MidniteSolarButton):
    """Button to reset flags."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the button."""
        super().__init__(api, entry)
        self._attr_name = "Reset Flags"
        self._attr_unique_id = f"{entry.entry_id}_reset_flags"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Press the button."""
        flag_value = 1 << FORCE_FLAGS["ResetFlags"]
        _LOGGER.info(f"Resetting flags with value: {flag_value} (0x{flag_value:x})")
        success = await self._api.write_register(REGISTER_MAP["FORCE_FLAG_BITS"], flag_value)
        if not success:
            _LOGGER.error("Failed to write to force register")
