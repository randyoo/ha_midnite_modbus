"""The Midnite Solar custom component for Home Assistant."""

import logging
from typing import Any

from pymodbus.client import ModbusTcpClient
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    DEVICE_DEFAULT_NAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)
_PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Midnite Solar component from YAML configuration."""
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up Midnite Solar from a config entry."""
    _LOGGER.info(f"Setting up Midnite Solar at {entry.data[CONF_HOST]}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}")
    client = ModbusTcpClient(
        entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
    )

    # Connect to the device
    _LOGGER.info("Attempting to connect to Midnite Solar device...")
    connected = await hass.async_add_executor_job(client.connect)
    _LOGGER.info(f"Connection result: {connected}")
    if not connected:
        raise ConfigEntryNotReady("Could not connect to Midnite Solar device")

    # Configure client timeout settings
    client.timeout = 5
    client.retries = 3
    
    # Create a wrapper for easier access
    midnite_api = MidniteAPI(hass, client)
    
    # Read device information (serial number, model, etc.)
    await midnite_api.read_device_info(entry.data[CONF_HOST])
    
    # Store the client in runtime data
    entry.runtime_data = midnite_api

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload a config entry."""
    if hasattr(entry, 'runtime_data') and entry.runtime_data:
        api = entry.runtime_data
        _LOGGER.info("Closing Modbus connection...")
        hass.async_add_executor_job(api.client.close)
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)


class MidniteAPI:
    """Wrapper class for Midnite Solar Modbus communication."""

    def __init__(self, hass: HomeAssistant, client: ModbusTcpClient):
        """Initialize the API wrapper."""
        self.hass = hass
        self.client = client
        self.device_info = {
            "identifiers": {},
            "name": None,
            "model": None,
            "serial_number": None,
            "manufacturer": "Midnite Solar",
        }
        # Keep connection open
        if not client.connected:
            _LOGGER.info("Connecting Modbus client...")
            self.hass.async_add_executor_job(client.connect)

    async def read_holding_registers(self, address: int, count: int = 1):
        """Read holding registers from the device."""
        _LOGGER.info(f"Reading holding registers: address={address}, count={count}")
        try:
            result = await self._execute(lambda: self.client.read_holding_registers(
                address=address - 1,  # Modbus addresses are 0-indexed
                count=count,
            ))
            _LOGGER.info(f"Read result: {result}")
            if result.isError():
                _LOGGER.error(f"Modbus error reading address {address}: {result}")
                return None
            _LOGGER.info(f"Registers read successfully: {result.registers}")
            return result.registers
        except Exception as e:
            _LOGGER.error(f"Exception while reading registers at address {address}: {e}", exc_info=True)
            return None

    async def write_register(self, address: int, value: int):
        """Write a single register to the device."""
        _LOGGER.info(f"Writing register: address={address}, value={value}")
        try:
            result = await self._execute(lambda: self.client.write_register(
                address=address - 1,  # Modbus addresses are 0-indexed
                value=value,
            ))
            _LOGGER.info(f"Write result: {result}")
            return not result.isError()
        except Exception as e:
            _LOGGER.error(f"Exception while writing register at address {address}: {e}", exc_info=True)
            return False

    async def read_device_info(self, hostname):
        """Read device information including serial number and model."""
        from .const import DEVICE_TYPES, REGISTER_MAP
        
        _LOGGER.info("Reading device information...")
        
        # Read unit ID to get device type/model
        unit_id_reg = await self.read_holding_registers(REGISTER_MAP["UNIT_ID"])
        if unit_id_reg:
            device_value = unit_id_reg[0] & 0xFF  # Get LSB (unit type)
            model = DEVICE_TYPES.get(device_value, f"Unknown ({device_value})")
            self.device_info["model"] = model
            _LOGGER.info(f"Device model: {model}")
        
        # Read serial number (32-bit value from registers 4369 and 4370)
        serial_lo = await self.read_holding_registers(REGISTER_MAP["SERIAL_NUMBER_LO"])
        serial_hi = await self.read_holding_registers(REGISTER_MAP["SERIAL_NUMBER_HI"]) if serial_lo else None
        
        if serial_lo and serial_hi:
            serial_number = (serial_hi[0] << 16) | serial_lo[0]
            self.device_info["serial_number"] = str(serial_number)
            # Use serial number as identifier for device registry
            self.device_info["identifiers"] = {(DOMAIN, str(serial_number))}
            self.device_info["name"] = f"Midnite {model} ({serial_number})"
            _LOGGER.info(f"Device serial number: {serial_number}")
        else:
            # Fallback to hostname if serial not available
            self.device_info["identifiers"] = {(DOMAIN, hostname)}
            self.device_info["name"] = f"Midnite Device ({hostname})"
            _LOGGER.warning("Could not read serial number, using hostname as identifier")
    
    async def _execute(self, func):
        """Execute a function in the executor and return the result."""
        # Use hass.async_add_executor_job to run synchronous Modbus calls
        # This is needed because pymodbus client methods are synchronous
        max_retries = 3
        for attempt in range(max_retries):
            try:
                _LOGGER.info(f"Executing Modbus function: {func}")
                
                # Ensure we're connected before executing
                if not self.client.connected:
                    _LOGGER.info("Reconnecting Modbus client...")
                    await self.hass.async_add_executor_job(self.client.connect)
                    _LOGGER.info(f"Connection status after reconnect: {self.client.connected}")
                
                result = await self.hass.async_add_executor_job(func)
                _LOGGER.info(f"Function executed successfully, result: {result}")
                return result
            except Exception as e:
                _LOGGER.error(f"Exception during executor job (attempt {attempt + 1}/{max_retries}): {e}", exc_info=True)
                # Try to reconnect on failure
                try:
                    if self.client.connected:
                        _LOGGER.info("Closing connection after error...")
                        await self.hass.async_add_executor_job(self.client.close)
                    _LOGGER.info(f"Waiting {attempt + 1} seconds before retry...")
                    import asyncio
                    await asyncio.sleep(attempt + 1)
                except Exception as close_error:
                    _LOGGER.error(f"Error while closing connection: {close_error}")
        
        _LOGGER.error(f"Failed after {max_retries} attempts")
        raise
