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
        return self._client.is_socket_open()

    def connect(self):
        """Connect to the Modbus TCP server."""
        _LOGGER.debug(f"Connecting to {self.host}:{self.port}")
        return self._client.connect()

    def disconnect(self):
        """Disconnect from the Modbus TCP server."""
        if self._client.is_socket_open():
            _LOGGER.debug(f"Disconnecting from {self.host}:{self.port}")
            return self._client.close()
        return None

    def write_register(self, address: int, value: int):
        """Write a register."""
        # Midnite devices use unit_id 1 by default
        return self._client.write_register(
            address=address - 1,  # Modbus addresses are 0-indexed
            value=value,
            device_id=1,
        )

    def read_holding_registers(self, address: int, count: int = 1):
        """Read holding registers with enhanced retry logic and debug logging."""
        _LOGGER.debug(f"Reading unit 1 address {address} count {count}")
        # Midnite devices use unit_id 1 by default
        
        max_retries = 5  # Increased from 3 to 5 for better reliability
        for attempt in range(max_retries):
            try:
                result = self._client.read_holding_registers(
                    address=address - 1,  # Modbus addresses are 0-indexed
                    count=count,
                    device_id=1,
                )
                if result is not None and not result.isError():
                    _LOGGER.debug(f"Successfully read address {address}: {result.registers}")
                    return result
                _LOGGER.warning(f"Attempt {attempt + 1} failed for address {address}: {result}")
            except Exception as e:
                _LOGGER.warning(f"Attempt {attempt + 1} exception for address {address}: {e}")
                if attempt < max_retries - 1:
                    backoff_time = 0.2 * (attempt + 1)  # Increased exponential backoff
                    _LOGGER.debug(f"Waiting {backoff_time}s before retry {attempt + 2}")
                    time.sleep(backoff_time)
        
        _LOGGER.error(f"All {max_retries} attempts failed for address {address}, count={count}")
        return None
