"""Support for Midnite Solar select platform."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import MidniteBaseEntityDescription

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    AUX1_FUNCTIONS,
    AUX2_FUNCTIONS,
    DEVICE_TYPES,
    DOMAIN,
    FORCE_FLAGS,
    MPPT_MODES,
    REGISTER_MAP,
)
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
        Aux1FunctionSelector(coordinator, entry),
        Aux2FunctionSelector(coordinator, entry),
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
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Move to Diagnostics category
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


class Aux1FunctionSelector(MidniteSolarSelect):
    """Selector for AUX 1 function control."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX 1 Function"
        self._attr_unique_id = f"{entry.entry_id}_aux1_function_selector"
        # Convert AUX1_FUNCTIONS list to options
        self._attr_options = AUX1_FUNCTIONS
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        if self.coordinator.data and "data" in self.coordinator.data:
            aux_settings = self.coordinator.data["data"].get("aux_settings")
            if aux_settings:
                value = aux_settings.get(REGISTER_MAP["AUX_1_AND_2_FUNCTION"])
                if value is not None:
                    # Extract AUX 1 function (bits 0-2)
                    aux1_function_value = value & 0x07
                    return AUX1_FUNCTIONS[aux1_function_value] if aux1_function_value < len(AUX1_FUNCTIONS) else f"Unknown ({aux1_function_value})"
        return "Off"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find the index of the option in AUX1_FUNCTIONS
        try:
            function_index = AUX1_FUNCTIONS.index(option)
        except ValueError:
            _LOGGER.warning(f"Unknown AUX 1 function option: {option}")
            return

        if self.coordinator.data and "data" in self.coordinator.data:
            aux_settings = self.coordinator.data["data"].get("aux_settings")
            if aux_settings:
                # Read current value to preserve AUX 2 function bits
                current_value = aux_settings.get(REGISTER_MAP["AUX_1_AND_2_FUNCTION"])
                if current_value is not None:
                    # Preserve AUX 2 function (bits 3-5) and ON/OFF bit (bit 8)
                    aux2_function_bits = (current_value >> 3) & 0x07
                    on_off_bit = (current_value >> 8) & 0x01
                    
                    # Build new value with AUX 1 function, preserved AUX 2 function, and ON/OFF bit
                    new_value = (function_index & 0x07) | ((aux2_function_bits & 0x07) << 3) | ((on_off_bit & 0x01) << 8)
                    
                    _LOGGER.info(f"Setting AUX 1 function to {option} (value: {new_value})")
                    try:
                        result = await self.hass.async_add_executor_job(
                            self.coordinator.api.write_register, REGISTER_MAP["AUX_1_AND_2_FUNCTION"], new_value
                        )
                        if not result or result.isError():
                            _LOGGER.error(f"Failed to write AUX 1 function {option} to register")
                    except Exception as e:
                        _LOGGER.error(f"Error writing AUX 1 function {option} to register: {e}")
                    
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
                else:
                    _LOGGER.warning("Current AUX settings not available, cannot preserve AUX 2 function")
        else:
            _LOGGER.warning("Coordinator data not available")


class Aux2FunctionSelector(MidniteSolarSelect):
    """Selector for AUX 2 function control."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX 2 Function"
        self._attr_unique_id = f"{entry.entry_id}_aux2_function_selector"
        # Convert AUX2_FUNCTIONS list to options
        self._attr_options = AUX2_FUNCTIONS
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        if self.coordinator.data and "data" in self.coordinator.data:
            aux_settings = self.coordinator.data["data"].get("aux_settings")
            if aux_settings:
                value = aux_settings.get(REGISTER_MAP["AUX_1_AND_2_FUNCTION"])
                if value is not None:
                    # Extract AUX 2 function (bits 3-5)
                    aux2_function_value = (value >> 3) & 0x07
                    return AUX2_FUNCTIONS[aux2_function_value] if aux2_function_value < len(AUX2_FUNCTIONS) else f"Unknown ({aux2_function_value})"
        return "Off"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find the index of the option in AUX2_FUNCTIONS
        try:
            function_index = AUX2_FUNCTIONS.index(option)
        except ValueError:
            _LOGGER.warning(f"Unknown AUX 2 function option: {option}")
            return

        if self.coordinator.data and "data" in self.coordinator.data:
            aux_settings = self.coordinator.data["data"].get("aux_settings")
            if aux_settings:
                # Read current value to preserve AUX 1 function bits
                current_value = aux_settings.get(REGISTER_MAP["AUX_1_AND_2_FUNCTION"])
                if current_value is not None:
                    # Preserve AUX 1 function (bits 0-2) and ON/OFF bit (bit 8)
                    aux1_function_bits = current_value & 0x07
                    on_off_bit = (current_value >> 8) & 0x01
                    
                    # Build new value with AUX 2 function, preserved AUX 1 function, and ON/OFF bit
                    new_value = (aux1_function_bits & 0x07) | ((function_index & 0x07) << 3) | ((on_off_bit & 0x01) << 8)
                    
                    _LOGGER.info(f"Setting AUX 2 function to {option} (value: {new_value})")
                    try:
                        result = await self.hass.async_add_executor_job(
                            self.coordinator.api.write_register, REGISTER_MAP["AUX_1_AND_2_FUNCTION"], new_value
                        )
                        if not result or result.isError():
                            _LOGGER.error(f"Failed to write AUX 2 function {option} to register")
                    except Exception as e:
                        _LOGGER.error(f"Error writing AUX 2 function {option} to register: {e}")
                    
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
                else:
                    _LOGGER.warning("Current AUX settings not available, cannot preserve AUX 1 function")
        else:
            _LOGGER.warning("Coordinator data not available")
