"""Support for Midnite Solar select platform."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import MidniteBaseEntityDescription

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPES, DOMAIN, FORCE_FLAGS, MPPT_MODES, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar selectors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    selectors = [
        ChargeModeSelector(coordinator, entry),
        MPPTModeSelector(coordinator, entry),
    ]
    
    async_add_entities(selectors)


class MidniteSolarSelect(CoordinatorEntity[MidniteSolarUpdateCoordinator], SelectEntity):
    """Base class for all Midnite Solar selectors."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
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
        return MidniteBaseEntityDescription.get_device_info(
            self.coordinator, self._entry, DOMAIN
        )


class ChargeModeSelector(MidniteSolarSelect):
    """Selector for force charge mode control."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "Force Charge Mode"
        self._attr_unique_id = f"{entry.entry_id}_charge_mode_selector"
        self._attr_options = ["None", "Float", "Bulk", "Equalize"]

    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        # Check which force flag is active by reading the charge stage
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                raw_value = status_data.get(REGISTER_MAP["COMBO_CHARGE_STAGE"])
                if raw_value is not None:
                    # Extract MSB (high byte) for charge stage
                    charge_stage_value = (raw_value >> 8) & 0xFF
                    
                    # Map charge stages to mode names
                    if charge_stage_value == 5:  # Float
                        return "Float"
                    elif charge_stage_value == 4:  # BulkMPPT
                        return "Bulk"
                    elif charge_stage_value == 7:  # Equalize
                        return "Equalize"
        
        return "None"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == "None":
            _LOGGER.info("Force charge mode control: No action")
            return
        
        # Map option to force flag
        flag_map = {
            "Float": FORCE_FLAGS["ForceFloat"],
            "Bulk": FORCE_FLAGS["ForceBulk"],
            "Equalize": FORCE_FLAGS["ForceEqualize"],
        }
        
        flag_bit = flag_map.get(option)
        if flag_bit is not None:
            flag_value = 1 << flag_bit
            _LOGGER.info(f"Forcing {option} mode with value: {flag_value} (0x{flag_value:x})")
            try:
                result = await self.hass.async_add_executor_job(
                    self.coordinator.api.write_register, REGISTER_MAP["FORCE_FLAG_BITS"], flag_value
                )
                if not result or result.isError():
                    _LOGGER.error(f"Failed to write {option} mode to force register")
            except Exception as e:
                _LOGGER.error(f"Error writing {option} mode to force register: {e}")
        
        # Request a refresh after changing mode
        await self.coordinator.async_request_refresh()


class MPPTModeSelector(MidniteSolarSelect):
    """Selector for MPPT mode control."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "MPPT Mode"
        self._attr_unique_id = f"{entry.entry_id}_mppt_mode_selector"
        # Convert MPPT_MODES dict to list of options
        self._attr_options = list(MPPT_MODES.values())
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        if self.coordinator.data and "data" in self.coordinator.data:
            settings = self.coordinator.data["data"].get("settings")
            if settings:
                value = settings.get(REGISTER_MAP["MPPT_MODE"])
                if value is not None:
                    return MPPT_MODES.get(value, f"Unknown (0x{value:04X})")
        return "PV_Uset"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Map option name back to value
        for value, name in MPPT_MODES.items():
            if name == option:
                _LOGGER.info(f"Setting MPPT mode to {option} (0x{value:04X})")
                try:
                    result = await self.hass.async_add_executor_job(
                        self.coordinator.api.write_register, REGISTER_MAP["MPPT_MODE"], value
                    )
                    if not result or result.isError():
                        _LOGGER.error(f"Failed to write MPPT mode {option} to register")
                except Exception as e:
                    _LOGGER.error(f"Error writing MPPT mode {option} to register: {e}")
                
                # After writing the mode, we need to force an EEPROM update
                try:
                    force_value = 1 << 2  # ForceEEpromUpdate flag (bit 2)
                    result = await self.hass.async_add_executor_job(
                        self.coordinator.api.write_register, REGISTER_MAP["FORCE_FLAG_BITS"], force_value
                    )
                    if not result or result.isError():
                        _LOGGER.error("Failed to trigger EEPROM update")
                except Exception as e:
                    _LOGGER.error(f"Error triggering EEPROM update: {e}")
                
                # Request a refresh after changing mode
                await self.coordinator.async_request_refresh()
                return
        
        _LOGGER.warning(f"Unknown MPPT mode option: {option}")
