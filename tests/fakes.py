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

    def __init__(
        self,
        read_values: Optional[dict[int, int]] = None,
        fail_writes=False,
        error_writes=False,
        stale_read: bool = False,
        unreadable: bool = False,
        bad_blocks: Optional[set[tuple[int, int]]] = None,
        unreadable_registers: Optional[set[int]] = None,
    ):
        self.read_values = read_values or {}
        self.writes: list[tuple[int, int]] = []
        self.reads: list[int] = []
        self.fail_writes = fail_writes
        self.error_writes = error_writes
        # A Classic that accepts a write stores it, so a read-back returns it.
        # stale_read models the write-protected Classic that ignores the write
        # and keeps answering with the old value; unreadable models a register
        # that does not answer at all.
        self.stale_read = stale_read
        self.unreadable = unreadable
        # (address, count) pairs that answer with an exception, so the block
        # fallback can be exercised; and addresses that never answer at all.
        self.bad_blocks = bad_blocks or set()
        self.unreadable_registers = unreadable_registers or set()
        # The coordinator hands the serial number over after every update, because
        # the write-protect grant dies with the connection.
        self._serial = None
        self.serial_sets = 0

    def write_register(self, address: int, value: int, retries: int = 2):
        self.writes.append((address, value))
        if self.fail_writes:
            raise OSError("[Errno 104] Connection reset by peer")
        if not self.stale_read and not self.unreadable:
            self.read_values[address] = value
        return ModbusResult(error=self.error_writes)

    def read_holding_registers(self, address: int, count: int = 1, retries: int = 5):
        self.reads.append(address)
        if self.unreadable or (address, count) in self.bad_blocks:
            return ModbusResult(error=True)
        if count == 1 and address in self.unreadable_registers:
            return ModbusResult(error=True)
        return ModbusResult(
            registers=[self.read_values.get(address + offset, 0) for offset in range(count)]
        )

    def set_serial_number(self, serial):
        self._serial = serial
        self.serial_sets += 1

    def connect(self):
        """No socket to open."""
        return True

    def disconnect(self):
        """No socket to close."""

    def reset(self):
        """No socket to reset."""


class FakeCoordinator(DataUpdateCoordinator):
    """Coordinator holding canned register data, keyed by group name."""

    def __init__(self, hass, api: FakeApi, groups: Optional[dict[str, dict[int, int]]] = None):
        super().__init__(hass, logging.getLogger(__name__), name="midnite_solar")
        self.api = api
        self.data = {"data": groups or {}, "groups": groups or {}}
        self.refresh_requests = 0

    async def async_request_refresh(self):
        """A refresh brings back what the device reports now, as a real one does."""
        self.refresh_requests += 1
        for group in self.data["data"].values():
            for address in group:
                if address in self.api.read_values:
                    group[address] = self.api.read_values[address]

    def get_register_value(self, address: int) -> Any:
        for group in self.data["data"].values():
            if address in group:
                return group[address]
        return None

    def group(self, name: str) -> dict[int, int]:
        return self.data["data"].setdefault(name, {})
