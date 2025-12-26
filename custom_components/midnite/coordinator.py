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
        # Use DEVICE_ID (registers 4111-4112) as the serial number identifier
        # This is more reliable than SERIAL_NUMBER registers (20492/20493)
        REGISTER_MAP["DEVICE_ID_LSW"],
        REGISTER_MAP["DEVICE_ID_MSW"],
        # Unit name (8 characters from 4 registers, each holding 2 bytes)
        REGISTER_MAP["UNIT_NAME_0"],
        REGISTER_MAP["UNIT_NAME_1"],
        REGISTER_MAP["UNIT_NAME_2"],
        REGISTER_MAP["UNIT_NAME_3"],
        # MAC address (registers 4106-4108)
        REGISTER_MAP["MAC_ADDRESS_PART_1"],
        REGISTER_MAP["MAC_ADDRESS_PART_2"],
        REGISTER_MAP["MAC_ADDRESS_PART_3"],
        # Software date information
        REGISTER_MAP["UNIT_SW_DATE_RO"],
        REGISTER_MAP["UNIT_SW_DATE_MONTH_DAY"],
    ],
    "status": [
        REGISTER_MAP["DISP_AVG_VBATT"],
        REGISTER_MAP["DISP_AVG_VPV"],
        REGISTER_MAP["IBATT_DISPLAY_S"],
        REGISTER_MAP["WATTS"],
        REGISTER_MAP["COMBO_CHARGE_STAGE"],
        REGISTER_MAP["PV_INPUT_CURRENT"],
        REGISTER_MAP["VOC_LAST_MEASURED"],
        REGISTER_MAP["KW_HOURS"],
        REGISTER_MAP["STATUSROLL"],
        REGISTER_MAP["INFO_FLAGS_BITS3"],
        # Additional status registers
        REGISTER_MAP["RESERVED_4105"],
        REGISTER_MAP["NITE_MINUTES_NO_PWR"],
        REGISTER_MAP["REASON_FOR_RESET"],
        REGISTER_MAP["MPP_W_LAST"],
        REGISTER_MAP["NO_DOUBLE_CLICK_TIMER"],
        REGISTER_MAP["SLIDING_CURRENT_LIMIT"],
        REGISTER_MAP["MIN_ABSORB_TIME"],
        REGISTER_MAP["GENERAL_PURPOSE_WORD"],
        REGISTER_MAP["EQUALIZE_RETRY_DAYS"],
        REGISTER_MAP["FORCE_FLAG_BITS"],
        # Raw/unfiltered registers
        REGISTER_MAP["IBATT_RAW_A"],
        REGISTER_MAP["OUTPUT_VBATT_RAW"],
        REGISTER_MAP["INPUT_VPV_RAW"],
        # Additional status registers
        REGISTER_MAP["PREVOC"],
        REGISTER_MAP["PK_HOLD_VPV_STAMP"],
        REGISTER_MAP["IPV_MINUS_RAW"],
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
        REGISTER_MAP["RESTART_TIME_MS"],
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
    # AUX control registers
    "aux_control": [
        REGISTER_MAP["AUX1_VOLTS_HI_REL"],
        REGISTER_MAP["AUX1_VOLTS_LO_REL"],
        REGISTER_MAP["AUX2_A2D_D2A"],
        REGISTER_MAP["AUX2_VOLTS_HI_REL"],
        REGISTER_MAP["AUX2_VOLTS_LO_REL"],
    ],
    # Advanced status registers
    "advanced_status": [
        REGISTER_MAP["HIGHEST_VINPUT_LOG"],
        REGISTER_MAP["JrAmpHourNET"],
        REGISTER_MAP["MATCH_POINT_SHADOW"],
        REGISTER_MAP["MINUTE_LOG_INTERVAL_SEC"],
        REGISTER_MAP["MODBUS_PORT_REGISTER"],
        REGISTER_MAP["MPP_W_LAST"],
        # Additional advanced status registers
        REGISTER_MAP["ABSORB_TIME_DUPLICATE"],
        REGISTER_MAP["ARC_FAULT_SENSITIVITY"],
        REGISTER_MAP["BATTERY_TEMP_PASSED_EEPROM"],
        REGISTER_MAP["CLEAR_LOGS_CAT"],
        REGISTER_MAP["CLEAR_LOGS_COUNTER_10MS"],
        REGISTER_MAP["CLIPPER_CMD_VOLTS"],
        REGISTER_MAP["CTI_ME0"],
        REGISTER_MAP["CTI_ME0_HIGH"],
        REGISTER_MAP["CTI_ME1"],
        REGISTER_MAP["CTI_ME1_HIGH"],
        REGISTER_MAP["CTI_ME2"],
        REGISTER_MAP["DAY_LOG_COMB_CAT_INDEX"],
        REGISTER_MAP["MIN_LOG_COMB_CAT_INDEX"],
    ],
    # Advanced configuration registers
    "advanced_config": [
        REGISTER_MAP["MPPT_MODE"],
        REGISTER_MAP["AUX_1_AND_2_FUNCTION"],
        REGISTER_MAP["VARIMAX"],
        REGISTER_MAP["ENABLE_FLAGS3"],
        REGISTER_MAP["ENABLE_FLAGS2"],
        REGISTER_MAP["ENABLE_FLAGS_BITS"],
        # Additional config registers
        REGISTER_MAP["LED_MODE_EEPROM"],
        REGISTER_MAP["USB_COMM_MODE"],
    ],
    # AUX control registers
    "aux_control": [
        REGISTER_MAP["AUX1_VOLTS_LO_ABS"],
        REGISTER_MAP["AUX1_VOLTS_HI_ABS"],
        REGISTER_MAP["AUX1_DELAY_T_MS"],
        REGISTER_MAP["AUX1_HOLD_T_MS"],
        REGISTER_MAP["AUX2_PWM_VWIDTH"],
        REGISTER_MAP["AUX1_VOLTS_LO_REL"],
        REGISTER_MAP["AUX1_VOLTS_HI_REL"],
        REGISTER_MAP["AUX2_VOLTS_LO_REL"],
        REGISTER_MAP["AUX2_VOLTS_HI_REL"],
        REGISTER_MAP["AUX1_VOLTS_LO_PV_ABS"],
        REGISTER_MAP["AUX1_VOLTS_HI_PV_ABS"],
        REGISTER_MAP["AUX2_VOLTS_HI_PV_ABS"],
    ],
    # Voltage offset registers
    "voltage_offsets": [
        REGISTER_MAP["VBATT_OFFSET"],
        REGISTER_MAP["VPV_OFFSET"],
        REGISTER_MAP["VPV_TARGET_RD"],
        REGISTER_MAP["VPV_TARGET_WR"],
    ],
    # Temperature compensation registers
    "temp_comp": [
        REGISTER_MAP["MAX_BATTERY_TEMP_COMP_VOLTAGE"],
        REGISTER_MAP["MIN_BATTERY_TEMP_COMP_VOLTAGE"],
        REGISTER_MAP["BATTERY_TEMP_COMP_VALUE"],
    ],
    # Network configuration registers
    "network_config": [
        REGISTER_MAP["IP_SETTINGS_FLAGS"],
        REGISTER_MAP["IP_ADDRESS_LSB_1"],
        REGISTER_MAP["IP_ADDRESS_LSB_2"],
        REGISTER_MAP["GATEWAY_ADDRESS_LSB_1"],
        REGISTER_MAP["GATEWAY_ADDRESS_LSB_2"],
        REGISTER_MAP["SUBNET_MASK_LSB_1"],
        REGISTER_MAP["SUBNET_MASK_LSB_2"],
        REGISTER_MAP["DNS_1_LSB_1"],
        REGISTER_MAP["DNS_1_LSB_2"],
        REGISTER_MAP["DNS_2_LSB_1"],
        REGISTER_MAP["DNS_2_LSB_2"],
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
        import asyncio
        
        data = {}
        unavailable_entities = {}

        # Ensure connection is active
        if not self.api.is_still_connected():
            _LOGGER.debug("Connection not active, attempting to reconnect")
            try:
                await self.hass.async_add_executor_job(self.api.connect)
                # Add delay after connect to allow device to respond
                await asyncio.sleep(0.5)
            except Exception as e:
                _LOGGER.error(f"Failed to connect: {e}")
                raise UpdateFailed(f"Cannot connect to device: {e}") from e
        
        # Test connection with a simple read before proceeding
        # Try multiple registers to handle temporary communication issues
        try:
            _LOGGER.debug(f"Testing connection by reading UNIT_ID register ({REGISTER_MAP['UNIT_ID']})")
            test_result = await self.hass.async_add_executor_job(
                self.api.read_holding_registers, REGISTER_MAP["UNIT_ID"], 1
            )
            if test_result is None or test_result.isError():
                _LOGGER.warning(f"Connection test failed on UNIT_ID. Trying alternative register...")
                # Try a different register that might be more stable
                test_result = await self.hass.async_add_executor_job(
                    self.api.read_holding_registers, REGISTER_MAP["DISP_AVG_VBATT"], 1
                )
                if test_result is None or test_result.isError():
                    _LOGGER.error(f"Connection tests failed. Device not responding.")
                    raise UpdateFailed("Device not responding to connection tests")
            
            unit_id = test_result.registers[0] if test_result.registers else None
            _LOGGER.debug(f"Connection test successful. UNIT_ID: {unit_id}")
        except Exception as e:
            _LOGGER.error(f"Connection test failed with exception: {e}", exc_info=True)
            # Try to reconnect once more with detailed logging
            try:
                _LOGGER.debug("Attempting reconnect...")
                await self.hass.async_add_executor_job(self.api.disconnect)
                await asyncio.sleep(0.3)  # Brief pause before reconnect
                await self.hass.async_add_executor_job(self.api.connect)
                await asyncio.sleep(0.5)  # Allow device to respond after reconnect
                
                _LOGGER.debug("Testing connection again after reconnect...")
                test_result = await self.hass.async_add_executor_job(
                    self.api.read_holding_registers, REGISTER_MAP["UNIT_ID"], 1
                )
                if test_result is None or test_result.isError():
                    _LOGGER.error(f"Connection test still failing after reconnect. Result: {test_result}")
                    raise UpdateFailed("Device not responding after reconnect attempt")
                else:
                    unit_id = test_result.registers[0] if test_result.registers else None
                    _LOGGER.debug(f"Reconnect successful. UNIT_ID: {unit_id}")
            except Exception as e2:
                _LOGGER.error(f"Reconnect failed: {e2}", exc_info=True)
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
        """Read a group of registers with enhanced debug logging."""
        if not registers:
            return None

        # Sort and deduplicate registers
        sorted_regs = sorted(set(registers))
        result_data = {}
        failed_registers = []

        for reg in sorted_regs:
            try:
                _LOGGER.debug(f"Reading register {reg} (group: {REGISTER_MAP.get(reg, 'unknown')})")
                result = await self.hass.async_add_executor_job(
                    self.api.read_holding_registers, reg, 1
                )
                if result is not None and not result.isError():
                    value = result.registers[0]
                    result_data[reg] = value
                    _LOGGER.debug(f"Successfully read register {reg}: {value}")
                else:
                    _LOGGER.warning(f"Failed to read register {reg} (group: {REGISTER_MAP.get(reg, 'unknown')})")
                    failed_registers.append(reg)
            except Exception as e:
                error_msg = str(e)
                reg_name = REGISTER_MAP.get(reg, 'unknown')
                
                _LOGGER.warning(f"Exception reading register {reg}: {e}", exc_info=True)
                failed_registers.append(reg)

        if failed_registers:
            _LOGGER.debug(f"Failed to read registers: {failed_registers}")

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
