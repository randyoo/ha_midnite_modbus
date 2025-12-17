"""The Midnite Solar custom component for Home Assistant."""

import asyncio
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

    # Configure client timeout settings BEFORE connecting
    client.timeout = 5
    client.retries = 3

    # Connect to the device
    _LOGGER.info("Attempting to connect to Midnite Solar device...")
    connected = await hass.async_add_executor_job(client.connect)
    _LOGGER.info(f"Connection result: {connected}")
    if not connected:
        raise ConfigEntryNotReady("Could not connect to Midnite Solar device")
    
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
            # Ensure connection is active
            if not self.client.connected:
                _LOGGER.info("Reconnecting Modbus client before read...")
                await self.hass.async_add_executor_job(self.client.connect)
                _LOGGER.info(f"Connection status: {self.client.connected}")
            
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
            # Try to reconnect on connection errors
            try:
                if self.client.connected:
                    await self.hass.async_add_executor_job(self.client.close)
                await self.hass.async_add_executor_job(self.client.connect)
                _LOGGER.info(f"Reconnection attempt after error: {self.client.connected}")
            except Exception as reconnect_error:
                _LOGGER.error(f"Reconnection failed: {reconnect_error}")
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
        
        # Read unit ID to get device type/model (register 4101)
        # This is a critical register that should always be readable
        max_retries = 3
        for attempt in range(max_retries):
            unit_id_reg = await self.read_holding_registers(REGISTER_MAP["UNIT_ID"])
            if unit_id_reg:
                device_value = unit_id_reg[0] & 0xFF  # Get LSB (unit type)
                model = DEVICE_TYPES.get(device_value, f"Unknown ({device_value})")
                self.device_info["model"] = model
                _LOGGER.info(f"Device model: {model}")
                break
            if attempt < max_retries - 1:
                _LOGGER.warning(f"Attempt {attempt + 1} failed to read UNIT_ID, retrying...")
                import asyncio
                await asyncio.sleep(2)
        
        # Read software date (registers 4102-4103)
        try:
            sw_date_year = await self.read_holding_registers(REGISTER_MAP["UNIT_SW_DATE_RO"])
            if sw_date_year:
                sw_date_month_day = await self.read_holding_registers(REGISTER_MAP.get("UNIT_SW_DATE_MONTH_DAY", 4103))
                if sw_date_month_day:
                    year = sw_date_year[0]
                    month = (sw_date_month_day[0] >> 8) & 0xFF
                    day = sw_date_month_day[0] & 0xFF
                    self.device_info["sw_version"] = f"{year}-{month:02d}-{day:02d}"
                    _LOGGER.info(f"Software date: {self.device_info['sw_version']}")
        except Exception as e:
            _LOGGER.warning(f"Error reading software date: {e}")
        
        # Read serial number (16-bit value from registers 20492 and 20493)
        # According to registers2.json: SERIAL_NUMBER_MSB = 20492, SERIAL_NUMBER_LSB = 20493
        try:
            for attempt in range(max_retries):
                serial_msb = await self.read_holding_registers(REGISTER_MAP["SERIAL_NUMBER_MSB"])
                if serial_msb:
                    serial_lsb = await self.read_holding_registers(REGISTER_MAP["SERIAL_NUMBER_LSB"])
                    if serial_lsb:
                        # Formula from registers2.json: (high << 16) + low
                        serial_number = (serial_msb[0] << 16) | serial_lsb[0]
                        self.device_info["serial_number"] = str(serial_number)
                        _LOGGER.info(f"Device serial number (MSB/LSB): {serial_number} (0x{serial_msb[0]:04X}/0x{serial_lsb[0]:04X})")
                        break
                    if attempt < max_retries - 1:
                        _LOGGER.warning(f"Attempt {attempt + 1} failed to read serial number, retrying...")
                        import asyncio
                        await asyncio.sleep(2)
        except Exception as e:
            _LOGGER.warning(f"Could not read serial number from registers 20492/20493: {e}")
        
        # Try alternative: Device ID (registers 4111-4112, described as clone of register 4369)
        try:
            if not self.device_info.get("serial_number"):
                for attempt in range(max_retries):
                    device_id_lsw = await self.read_holding_registers(REGISTER_MAP["DEVICE_ID_LSW"])
                    if device_id_lsw:
                        device_id_msw = await self.read_holding_registers(REGISTER_MAP["DEVICE_ID_MSW"])  # Note: MSW is at 4112, not 4113
                        if device_id_msw:
                            alt_serial = (device_id_msw[0] << 16) | device_id_lsw[0]
                            self.device_info["serial_number"] = str(alt_serial)
                            _LOGGER.info(f"Alternative serial from DEVICE_ID: {alt_serial} (0x{device_id_msw[0]:04X}/0x{device_id_lsw[0]:04X})")
                            break
                        if attempt < max_retries - 1:
                            _LOGGER.warning(f"Attempt {attempt + 1} failed to read DEVICE_ID, retrying...")
                            import asyncio
                            await asyncio.sleep(2)
        except Exception as e:
            _LOGGER.warning(f"Error reading alternative serial from DEVICE_ID: {e}")
        
        # Read unit name (ASCII, 8 characters from registers 4210-4213)
        try:
            unit_name_parts = []
            for i in range(4):
                reg_name = f"UNIT_NAME_{i}"
                if REGISTER_MAP.get(reg_name):
                    name_part = await self.read_holding_registers(REGISTER_MAP[reg_name])
                    if name_part:
                        # Convert to ASCII characters (LSB first as per spec)
                        word = name_part[0]
                        char1 = chr(word & 0xFF) if (word & 0xFF) < 128 else '?'
                        char2 = chr((word >> 8) & 0xFF) if ((word >> 8) & 0xFF) < 128 else '?'
                        unit_name_parts.extend([char1, char2])
            
            if unit_name_parts:
                unit_name = ''.join(unit_name_parts).rstrip('\x00').rstrip().rstrip('?')
                if unit_name:
                    _LOGGER.info(f"Unit name: '{unit_name}'")
        except Exception as e:
            _LOGGER.warning(f"Error reading unit name: {e}")
        
        # Set device identifiers and name
        # Use Device ID (from registers 20492/20493) as the primary identifier
        if self.device_info.get("serial_number"):
            # Use serial number as identifier for device registry
            self.device_info["identifiers"] = {(DOMAIN, str(self.device_info["serial_number"]))}
            self.device_info["name"] = f"Midnite {self.device_info.get('model', 'Device')} ({self.device_info['serial_number']})"
        else:
            # Fallback to hostname if serial not available
            self.device_info["identifiers"] = {(DOMAIN, hostname)}
            self.device_info["name"] = f"Midnite {self.device_info.get('model', 'Device')} @ {hostname}"
            _LOGGER.warning("Could not read Device ID/Serial number from registers 20492/20493, using hostname as identifier")
    
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
            except (OSError, BrokenPipeError) as e:
                # Connection/socket errors - need to reconnect
                _LOGGER.error(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
                try:
                    await self.hass.async_add_executor_job(self.client.close)
                except Exception as close_error:
                    _LOGGER.debug(f"Error closing connection: {close_error}")
                
                if attempt < max_retries - 1:
                    _LOGGER.info(f"Waiting {(attempt + 1) * 2} seconds before retry...")
                    await asyncio.sleep((attempt + 1) * 2)
            except Exception as e:
                # Other errors - don't close connection, just retry
                _LOGGER.error(f"Error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        
        _LOGGER.error(f"Failed after {max_retries} attempts")
        raise
