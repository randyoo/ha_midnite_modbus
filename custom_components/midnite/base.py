"""Module defines entity descriptions for Midnite Solar components."""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.typing import StateType

_LOGGER = logging.getLogger(__name__)


@dataclass
class MidniteBaseEntityDescription(EntityDescription):
    """An extension of EntityDescription for Midnite Solar components."""

    @staticmethod
    def lambda_func():
        """Return an entitydescription."""
        return lambda coordinator, address: coordinator.get_register_value(address)

    value_fn: Callable[[dict], StateType] = lambda_func()

    @staticmethod
    @staticmethod
    def get_device_info(coordinator, entry, domain):
        """Extract device info from coordinator data."""
        # Debug logging to track when device_info is called
        _LOGGER.debug(f"get_device_info called for entry: {entry.entry_id}")
        
        # Try to get device ID from coordinator data (registers 4111-4112)
        if coordinator.data and "data" in coordinator.data:
            _LOGGER.debug(f"Coordinator has data: {coordinator.data.get('data', {}).keys()}")
            device_info_data = coordinator.data["data"].get("device_info")
            if device_info_data:
                _LOGGER.debug(f"Device info data available with keys: {list(device_info_data.keys())}")
                
                from .const import REGISTER_MAP, DEVICE_TYPES
                
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
                    _LOGGER.debug(f"Software date registers - RO: {sw_date_ro}, Month/Day: {sw_date_month_day}")
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
                     
                    _LOGGER.debug(f"Returning device_info with hw_version={'PCB ' + str(pcb_revision) if pcb_revision is not None else None}, sw_version={sw_build_date}")
                    return {
                        "identifiers": {(domain, str(device_id))},
                        "name": f"{model} ({device_id})",
                        "manufacturer": "Midnite Solar",
                        "model": model,
                        "hw_version": f"PCB {pcb_revision}" if pcb_revision is not None else None,
                        "sw_version": sw_build_date,
                    }
        
        # Fallback to entry_id if device ID not available
        return {
            "identifiers": {(domain, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
        }
