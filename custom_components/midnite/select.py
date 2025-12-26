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
        INFO_FLAGS_BITS2_1Select(coordinator, entry),
        INFO_FLAGS_BITS2_0Select(coordinator, entry),
        USB_COMM_MODESelect(coordinator, entry),
        MPPT_MODESelect(coordinator, entry),
        AUX_1_AND_2_FUNCTIONSelect(coordinator, entry),
        ENABLE_FLAGS2Select(coordinator, entry),
        ENABLE_FLAGS_BITSSelect(coordinator, entry),
        LED_MODE_EEPROMSelect(coordinator, entry),
        REMOTE_MENU_MODESelect(coordinator, entry),
        FLAGS_RD_32BITSelect(coordinator, entry),
        I_FLAGS_RO_HIGHSelect(coordinator, entry),
        IP_SETTINGS_FLAGSSelect(coordinator, entry),
    ]
    
    async_add_entities(selectors)

    @property
    def options(self) -> list[str] | None:
        """Return the select options."""
        # Default implementation - subclasses should override this
        return ["Option 1", "Option 2", "Option 3"]


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
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

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


class INFO_FLAGS_BITS2_1Select(MidniteSolarSelect):
    """Representation of a 32-bit info flags (low word) selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "INFO_FLAGS_BITS2_1"
        self._attr_unique_id = f"{entry.entry_id}_info_flags_bits2_1_select"
        self._attr_icon = "mdi:cog"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class INFO_FLAGS_BITS2_0Select(MidniteSolarSelect):
    """Representation of a 32-bit info flags (high word) selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "INFO_FLAGS_BITS2_0"
        self._attr_unique_id = f"{entry.entry_id}_info_flags_bits2_0_select"
        self._attr_icon = "mdi:cog"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class USB_COMM_MODESelect(MidniteSolarSelect):
    """Representation of a usb function # selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "USB_COMM_MODE"
        self._attr_unique_id = f"{entry.entry_id}_usb_comm_mode_select"
        self._attr_icon = "mdi:usb-port"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class MPPT_MODESelect(MidniteSolarSelect):
    """Representation of a solar, wind, etc. (bit 0 = on/off) selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "MPPT_MODE"
        self._attr_unique_id = f"{entry.entry_id}_mppt_mode_select"
        self._attr_icon = "mdi:cog"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class AUX_1_AND_2_FUNCTIONSelect(MidniteSolarSelect):
    """Representation of a combined aux 1 & 2 function + on/off selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX_1_AND_2_FUNCTION"
        self._attr_unique_id = f"{entry.entry_id}_aux_1_and_2_function_select"
        self._attr_icon = "mdi:radiobox-marked"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class ENABLE_FLAGS2Select(MidniteSolarSelect):
    """Representation of a various feature flags selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "ENABLE_FLAGS2"
        self._attr_unique_id = f"{entry.entry_id}_enable_flags2_select"
        self._attr_icon = "mdi:cog"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class ENABLE_FLAGS_BITSSelect(MidniteSolarSelect):
    """Representation of a legacy flags moved to enableflags2 selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "ENABLE_FLAGS_BITS"
        self._attr_unique_id = f"{entry.entry_id}_enable_flags_bits_select"
        self._attr_icon = "mdi:cog"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class LED_MODE_EEPROMSelect(MidniteSolarSelect):
    """Representation of a led display mode selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "LED_MODE_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_led_mode_eeprom_select"
        self._attr_icon = "mdi:cog"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class REMOTE_MENU_MODESelect(MidniteSolarSelect):
    """Representation of a remote menu sent from mngp selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "REMOTE_MENU_MODE"
        self._attr_unique_id = f"{entry.entry_id}_remote_menu_mode_select"
        self._attr_icon = "mdi:cog"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class FLAGS_RD_32BITSelect(MidniteSolarSelect):
    """Representation of a internal status flags (32-bit) selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "FLAGS_RD_32BIT"
        self._attr_unique_id = f"{entry.entry_id}_flags_rd_32bit_select"
        self._attr_icon = "mdi:cog"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class I_FLAGS_RO_HIGHSelect(MidniteSolarSelect):
    """Representation of a follow-me high bits - charge stage coordination selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "I_FLAGS_RO_HIGH"
        self._attr_unique_id = f"{entry.entry_id}_i_flags_ro_high_select"
        self._attr_icon = "mdi:cog"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None


class IP_SETTINGS_FLAGSSelect(MidniteSolarSelect):
    """Representation of a network settings flags - see table 20481-1 (dhcp, web access) selector."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "IP_SETTINGS_FLAGS"
        self._attr_unique_id = f"{entry.entry_id}_ip_settings_flags_select"
        self._attr_icon = "mdi:cog"

    @property
    @property
    def options(self) -> list[str]:
        """Return the select options."""
        return ["Option 1", "Option 2", "Option 3"]

    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None
