"""The Midnite Solar custom component for Home Assistant."""

import asyncio
import logging
import random
from typing import Any, Optional

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

# Connection state constants
CONNECTION_STATE_CONNECTED = "connected"
CONNECTION_STATE_DISCONNECTED = "disconnected"
CONNECTION_STATE_RECONNECTING = "reconnecting"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Midnite Solar component from YAML configuration."""
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up Midnite Solar from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    _LOGGER.info(f"Setting up Midnite Solar at {host}:{port}")
    
    # Create a wrapper for easier access
    midnite_api = MidniteAPI(hass, host, port)
    
    # Connect to the device with retry logic
    _LOGGER.info("Attempting to connect to Midnite Solar device...")
    connected = await midnite_api.connection_manager.connect()
    if not connected:
        raise ConfigEntryNotReady("Could not connect to Midnite Solar device")
    
    # Read device information (serial number, model, etc.)
    await midnite_api.read_device_info(host)
    
    # Store the API in runtime data
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
        await api.connection_manager.close()
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)


class ConnectionManager:
    """Manages Modbus TCP connections with exponential backoff and retry logic."""

    def __init__(self, hass: HomeAssistant, host: str, port: int = 502):
        """Initialize the connection manager."""
        self.hass = hass
        self.host = host
        self.port = port
        self.client = ModbusTcpClient(host, port=port)
        self.connection_state = CONNECTION_STATE_DISCONNECTED
        self.retry_count = 0
        self.last_connection_attempt = 0
        self.lock = asyncio.Lock()
        
        # Configure client with better defaults
        self.client.timeout = 10  # Increased from 5 to 10 seconds
        self.client.retries = 3
    
    async def connect(self) -> bool:
        """Connect to the Modbus device with retry logic."""
        async with self.lock:
            if self.connection_state == CONNECTION_STATE_CONNECTED and self.client.connected:
                _LOGGER.debug("Already connected")
                return True
            
            if self.connection_state == CONNECTION_STATE_RECONNECTING:
                _LOGGER.debug("Connection attempt already in progress")
                return False
            
            self.connection_state = CONNECTION_STATE_RECONNECTING
            self.retry_count += 1
            
            try:
                # Calculate backoff with jitter
                backoff_delay = await self._calculate_backoff()
                if backoff_delay > 0:
                    _LOGGER.info(f"Waiting {backoff_delay:.1f} seconds before connection attempt {self.retry_count}")
                    await asyncio.sleep(backoff_delay)
                
                # Close any existing connection first
                if self.client.connected:
                    _LOGGER.debug("Closing existing connection before reconnect")
                    await self.hass.async_add_executor_job(self.client.close)
                
                _LOGGER.info(f"Attempting to connect to {self.host}:{self.port} (attempt {self.retry_count})")
                connected = await self.hass.async_add_executor_job(self.client.connect)
                
                if connected:
                    self.connection_state = CONNECTION_STATE_CONNECTED
                    self.retry_count = 0  # Reset retry counter on success
                    _LOGGER.info(f"Successfully connected to {self.host}:{self.port}")
                    return True
                else:
                    _LOGGER.warning(f"Connection attempt {self.retry_count} failed")
                    self.connection_state = CONNECTION_STATE_DISCONNECTED
                    return False
                    
            except Exception as e:
                _LOGGER.error(f"Connection error: {e}", exc_info=True)
                self.connection_state = CONNECTION_STATE_DISCONNECTED
                # Try to close the connection to cleanup
                try:
                    await self.hass.async_add_executor_job(self.client.close)
                except Exception as close_error:
                    _LOGGER.debug(f"Error closing connection: {close_error}")
                return False
    
    async def _calculate_backoff(self) -> float:
        """Calculate exponential backoff with jitter."""
        if self.retry_count == 0:
            return 0
        elif self.retry_count == 1:
            base_delay = 2.0
        elif self.retry_count == 2:
            base_delay = 4.0
        elif self.retry_count == 3:
            base_delay = 8.0
        else:
            # For retries beyond 3, use longer delays with cap
            base_delay = min(64.0 * (2 ** (self.retry_count - 4)), 120.0)
        
        # Add jitter (±20%)
        jitter = random.uniform(0.8, 1.2)
        return base_delay * jitter
    
    async def ensure_connected(self) -> bool:
        """Ensure we have an active connection."""
        if self.connection_state == CONNECTION_STATE_CONNECTED and self.client.connected:
            return True
        
        # Check if client thinks it's connected but socket might be bad
        if self.client.connected:
            _LOGGER.debug("Client reports connected, verifying connection...")
            try:
                # Quick ping by reading a register that should always work
                result = await self.hass.async_add_executor_job(
                    lambda: self.client.read_holding_registers(0, 1)
                )
                if not result.isError():
                    _LOGGER.debug("Connection verified as healthy")
                    return True
            except Exception as e:
                _LOGGER.debug(f"Connection verification failed: {e}")
        
        # Need to reconnect
        return await self.connect()
    
    async def close(self):
        """Close the connection."""
        async with self.lock:
            if self.client.connected:
                _LOGGER.info("Closing Modbus connection")
                try:
                    await self.hass.async_add_executor_job(self.client.close)
                except Exception as e:
                    _LOGGER.error(f"Error closing connection: {e}")
            self.connection_state = CONNECTION_STATE_DISCONNECTED


class MidniteAPI:
    """Wrapper class for Midnite Solar Modbus communication."""

    def __init__(self, hass: HomeAssistant, host: str, port: int = 502):
        """Initialize the API wrapper."""
        self.hass = hass
        self.host = host
        self.port = port
        self.connection_manager = ConnectionManager(hass, host, port)
        self.device_info = {
            "identifiers": {},
            "name": None,
            "model": None,
            "serial_number": None,
            "manufacturer": "Midnite Solar",
        }
        # Note: Connection is established lazily during first operation
        # This prevents initialization deadlocks during Home Assistant startup

    async def read_holding_registers(self, address: int, count: int = 1):
        """Read holding registers from the device."""
        _LOGGER.debug(f"Reading holding registers: address={address}, count={count}")
        try:
            # Ensure connection is active
            if not await self.connection_manager.ensure_connected():
                _LOGGER.warning(f"Failed to establish connection for reading address {address}")
                return None
            
            result = await self._execute(lambda: self.connection_manager.client.read_holding_registers(
                address=address - 1,  # Modbus addresses are 0-indexed
                count=count,
            ))
            if result is None:
                _LOGGER.debug(f"Read operation failed for address {address}")
                return None
            
            _LOGGER.debug(f"Read result: {result}")
            if result.isError():
                _LOGGER.warning(f"Modbus error reading address {address}: {result}")
                return None
            _LOGGER.debug(f"Registers read successfully: {result.registers}")
            return result.registers
        except Exception as e:
            _LOGGER.debug(f"Exception while reading registers at address {address}: {e}")
            # The connection manager will handle reconnection on next attempt
            return None

    async def write_register(self, address: int, value: int):
        """Write a single register to the device."""
        _LOGGER.debug(f"Writing register: address={address}, value={value}")
        try:
            # Ensure connection is active
            if not await self.connection_manager.ensure_connected():
                _LOGGER.warning(f"Failed to establish connection for writing to address {address}")
                return False
            
            result = await self._execute(lambda: self.connection_manager.client.write_register(
                address=address - 1,  # Modbus addresses are 0-indexed
                value=value,
            ))
            if result is None:
                _LOGGER.debug(f"Write operation failed for address {address}")
                return False
            
            _LOGGER.debug(f"Write result: {result}")
            return not result.isError()
        except Exception as e:
            _LOGGER.debug(f"Exception while writing register at address {address}: {e}")
            return False

    async def read_device_info(self, hostname):
        """Read device information including serial number and model."""
        from .const import DEVICE_TYPES, REGISTER_MAP
        
        _LOGGER.debug("Reading device information...")
        
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
                _LOGGER.debug(f"Executing Modbus function: {func}")
                
                # Ensure we're connected before executing
                if not await self.connection_manager.ensure_connected():
                    _LOGGER.warning(f"Failed to establish connection for execution (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                    continue
                
                result = await self.hass.async_add_executor_job(func)
                _LOGGER.debug(f"Function executed successfully, result: {result}")
                return result
            except (OSError, BrokenPipeError) as e:
                # Connection/socket errors - need to reconnect
                if attempt == max_retries - 1:
                    _LOGGER.error(f"Connection error after {max_retries} attempts: {e}")
                else:
                    _LOGGER.debug(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # The connection manager will handle the backoff on next ensure_connected call
                    await asyncio.sleep(2)
            except Exception as e:
                # Other errors - don't close connection, just retry
                if attempt == max_retries - 1:
                    _LOGGER.error(f"Error after {max_retries} attempts: {e}")
                else:
                    _LOGGER.debug(f"Error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        
        # Don't raise here, just return None to indicate failure
        _LOGGER.debug(f"Operation failed after {max_retries} attempts, returning None")
        return None
