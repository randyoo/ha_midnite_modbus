"""Support for Midnite Solar devices."""

import logging
import threading
import time
from typing import Optional

from pymodbus.client import ModbusTcpClient

_LOGGER = logging.getLogger(__name__)


class MidniteHub:
    """Midnite Hub for managing Modbus TCP connections."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the hub."""
        self.host = host
        self.port = port
        self._client = ModbusTcpClient(host=self.host, port=self.port)
        self._lock = threading.Lock()

    def is_still_connected(self):
        """Check if the connection is still open."""
        with self._lock:
            return self._client.is_socket_open()

    def connect(self):
        """Connect to the Modbus TCP server."""
        with self._lock:
            _LOGGER.debug(f"Connecting to {self.host}:{self.port}")
            return self._client.connect()

    def disconnect(self):
        """Disconnect from the Modbus TCP server."""
        with self._lock:
            if self._client.is_socket_open():
                _LOGGER.debug(f"Disconnecting from {self.host}:{self.port}")
                return self._client.close()
            return None

    def write_register(self, address: int, value: int):
        """Write a register."""
        # Midnite devices use unit_id 1 by default
        with self._lock:
            try:
                result = self._client.write_register(
                    address=address - 1,  # Modbus addresses are 0-indexed
                    value=value,
                    # device_id=1,  # Removed - may cause issues with certain registers
                )
                return result
            except Exception:
                raise

    def read_holding_registers(self, address: int, count: int = 1):
        """Read holding registers with enhanced retry logic and debug logging."""
        _LOGGER.debug(f"Reading unit 1 address {address} count {count}")
        # Midnite devices use unit_id 1 by default
        
        max_retries = 5  # Increased from 3 to 5 for better reliability
        with self._lock:
            for attempt in range(max_retries):
                try:
                    # Ensure connection is active before reading
                    if not self._client.is_socket_open():
                        _LOGGER.debug(f"Connection closed, reconnecting before read attempt {attempt + 1}")
                        self.connect()
                        # Add a small delay after connect to allow device to stabilize
                        time.sleep(0.2)
                    
                    result = self._client.read_holding_registers(
                        address=address - 1,  # Modbus addresses are 0-indexed
                        count=count,
                        # device_id=1,  # Removed - may cause issues with certain registers like 20492/20493
                    )
                    if result is not None and not result.isError():
                        _LOGGER.debug(f"Successfully read address {address}: {result.registers}")
                        return result
                    _LOGGER.warning(f"Attempt {attempt + 1} failed for address {address}: {result}")
                except Exception as e:
                    # Special handling for "Unable to decode request" errors
                    error_msg = str(e)
                    if "Unable to decode request" in error_msg or "byte_count" in error_msg:
                        _LOGGER.warning(f"Attempt {attempt + 1} exception for address {address}: {e}")
                        _LOGGER.debug(f"This may indicate a Modbus protocol issue with this register range")
                        # Try to reset connection on protocol errors
                        if attempt < max_retries - 1:
                            _LOGGER.debug("Closing and reopening connection due to protocol error")
                            self.disconnect()
                    else:
                        _LOGGER.warning(f"Attempt {attempt + 1} exception for address {address}: {e}")
                    
                    if attempt < max_retries - 1:
                        backoff_time = 0.2 * (attempt + 1)  # Increased exponential backoff
                        _LOGGER.debug(f"Waiting {backoff_time}s before retry {attempt + 2}")
                        time.sleep(backoff_time)
            
            _LOGGER.error(f"All {max_retries} attempts failed for address {address}, count={count}")
            return None
