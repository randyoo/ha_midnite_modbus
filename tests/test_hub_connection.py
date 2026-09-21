"""Tests for hub.py: how it treats a connection that is failing.

The Classic has one Modbus connection and drops idle ones, so the hub's job is to
notice a dead socket, release it cleanly, wait, and open exactly one new one - never
two, and never a retry storm on a device that is simply not answering. These tests
use a recorder in place of pymodbus; no socket is opened.
"""

from __future__ import annotations

import pytest

from midnite_solar import hub as hub_module
from midnite_solar.hub import MidniteHub


class Recorder:
    """Records everything the hub asks of the Modbus client."""

    log = []

    def __init__(self, host=None, port=None, timeout=None, retries=None, **kwargs):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.open = False
        self.reads = 0
        Recorder.log.append(("created", id(self)))
        Recorder.instances.append(self)

    instances = []

    def is_socket_open(self):
        return self.open

    def connect(self):
        self.open = True
        Recorder.log.append(("connect", id(self)))
        return True

    def close(self):
        self.open = False
        Recorder.log.append(("close", id(self)))

    def read_holding_registers(self, address=0, count=1, **kwargs):
        self.reads += 1
        Recorder.log.append(("read", id(self)))
        return Recorder.read_result

    def write_register(self, address=0, value=0, **kwargs):
        Recorder.writes.append((address, value))
        return Recorder.write_result

    writes = []
    read_result = None
    write_result = None


class Result:
    def __init__(self, registers=None, error=False, raises=None):
        self.registers = registers or []
        self._error = error
        self.raises = raises

    def isError(self):
        return self._error


def make_hub(monkeypatch, client=Recorder):
    Recorder.log = []
    Recorder.instances = []
    Recorder.writes = []
    Recorder.read_result = Result(registers=[0])
    Recorder.write_result = Result()
    monkeypatch.setattr(hub_module, "ModbusTcpClient", client)
    monkeypatch.setattr(MidniteHub, "RECONNECT_DELAY", 0)
    monkeypatch.setattr(hub_module.time, "sleep", lambda seconds: None)
    # MidniteHub.__init__ already builds a client through the patched class; that
    # is the one under test, so it is not thrown away here.
    return MidniteHub("192.168.88.53", 502)


class TestClientIsBuiltForASingleConnectionDevice:
    def test_the_socket_timeout_is_bounded(self, monkeypatch):
        make_hub(monkeypatch)
        assert Recorder.instances[-1].timeout == MidniteHub.DEFAULT_TIMEOUT
        assert MidniteHub.DEFAULT_TIMEOUT <= 5

    def test_the_library_is_told_not_to_retry(self, monkeypatch):
        """The hub runs its own retry loop; nested retries take minutes on a dead device."""
        make_hub(monkeypatch)
        assert Recorder.instances[-1].retries == 0

    def test_the_host_and_port_reach_the_client(self, monkeypatch):
        make_hub(monkeypatch)
        client = Recorder.instances[-1]
        assert (client.host, client.port) == ("192.168.88.53", 502)


class TestConnectionErrorsAreToldApart:
    """A dead socket needs a new socket; a bad register does not."""

    # Pinned here as a literal, not read back from the production set: the point is
    # to fail if an errno is dropped from MidniteHub._CONN_ERRNOS. Parametrizing the
    # test over that same set is circular - deleting an entry would only delete the
    # test case and stay green.
    CONN_ERRNOS = [32, 103, 104, 105, 110, 111, 112, 113]

    def test_the_listed_connection_errnos_are_exactly_these(self, monkeypatch):
        make_hub(monkeypatch)
        assert sorted(MidniteHub._CONN_ERRNOS) == self.CONN_ERRNOS

    @pytest.mark.parametrize("errno", CONN_ERRNOS)
    def test_every_listed_errno_is_a_connection_error(self, monkeypatch, errno):
        hub = make_hub(monkeypatch)
        assert hub._is_connection_error(OSError(errno, "boom")) is True

    def test_an_unrelated_os_error_is_not(self, monkeypatch):
        hub = make_hub(monkeypatch)
        assert hub._is_connection_error(OSError(22, "Invalid argument")) is False

    def test_the_message_is_checked_too(self, monkeypatch):
        hub = make_hub(monkeypatch)
        assert hub._is_connection_error(RuntimeError("[Errno 104] Connection reset by peer")) is True

    def test_a_wrapped_cause_counts(self, monkeypatch):
        hub = make_hub(monkeypatch)
        cause = OSError(104, "reset")
        wrapper = RuntimeError("pymodbus gave up")
        wrapper.__cause__ = cause
        assert hub._is_connection_error(wrapper) is True

    def test_a_pymodbus_connection_exception_type_counts(self, monkeypatch):
        hub = make_hub(monkeypatch)

        class ConnectionException(Exception):
            pass

        assert hub._is_connection_error(ConnectionException("no reply")) is True

    def test_a_modbus_error_response_is_not_a_connection_error(self, monkeypatch):
        """An exception code from the device means the socket is fine."""
        hub = make_hub(monkeypatch)
        assert hub._is_connection_error(Exception("Modbus error: illegal data address")) is False


class TestReading:
    def test_a_good_read_is_returned(self, monkeypatch):
        hub = make_hub(monkeypatch)
        Recorder.read_result = Result(registers=[1, 2, 3])
        result = hub.read_holding_registers(4113, 12)
        assert result.registers == [1, 2, 3]

    def test_the_addresses_are_zero_indexed_on_the_wire(self, monkeypatch):
        hub = make_hub(monkeypatch)
        seen = {}

        class Client(Recorder):
            def read_holding_registers(self, address=0, count=1, **kwargs):
                seen["address"] = address
                return Result(registers=[0] * count)

        monkeypatch.setattr(hub_module, "ModbusTcpClient", Client)
        hub._client = Client()
        hub.read_holding_registers(4113, 1)
        assert seen["address"] == 4112

    def test_a_device_that_says_nothing_returns_nothing(self, monkeypatch):
        """No exception, just an error response: the read gives up and reports None."""
        monkeypatch.setattr(hub_module, "ModbusTcpClient", Recorder)
        monkeypatch.setattr(MidniteHub, "RECONNECT_DELAY", 0)
        monkeypatch.setattr(hub_module.time, "sleep", lambda seconds: None)
        Recorder.read_result = Result(error=True)
        Recorder.log = []
        Recorder.instances = []
        hub = MidniteHub("192.168.88.53", 502)
        hub._client = Recorder()
        assert hub.read_holding_registers(4113, 1, retries=3) is None

    def test_the_default_read_retries_are_five(self, monkeypatch):
        """Nothing else pins the default; it is the knob that bounds a failing block.

        Pin it so a future edit cannot quietly cut the number of Modbus
        transactions a dead register is given before it is marked unavailable.
        """
        import inspect

        default = inspect.signature(MidniteHub.read_holding_registers).parameters["retries"].default
        assert default == 5

    def test_a_read_that_times_out_reconnects(self, monkeypatch):
        """pymodbus' "no response" ModbusIOException is a dead socket, not a bad register.

        On a device that drops idle connections, matching neither errno nor the old
        message fragments meant all retries ran against the same half-open pipe.
        """

        class TimesOut(Recorder):
            def read_holding_registers(self, address=0, count=1, **kwargs):
                from pymodbus.exceptions import ModbusIOException

                raise ModbusIOException("Modbus Error: [Input/Output] no response")

        hub = make_hub(monkeypatch, TimesOut)
        hub._client = TimesOut()
        hub._client.open = True
        Recorder.log = []
        assert hub.read_holding_registers(4113, 1, retries=2) is None
        connects = [event for event in Recorder.log if event[0] == "connect"]
        assert connects, "a read timeout must force a reconnect, not retry the dead pipe"

    def test_a_dead_socket_is_replaced_and_the_read_retried(self, monkeypatch):
        hub = make_hub(monkeypatch)
        first = hub._client

        class DiesOnRead(Recorder):
            def read_holding_registers(self, address=0, count=1, **kwargs):
                raise ConnectionResetError(104, "Connection reset by peer")

        monkeypatch.setattr(hub_module, "ModbusTcpClient", DiesOnRead)
        hub._client = DiesOnRead()
        hub._client.open = True
        Recorder.log = []
        assert hub.read_holding_registers(4113, 1, retries=2) is None
        closes = [event for event in Recorder.log if event[0] == "close"]
        connects = [event for event in Recorder.log if event[0] == "connect"]
        assert closes and len(connects) == len(closes), "one closed, one opened"

    def test_the_client_is_never_left_two_deep(self, monkeypatch):
        """Every reconnect closes before it opens, so the device never sees two clients."""
        hub = make_hub(monkeypatch)
        order = []

        class Logging(Recorder):
            def connect(self):
                order.append("connect")
                return super().connect()

            def close(self):
                order.append("close")
                super().close()

        monkeypatch.setattr(hub_module, "ModbusTcpClient", Logging)
        hub._client = Logging()
        hub._client.open = True
        hub._reconnect()
        assert order[:2] == ["close", "connect"]


class TestWriting:
    def test_a_good_write_reaches_the_wire(self, monkeypatch):
        hub = make_hub(monkeypatch)
        hub._client.open = True
        hub.set_serial_number(0x12345678)
        hub.write_register(4149, 576)
        assert (4148, 576) in Recorder.writes

    def test_a_write_that_keeps_being_refused_is_handed_back(self, monkeypatch):
        """The caller decides what a refused write means; the hub does not loop forever."""

        class RefusesSettings(Recorder):
            """Answers the unlock, refuses the setting - a clamping Classic."""

            def write_register(self, address=0, value=0, **kwargs):
                unlock = address in (20491, 20492)
                Recorder.writes.append((address, value))
                return Result(error=not unlock)

        monkeypatch.setattr(hub_module, "ModbusTcpClient", RefusesSettings)
        monkeypatch.setattr(MidniteHub, "RECONNECT_DELAY", 0)
        monkeypatch.setattr(hub_module.time, "sleep", lambda seconds: None)
        Recorder.log, Recorder.instances, Recorder.writes = [], [], []
        hub = MidniteHub("192.168.88.53", 502)
        hub._client.open = True
        hub.set_serial_number(0x12345678)
        result = hub.write_register(4149, 576, retries=2)
        assert result.isError() is True
        assert Recorder.writes.count((4148, 576)) == 2, "it tried twice and stopped"

    def test_a_stale_socket_during_unlock_reconnects_instead_of_raising(self, monkeypatch):
        """The unlock is a write too; a half-open socket must reconnect, not escape.

        Before the fix the raw unlock write sat outside the guarded block, so the
        first setting press after an idle drop failed with a bare connection error
        instead of the reconnect the file promises.
        """

        class DiesOnFirstUnlock(Recorder):
            raised = False

            def write_register(self, address=0, value=0, **kwargs):
                # Unlock registers on the wire are 20491/20492; fail the first one
                # with a connection error, then behave normally.
                if address in (20491, 20492) and not DiesOnFirstUnlock.raised:
                    DiesOnFirstUnlock.raised = True
                    raise ConnectionResetError(104, "Connection reset by peer")
                Recorder.writes.append((address, value))
                return Recorder.write_result

        DiesOnFirstUnlock.raised = False
        hub = make_hub(monkeypatch, DiesOnFirstUnlock)
        hub._client = DiesOnFirstUnlock()
        hub._client.open = True
        Recorder.log = []
        hub.set_serial_number(0x12345678)
        result = hub.write_register(4149, 576, retries=3)
        assert not result.isError()
        assert (4148, 576) in Recorder.writes, "the setting landed after the reconnect"
        connects = [event for event in Recorder.log if event[0] == "connect"]
        assert connects, "the unlock failure forced a reconnect"

    def test_a_write_with_no_connection_at_all_says_so(self, monkeypatch):
        """Not a Modbus error - there is nothing to write to."""
        monkeypatch.setattr(MidniteHub, "RECONNECT_DELAY", 0)
        monkeypatch.setattr(hub_module.time, "sleep", lambda seconds: None)

        class NeverConnects(Recorder):
            def connect(self):
                self.open = False
                return False

        monkeypatch.setattr(hub_module, "ModbusTcpClient", NeverConnects)
        hub = MidniteHub("192.168.88.53", 502)
        hub._client = NeverConnects()
        hub.set_serial_number(0x12345678)
        with pytest.raises(OSError):
            hub.write_register(4149, 576, retries=2)


class TestResetting:
    def test_a_reset_leaves_the_client_disconnected(self, monkeypatch):
        hub = make_hub(monkeypatch)
        hub._client.open = True
        hub.reset()
        assert hub._client.is_socket_open() is False

    def test_a_reset_creates_a_fresh_client(self, monkeypatch):
        hub = make_hub(monkeypatch)
        before = hub._client
        hub.reset()
        assert hub._client is not before

    def test_the_wait_falls_between_the_close_and_the_new_client(self, monkeypatch):
        """The device must be allowed to drop the old session before a new one."""
        hub = make_hub(monkeypatch)
        order = []

        class Logging(Recorder):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                order.append("client created")

            def close(self):
                order.append("close")
                super().close()

        monkeypatch.setattr(hub_module, "ModbusTcpClient", Logging)
        monkeypatch.setattr(hub_module.time, "sleep", lambda seconds: order.append("wait"))
        hub._client = Logging()
        hub._client.open = True
        order.clear()
        hub.reset()
        assert order[:3] == ["close", "wait", "client created"]

    def test_the_reconnect_wait_is_bounded(self):
        """Long enough for the Classic to notice, short enough not to hang a poll."""
        assert 0 < MidniteHub.RECONNECT_DELAY <= 5

    def test_the_default_socket_timeout_is_not_infinite(self):
        assert 0 < MidniteHub.DEFAULT_TIMEOUT <= 10
