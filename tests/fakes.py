"""Fakes that record what the integration would send to a Classic."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


class ModbusResult:
    """Stands in for a pymodbus response."""

    def __init__(self, registers: Optional[list[int]] = None, error: bool = False):
        self.registers = registers or []
        self._error = error

    def isError(self) -> bool:  # noqa: N802 - pymodbus spelling
        return self._error


class FakeApi:
    """Records Modbus writes instead of sending them.

    The Classic is effectively single-connection and must not be talked to from
    the test suite, so this is the only "device" the tests use.
    """

    def __init__(self, read_values: Optional[dict[int, int]] = None, fail_writes=False, error_writes=False):
        self.read_values = read_values or {}
        self.writes: list[tuple[int, int]] = []
        self.fail_writes = fail_writes
        self.error_writes = error_writes

    def write_register(self, address: int, value: int, retries: int = 2):
        self.writes.append((address, value))
        if self.fail_writes:
            raise OSError("[Errno 104] Connection reset by peer")
        return ModbusResult(error=self.error_writes)

    def read_holding_registers(self, address: int, count: int = 1, retries: int = 5):
        return ModbusResult(registers=[self.read_values.get(address, 0) for _ in range(count)])

    def disconnect(self):
        """No socket to close."""

    def reset(self):
        """No socket to reset."""

    def is_still_connected(self):
        return True


class FakeCoordinator(DataUpdateCoordinator):
    """Coordinator holding canned register data, keyed by group name."""

    def __init__(self, hass, api: FakeApi, groups: Optional[dict[str, dict[int, int]]] = None):
        super().__init__(hass, logging.getLogger(__name__), name="midnite_solar")
        self.api = api
        self.data = {"data": groups or {}, "groups": groups or {}}
        self.refresh_requests = 0

    async def async_request_refresh(self):
        self.refresh_requests += 1

    def get_register_value(self, address: int) -> Any:
        for group in self.data["data"].values():
            if address in group:
                return group[address]
        return None

    def group(self, name: str) -> dict[int, int]:
        return self.data["data"].setdefault(name, {})
