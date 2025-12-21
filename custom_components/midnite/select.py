"""Support for Midnite Solar select platform."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.select import SelectEntity
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
    """Set up Midnite Solar selectors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    selectors = [
        ChargeModeSelector(coordinator, entry),
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
        
        # Fallback to entry_id if device ID not available
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Midnite Solar",
        }


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
