"""Tests for a coordinator update: what it reads, and what it says when it fails.

The update is where the integration either reaches the Classic or does not. The
behaviours worth pinning are the ones that decide whether a user sees stale data
presented as live: which register is knocked on first, what happens to the rest of
the data when one group does not answer, and that a wedged read fails the update
instead of hanging the poll.
"""

from __future__ import annotations

import asyncio

import pytest
from fakes import FakeApi, ModbusResult
from homeassistant.core import Hass

from midnite_solar import coordinator as coordinator_module
from midnite_solar.const import REGISTER_GROUPS, REGISTER_MAP
from midnite_solar.coordinator import MidniteSolarUpdateCoordinator
from homeassistant.exceptions import UpdateFailed

UNIT_ID = REGISTER_MAP["UNIT_ID"]
FALLBACK = REGISTER_MAP["DISP_AVG_VBATT"]
SERIAL_MSB = REGISTER_MAP["SERIAL_NUMBER_MSB_RO"]
SERIAL_LSB = REGISTER_MAP["SERIAL_NUMBER_LSB_RO"]


def make(api):
    coordinator = MidniteSolarUpdateCoordinator(Hass(), "192.168.88.53", 502, interval=15)
    coordinator.api = api
    return coordinator


def update(api):
    return asyncio.run(make(api)._async_update_data())


class TestASuccessfulUpdate:
    def test_every_group_is_returned(self):
        data = update(FakeApi())
        assert set(data["data"]) == set(REGISTER_GROUPS)

    def test_nothing_is_marked_unavailable(self):
        assert update(FakeApi())["availability"] == {}

    def test_the_values_land_on_their_own_registers(self):
        api = FakeApi(read_values={UNIT_ID: 200, REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"]: 576})
        data = update(api)
        assert data["data"]["device_info"][UNIT_ID] == 200
        assert data["data"]["setpoints"][REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"]] == 576

    def test_a_block_read_lands_on_every_register_it_covers(self):
        """4113-4124 is one request; the twelve values have to be sorted out."""
        api = FakeApi(read_values={4113 + offset: offset for offset in range(12)})
        data = update(api)
        assert data["data"]["status"] == {4113 + offset: offset for offset in range(12)}

    def test_the_update_is_the_data_plus_availability_and_nothing_else(self):
        assert sorted(update(FakeApi())) == ["availability", "data"]

    def test_the_serial_number_is_handed_to_the_hub(self):
        api = FakeApi(read_values={SERIAL_MSB: 0x1234, SERIAL_LSB: 0x5678})
        update(api)
        assert api._serial == 0x12345678


class TestTheRetryBudgetFitsTheCap:
    """_safe_read cannot recall an executor thread when OP_TIMEOUT fires.

    The abandoned thread keeps holding the hub lock and can swap the client
    behind the next cycle, so the retry count the coordinator asks the hub for
    must have a worst case that fits under the cap - not the hub's own default.
    """

    def test_the_worst_case_of_a_block_read_is_under_the_operation_cap(self):
        import inspect

        from midnite_solar.hub import MidniteHub

        # One attempt against a half-dead port: full socket timeout, then a
        # full reconnect (RECONNECT_DELAY plus a fresh connect that itself
        # gets the full timeout), plus that attempt's backoff sleep.
        per_attempt = MidniteHub.DEFAULT_TIMEOUT + MidniteHub.RECONNECT_DELAY + MidniteHub.DEFAULT_TIMEOUT
        worst = sum(
            per_attempt + 0.2 * (attempt + 1)
            for attempt in range(coordinator_module.READ_RETRIES)
        )
        assert worst < coordinator_module.OP_TIMEOUT, f"{worst}s would outlive the {coordinator_module.OP_TIMEOUT}s cap"
        hub_default = inspect.signature(MidniteHub.read_holding_registers).parameters["retries"].default
        assert coordinator_module.READ_RETRIES < hub_default, (
            "the coordinator must ask for fewer retries than the hub defaults to"
        )


class TestTheConnectionTest:
    """The first read decides whether the rest of the update is even attempted."""

    def test_the_first_register_knocked_on_is_the_unit_id(self):
        api = FakeApi()
        update(api)
        assert api.reads[0] == UNIT_ID

    def test_a_silent_unit_id_register_gets_a_second_chance(self):
        api = FakeApi(unreadable_registers={UNIT_ID})
        update(api)
        assert FALLBACK in api.reads, "the connection test tries another register"

    def test_a_classic_that_answers_neither_is_not_ready(self):
        api = FakeApi(
            bad_blocks={(UNIT_ID, 1), (FALLBACK, 1)},
            unreadable_registers={UNIT_ID, FALLBACK},
        )
        with pytest.raises(UpdateFailed):
            update(api)

    def test_nothing_is_polled_after_the_connection_test_fails(self):
        api = FakeApi(unreadable=True)
        with pytest.raises(UpdateFailed):
            update(api)
        assert len(api.reads) <= 2, "the connection test does not go on to read 22 blocks"


class TestAGroupThatDoesNotAnswer:
    def test_the_other_groups_still_come_back(self):
        api = FakeApi(bad_blocks={(4113, 12)}, unreadable_registers=set(range(4113, 4125)))
        data = update(api)
        assert "status" not in data["data"]
        assert "setpoints" in data["data"]

    def test_the_group_that_failed_is_marked_unavailable(self):
        api = FakeApi(bad_blocks={(4113, 12)}, unreadable_registers=set(range(4113, 4125)))
        data = update(api)
        for address in REGISTER_GROUPS["status"]:
            assert address in [int(key) for key in data["availability"]]

    def test_the_registers_that_did_answer_are_not_marked(self):
        api = FakeApi(bad_blocks={(4113, 12)}, unreadable_registers=set(range(4113, 4125)))
        data = update(api)
        assert REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"] not in [
            int(key) for key in data["availability"]
        ]

    def test_a_partial_failure_is_not_an_availability_problem(self):
        """One register missing is not a group failure; the block fallback covers it."""
        api = FakeApi(bad_blocks={(4113, 12)}, unreadable_registers={4114})
        data = update(api)
        assert data["data"]["status"][4113] == 0
        assert 4114 not in data["data"]["status"]
        assert data["availability"] == {}


class TestAWedgedRead:
    """A read that never returns must fail the update, not hang Home Assistant."""

    class Wedged:
        def __init__(self):
            self.resets = 0
            self.reads = []

        async def read_holding_registers(self, address, count=1, retries=5):
            import asyncio

            self.reads.append(address)
            await asyncio.sleep(0.2)
            return ModbusResult(registers=[0] * count)

        def reset(self):
            self.resets += 1

        def set_serial_number(self, serial):
            self._serial = serial

    def test_a_wedged_read_raises_instead_of_stalling(self, monkeypatch):
        monkeypatch.setattr(coordinator_module, "OP_TIMEOUT", 0.01)
        with pytest.raises(UpdateFailed):
            update(self.Wedged())

    def test_the_connection_is_reset_after_a_wedge(self, monkeypatch):
        monkeypatch.setattr(coordinator_module, "OP_TIMEOUT", 0.01)
        api = self.Wedged()
        with pytest.raises(UpdateFailed):
            update(api)
        assert api.resets == 1, "the wedged socket must not be left for the next poll"

    def test_the_error_names_the_register_that_wedged(self, monkeypatch):
        monkeypatch.setattr(coordinator_module, "OP_TIMEOUT", 0.01)
        with pytest.raises(UpdateFailed) as err:
            update(self.Wedged())
        assert str(UNIT_ID) in str(err.value)


class TestReadingBackAValue:
    def test_a_value_that_was_read(self):
        coordinator = make(FakeApi())
        coordinator.data = {"data": {"setpoints": {4149: 576}}, "availability": {}}
        assert coordinator.get_register_value(4149) == 576

    def test_a_register_that_was_never_polled(self):
        coordinator = make(FakeApi())
        coordinator.data = {"data": {"setpoints": {4149: 576}}, "availability": {}}
        assert coordinator.get_register_value(4242) is None

    def test_a_group_that_failed_the_update(self):
        coordinator = make(FakeApi())
        coordinator.data = {"data": {}, "availability": {"4149": False}}
        assert coordinator.get_register_value(4149) is None

    def test_before_the_first_update(self):
        assert make(FakeApi()).get_register_value(4149) is None
