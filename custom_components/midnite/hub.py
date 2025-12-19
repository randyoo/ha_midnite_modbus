"""Support for Midnite Solar devices."""

import logging
import threading
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
        """Read holding registers."""
        _LOGGER.debug(f"Reading unit 1 address {address} count {count}")
        # Midnite devices use unit_id 1 by default
        return self._client.read_holding_registers(
            address=address - 1,  # Modbus addresses are 0-indexed
            count=count,
            device_id=1,
        )
