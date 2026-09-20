"""Support for Midnite Solar text input platform."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.text import TextEntity
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
    """Set up Midnite Solar text inputs."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    texts = [
        HostNameText(coordinator, entry),
    ]
    
    async_add_entities(texts)


class MidniteSolarText(CoordinatorEntity[MidniteSolarUpdateCoordinator], TextEntity):
    """Base class for all Midnite Solar text inputs."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the text input."""
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
                    
                    # Get PCB revision from UNIT_ID register (bits 8-15)
                    pcb_revision = None
                    if unit_id_value is not None:
                        pcb_revision = (unit_id_value >> 8) & 0xFF
                    
                    # Get software build date
                    sw_date_ro = device_info_data.get(REGISTER_MAP["UNIT_SW_DATE_RO"])
                    sw_date_month_day = device_info_data.get(REGISTER_MAP["UNIT_SW_DATE_MONTH_DAY"])
                    sw_build_date = None
                    if sw_date_ro is not None and sw_date_month_day is not None:
                        # Format: YYYY-MM-DD from two registers
                        # Register 4102 contains year, register 4103 has MSB=month, LSB=day
                        year = sw_date_ro & 0xFFFF  # Get full 16-bit value for year
                        month = (sw_date_month_day >> 8) & 0xFF  # Extract high byte (MSB)
                        day = sw_date_month_day & 0xFF  # Extract low byte (LSB)
                        
                        try:
                            sw_build_date = f"{year:04d}-{month:02d}-{day:02d}"
                        except (ValueError, TypeError) as e:
                            _LOGGER.warning(f"Failed to format software build date: year={year}, month={month}, day={day}. Error: {e}")
                    
                    return {
                        "identifiers": {(DOMAIN, str(device_id))},
                        "name": f"{model} ({device_id})",
                        "manufacturer": "Midnite Solar",
                        "model": model,
                        "hw_version": f"PCB {pcb_revision}" if pcb_revision is not None else None,
                        "sw_version": sw_build_date,
                    }
        
        # Fallback to entry_id if device ID not available
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def native_value(self) -> Optional[str]:
        """Return the current value."""
        # Read the unit name from registers 4210-4213
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                reg_0 = device_info_data.get(REGISTER_MAP["UNIT_NAME_0"])
                reg_1 = device_info_data.get(REGISTER_MAP["UNIT_NAME_1"])
                reg_2 = device_info_data.get(REGISTER_MAP["UNIT_NAME_2"])
                reg_3 = device_info_data.get(REGISTER_MAP["UNIT_NAME_3"])
                
                if all(r is not None for r in [reg_0, reg_1, reg_2, reg_3]):
                    # Each register contains 2 bytes of ASCII characters
                    # Registers are little-endian: LSB = char 0/2/4/6, MSB = char 1/3/5/7
                    chars = []
                    
                    def get_bytes(reg_value):
                        """Extract two bytes from a 16-bit register value."""
                        # LSB (low byte) first, then MSB (high byte)
                        return [reg_value & 0xFF, (reg_value >> 8) & 0xFF]
                    
                    chars.extend(get_bytes(reg_0))
                    chars.extend(get_bytes(reg_1))
                    chars.extend(get_bytes(reg_2))
                    chars.extend(get_bytes(reg_3))
                    
                    # Filter out null/zero bytes and convert to string
                    name = "".join(chr(c) for c in chars if c != 0)
                    return name.strip()
        return None

    async def _async_set_value(self, value: str) -> None:
        """Set the value on the device."""
        # Ensure the value is exactly 8 characters, pad with spaces if needed
        padded_value = (value[:8].ljust(8))
        
        try:
            # Write each pair of characters to a register
            # Each register holds 2 ASCII characters (16 bits)
            for i in range(4):
                start_idx = i * 2
                char1 = padded_value[start_idx]
                char2 = padded_value[start_idx + 1]
                
                # Combine two characters into a 16-bit value
                # Device uses little-endian format: LSB = first char, MSB = second char
                register_value = ord(char1) | (ord(char2) << 8)
                
                register_address = REGISTER_MAP[f"UNIT_NAME_{i}"]
                result = await self.hass.async_add_executor_job(
                    self.coordinator.api.write_register, register_address, register_value
                )
                if not result or result.isError():
                    _LOGGER.error(f"Failed to write value {padded_value} to register {register_address}")
                    return False
        except Exception as e:
            _LOGGER.error(f"Error writing host name: {e}")
            return False
        
        # After writing the name, we need to force an EEPROM update
        # This saves the changes to non-volatile memory
        try:
            force_value = 1 << 2  # ForceEEpromUpdate flag (bit 2)
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.write_register, REGISTER_MAP["FORCE_FLAG_BITS"], force_value
            )
            if not result or result.isError():
                _LOGGER.error("Failed to trigger EEPROM update")
                return False
        except Exception as e:
            _LOGGER.error(f"Error triggering EEPROM update: {e}")
            return False
        
        # Request a refresh after writing
        await self.coordinator.async_request_refresh()
        return True


class HostNameText(MidniteSolarText):
    """Text input to set the host name."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the text input."""
        super().__init__(coordinator, entry)
        self._attr_name = "Host Name"
        self._attr_unique_id = f"{entry.entry_id}_host_name"
        self._attr_max_length = 8
        self._attr_pattern = r"^[A-Za-z0-9_\-\. ]*$"  # Alphanumeric, underscore, hyphen, dot, space

    async def async_set_value(self, value: str) -> None:
        """Update the current value."""
        await self._async_set_value(value)
