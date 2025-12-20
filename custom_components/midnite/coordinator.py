"""Define the Midnite Solar Device Update Coordinator."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

import pymodbus

if "3.7.0" <= pymodbus.__version__ <= "3.7.4":
    from pymodbus.pdu.register_read_message import ReadHoldingRegistersResponse
else:
    from pymodbus.pdu.register_message import ReadHoldingRegistersResponse

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, REGISTER_MAP
from .hub import MidniteHub

_LOGGER = logging.getLogger(__name__)

# Define the register groups we need to read
REGISTER_GROUPS = {
    "device_info": [
        REGISTER_MAP["UNIT_ID"],
        REGISTER_MAP["SERIAL_NUMBER_MSB"],
        REGISTER_MAP["SERIAL_NUMBER_LSB"],
        REGISTER_MAP["DEVICE_ID_LSW"],
        REGISTER_MAP["DEVICE_ID_MSW"],
    ],
    "status": [
        REGISTER_MAP["DISP_AVG_VBATT"],
        REGISTER_MAP["DISP_AVG_VPV"],
        REGISTER_MAP["IBATT_DISPLAY_S"],
        REGISTER_MAP["WATTS"],
        REGISTER_MAP["COMBO_CHARGE_STAGE"],
        REGISTER_MAP["PV_INPUT_CURRENT"],
        REGISTER_MAP["VOC_LAST_MEASURED"],
    ],
    "temperatures": [
        REGISTER_MAP["BATT_TEMPERATURE"],
        REGISTER_MAP["FET_TEMPERATURE"],
        REGISTER_MAP["PCB_TEMPERATURE"],
    ],
    "energy": [
        REGISTER_MAP["AMP_HOURS_DAILY"],
        REGISTER_MAP["LIFETIME_KW_HOURS_1"],
        REGISTER_MAP["LIFETIME_KW_HOURS_1"] + 1,  # High word
        REGISTER_MAP["LIFETIME_AMP_HOURS_1"],
        REGISTER_MAP["LIFETIME_AMP_HOURS_1"] + 1,  # High word
    ],
    "time_settings": [
        REGISTER_MAP["FLOAT_TIME_TODAY_SEC"],
        REGISTER_MAP["ABSORB_TIME"],
        REGISTER_MAP["EQUALIZE_TIME"],
    ],
    "diagnostics": [
        REGISTER_MAP["REASON_FOR_RESTING"],
    ],
    # Add setpoint registers for number entities
    "setpoints": [
        REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"],
        REGISTER_MAP["FLOAT_VOLTAGE_SETPOINT"],
        REGISTER_MAP["EQUALIZE_VOLTAGE_SETPOINT"],
        REGISTER_MAP["BATTERY_OUTPUT_CURRENT_LIMIT"],
    ],
    # Add EEPROM time settings for number entities
    "eeprom_settings": [
        REGISTER_MAP["ABSORB_TIME_EEPROM"],
        REGISTER_MAP["EQUALIZE_TIME_EEPROM"],
        REGISTER_MAP["EQUALIZE_INTERVAL_DAYS_EEPROM"],
    ],
}


class MidniteSolarUpdateCoordinator(DataUpdateCoordinator):
    """Gather data for the Midnite Solar device."""

    api: MidniteHub

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        interval: int = 15,
    ) -> None:
        """Initialize Update Coordinator."""

        super().__init__(
            hass, 
            _LOGGER, 
            name=DOMAIN, 
            update_interval=timedelta(seconds=interval)
        )
        self.api = MidniteHub(host, port)
        self.interval = interval
        self.device_info = {}

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch all device and sensor data from api."""
        data = {}
        unavailable_entities = {}

        # Ensure connection is active
        if not self.api.is_still_connected():
            _LOGGER.debug("Connection not active, attempting to reconnect")
            try:
                await self.hass.async_add_executor_job(self.api.connect)
            except Exception as e:
                _LOGGER.error(f"Failed to connect: {e}")
                raise UpdateFailed(f"Cannot connect to device: {e}") from e
        
        # Test connection with a simple read before proceeding
        try:
            test_result = await self.hass.async_add_executor_job(
                self.api.read_holding_registers, REGISTER_MAP["UNIT_ID"], 1
            )
            if test_result is None or test_result.isError():
                _LOGGER.error("Connection test failed - device not responding")
                raise UpdateFailed("Device not responding to connection test")
        except Exception as e:
            _LOGGER.error(f"Connection test failed: {e}")
            # Try to reconnect once more
            try:
                await self.hass.async_add_executor_job(self.api.disconnect)
                await self.hass.async_add_executor_job(self.api.connect)
                test_result = await self.hass.async_add_executor_job(
                    self.api.read_holding_registers, REGISTER_MAP["UNIT_ID"], 1
                )
                if test_result is None or test_result.isError():
                    raise UpdateFailed("Device not responding after reconnect attempt")
            except Exception as e2:
                _LOGGER.error(f"Reconnect failed: {e2}")
                raise UpdateFailed(f"Cannot communicate with device: {e2}") from e2

        # Read all register groups
        for group_name, registers in REGISTER_GROUPS.items():
            try:
                result = await self._read_register_group(registers)
                if result is not None:
                    data[group_name] = result
                else:
                    _LOGGER.warning(f"Failed to read register group: {group_name}")
                    # Mark all registers in this group as unavailable
                    for reg in registers:
                        unavailable_entities[str(reg)] = False
            except Exception as e:
                _LOGGER.error(f"Error reading register group {group_name}: {e}")
                for reg in registers:
                    unavailable_entities[str(reg)] = False

        return {
            "data": data,
            "availability": unavailable_entities,
        }

    async def _read_register_group(self, registers: List[int]) -> Optional[Dict[int, Any]]:
        """Read a group of registers."""
        if not registers:
            return None

        # Sort and deduplicate registers
        sorted_regs = sorted(set(registers))
        result_data = {}

        for reg in sorted_regs:
            try:
                result = await self.hass.async_add_executor_job(
                    self.api.read_holding_registers, reg, 1
                )
                if result is not None and not result.isError():
                    result_data[reg] = result.registers[0]
                else:
                    _LOGGER.debug(f"Failed to read register {reg}")
            except Exception as e:
                _LOGGER.debug(f"Exception reading register {reg}: {e}")

        return result_data if result_data else None

    def get_register_value(self, address: int) -> Optional[int]:
        """Get a specific register value from the last update."""
        if self.data is None or "data" not in self.data:
            return None

        for group_name, registers in REGISTER_GROUPS.items():
            if address in registers and group_name in self.data["data"]:
                return self.data["data"][group_name].get(address)

        return None

    def get_32bit_value(self, low_address: int, high_address: int) -> Optional[int]:
        """Get a 32-bit value from two registers."""
        if self.data is None or "data" not in self.data:
            return None

        for group_name, registers in REGISTER_GROUPS.items():
            if low_address in registers and high_address in registers:
                data = self.data["data"].get(group_name)
                if data is not None:
                    low_value = data.get(low_address)
                    high_value = data.get(high_address)
                    if low_value is not None and high_value is not None:
                        return (high_value << 16) | low_value

        return None
