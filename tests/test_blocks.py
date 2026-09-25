"""Tests for block reads: fewer requests, same values, graceful fallback."""

from __future__ import annotations

import asyncio

from fakes import FakeApi, ModbusResult
from midnite_solar.const import REGISTER_GROUPS, REGISTER_MAP
from midnite_solar.coordinator import (
    MAX_BLOCK_GAP,
    MAX_BLOCK_SPAN,
    MidniteSolarUpdateCoordinator,
    register_blocks,
)

from homeassistant.core import Hass


def blocks_for(group):
    return register_blocks(REGISTER_GROUPS[group])


def coordinator(api):
    coordinator = MidniteSolarUpdateCoordinator(
        Hass(), "192.168.88.53", 502, interval=15
    )
    coordinator.api = api
    return coordinator


def read_group(api, registers):
    return asyncio.run(coordinator(api)._read_register_group(registers, "test"))


class TestRegisterBlocks:
    """How the register lists are chopped into requests."""

    def test_contiguous_registers_are_one_request(self):
        assert blocks_for("status") == [(4113, 4124)]
        assert blocks_for("energy") == [(4125, 4129)]
        assert blocks_for("temperatures") == [(4132, 4134)]
        assert blocks_for("serial") == [(28673, 28674)]
        assert blocks_for("network") == [(20481, 20491)]
        assert blocks_for("aux_settings") == [(4165, 4181)]

    def test_a_long_gap_starts_a_new_block(self):
        assert register_blocks([4101, 4102, 4200, 4201]) == [(4101, 4102), (4200, 4201)]

    def test_a_gap_at_the_limit_still_joins(self):
        assert register_blocks([4101, 4101 + MAX_BLOCK_GAP]) == [
            (4101, 4101 + MAX_BLOCK_GAP)
        ]

    def test_a_block_never_exceeds_the_span(self):
        # Pin against an absolute register count, not MAX_BLOCK_SPAN itself: a test
        # that compares to the constant under test cannot notice the constant being
        # raised (the reason for the cap is the card's 125-register limit, and we
        # want a real ceiling). A 100-register run forces the cap to fire.
        assert MAX_BLOCK_SPAN <= 32
        for group in REGISTER_GROUPS:
            for first, last in blocks_for(group):
                assert last - first + 1 <= 32, group
        long_run = register_blocks(list(range(5000, 5100)))
        assert long_run and all(last - first + 1 <= 32 for first, last in long_run), (
            "a run longer than the cap is actually split"
        )

    def test_every_wanted_register_is_covered_exactly_once(self):
        for group, registers in REGISTER_GROUPS.items():
            wanted = set(registers)
            covered = []
            for first, last in blocks_for(group):
                covered += [r for r in range(first, last + 1) if r in wanted]
            assert sorted(covered) == sorted(wanted), group
            assert len(covered) == len(set(covered)), group

    def test_the_request_count_drops_by_an_order_of_magnitude(self):
        """The whole reason for this: one request per register was ~93 an interval.

        The two numbers are pinned so adding a register cannot quietly undo the
        blocking: a new register should land in a block that is already read.
        """
        per_register = sum(len(set(r)) for r in REGISTER_GROUPS.values())
        blocks = sum(len(blocks_for(group)) for group in REGISTER_GROUPS)
        # 122 registers in 25 blocks: the clock group (4214-4218) is 5
        # consecutive registers in one added block; the settings group gained
        # the two Enable-Flags registers (4186-4187), one more block.
        assert per_register == 122
        assert blocks == 25
        assert blocks * 4 < per_register

    def test_the_modbus_address_register_is_read_on_its_own(self):
        """4326 is the Classic's own Modbus address, 160 registers past 4163."""
        assert (4326, 4326) in blocks_for("eeprom_settings")

    def test_the_eeprom_block_spans_the_write_only_force_flags(self):
        """Bench-confirmed: a read spanning W registers 4160/4161 comes back whole.

        A holding-register read of 4154..4163 on a real Classic answered with all
        ten registers, so there is no reason to split the block and a new request.
        """
        eeprom = blocks_for("eeprom_settings")
        assert (4154, 4163) in eeprom
        assert register_blocks([4159, 4162]) == [(4159, 4162)]

    def test_the_read_hostile_unlock_registers_are_never_in_a_block(self):
        """20492/20493 reject a read; they are write-only and no group polls them."""
        unlock = {REGISTER_MAP["UNLOCK_SERIAL_MSB"], REGISTER_MAP["UNLOCK_SERIAL_LSB"]}
        for group, registers in REGISTER_GROUPS.items():
            assert not unlock & set(registers), f"{group} polls an unlock register"
            for first, last in blocks_for(group):
                assert not any(first <= u <= last for u in unlock), (
                    f"{group} block {first}-{last} would read an unlock register"
                )


class TestBlockReads:
    """Values must land exactly where the one-per-request code put them."""

    def test_a_block_fills_every_register_it_covers(self):
        api = FakeApi(read_values={4113 + i: 100 + i for i in range(12)})
        assert read_group(api, REGISTER_GROUPS["status"]) == {
            4113 + i: 100 + i for i in range(12)
        }
        assert api.reads == [4113], "one request for twelve registers"

    def test_a_word_between_the_registers_we_want_is_ignored(self):
        api = FakeApi(read_values={4101: 60, 4102: 5, 4103: 99})
        assert read_group(api, [4101, 4102]) == {4101: 60, 4102: 5}

    def test_a_failed_block_is_read_register_by_register(self):
        """A register the card will not answer must not black out its neighbours."""
        api = FakeApi(
            read_values={4113: 600, 4114: 540, 4115: 300},
            bad_blocks={(4113, 12)},
        )
        data = read_group(api, REGISTER_GROUPS["status"])
        assert {reg: data[reg] for reg in (4113, 4114, 4115)} == {
            4113: 600,
            4114: 540,
            4115: 300,
        }
        assert api.reads[0] == 4113, "the block was attempted first"
        assert len(api.reads) > 1, "then the registers went individually"

    def test_a_short_answer_falls_back_to_singles(self):
        api = FakeApi(read_values={4113: 600, 4114: 540})
        original = api.read_holding_registers

        def short(address, count=1, retries=5):
            if count > 1:
                return ModbusResult(registers=[600])
            return original(address, 1, retries)

        api.read_holding_registers = short
        assert read_group(api, [4113, 4114]) == {4113: 600, 4114: 540}

    def test_a_register_that_never_answers_is_the_only_one_lost(self):
        api = FakeApi(
            read_values={4113: 600, 4114: 540},
            bad_blocks={(4113, 12)},
            unreadable_registers={4114},
        )
        data = read_group(api, REGISTER_GROUPS["status"])
        assert 4114 not in data
        assert data[4113] == 600

    def test_an_empty_group_reads_nothing(self):
        api = FakeApi()
        assert read_group(api, []) is None
        assert api.reads == []

    def test_a_group_that_answers_nothing_reports_no_data(self):
        api = FakeApi(unreadable=True)
        assert read_group(api, REGISTER_GROUPS["energy"]) is None
