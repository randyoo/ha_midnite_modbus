"""The Classic's onboard daily datalogger (internal file device 5).

The AIR app reads its history charts from the device itself with 96 private
function-104 reads (`DataMenu.as`), 32 little-endian u16 days per read, newest
day first at byte offset `62 - 2n`, one read per category in the order
3, 6, 0, 2, 4, 5, 7, 8 per block of 32 slots (PROTOCOL.md section 6). This
suite pins that byte-level contract, and the one app behaviour it refuses to
copy: a Modbus exception decoded as data (garbage days).

The category-3 day field was bench-open (PROTOCOL.md section 11) and the
2026-09-22 sweep closed it: day is 5 bits, month 4, year-2000 7 (FINDINGS 41)
- the AIR app's 4-bit parse is what produced its garbage days. The fixtures
here are REAL sweep values, past-15th days included.
"""

from __future__ import annotations

import asyncio
import datetime
from types import SimpleNamespace

import pytest
from fakes import FakeApi, RecordingInternalApi
from homeassistant.core import Hass

from midnite_solar import bridge as bridge_module
from midnite_solar import datalogger
from midnite_solar.coordinator import OP_TIMEOUT
from midnite_solar.datalogger import (
    DAYS_PER_READ,
    LOGGER_FILE_DEVICE,
    READ_BYTES,
    SWEEP_BLOCKS,
    SWEEP_CATEGORIES,
    SWEEP_DAY_SLOTS,
    SWEEP_READ_RETRIES,
    Datalogger,
    async_sweep,
    day_address,
    decode_date,
    decode_float_time,
    decode_time_of_day,
    unpack_newest_first,
)


def newest_first_payload(values: list) -> bytes:
    """Pack days (newest first) as the Classic packs one 64-byte read."""
    buf = [0] * READ_BYTES
    for n, value in enumerate(values):
        buf[READ_BYTES - 2 - 2 * n] = value & 0xFF
        buf[READ_BYTES - 1 - 2 * n] = (value >> 8) & 0xFF
    return bytes(buf)


def date_raw(day: datetime.date) -> int:
    """Pack a date the way the BENCH says the Classic packs it (FINDINGS 41):
    day in 5 bits, month in the next 4, year-2000 above - NOT the app's
    4-bit parse, which the hardware refuted."""
    return ((day.year - 2000) & 0x7F) << 9 | (day.month & 0x0F) << 5 | day.day & 0x1F


class TestDayAddress:
    def test_the_address_is_the_category_shifted_and_the_slot_masked(self):
        # (DataMenu.as:513): "(catIndex & 0x3F) << 10 | (daySlot & 0x3FF)"
        assert day_address(3, 0) == 3 << 10
        assert day_address(3, 32) == (3 << 10) + 32
        assert day_address(8, 1024 + 5) == (8 << 10) | 5

    def test_the_sweep_covers_just_over_a_year(self):
        assert SWEEP_BLOCKS * DAYS_PER_READ >= SWEEP_DAY_SLOTS
        assert SWEEP_BLOCKS == 12


class TestUnpack:
    def test_day_zero_is_the_newest_at_the_end_of_the_payload(self):
        values = [n * 100 + 7 for n in range(DAYS_PER_READ)]
        assert unpack_newest_first(newest_first_payload(values)) == values

    def test_a_short_payload_is_not_data(self):
        assert unpack_newest_first(b"") is None
        assert unpack_newest_first(b"\x00" * 63) is None

    def test_little_endian_within_the_register(self):
        # day 0 = 0xABCD stored LE: low byte CD at offset 62, AB at 63.
        payload = bytearray(64)
        payload[62] = 0xCD
        payload[63] = 0xAB
        assert unpack_newest_first(bytes(payload))[0] == 0xABCD


class TestDateQuirks:
    def test_a_dated_slot_decodes(self):
        assert decode_date(date_raw(datetime.date(2026, 9, 11))) == datetime.date(
            2026, 9, 11
        )

    def test_an_empty_slot_decodes_to_no_day(self):
        assert decode_date(0) is None

    def test_the_bench_layout_reads_days_past_15(self):
        """Real values from the 2026-09-22 sweep (FINDINGS 41).

        The AIR app's 4-bit day parse turns each of these into an
        impossible month; the hardware packs day(5) month(4) year(7), and
        the whole answered ring - a factory-era year of 2000 dates included
        - reads as a calendar only this way. These are exactly the days the
        AIR app itself showed as garbage.
        """
        assert decode_date(0x3559) == datetime.date(2026, 10, 25)
        assert decode_date(0x3569) == datetime.date(2026, 11, 9)
        assert decode_date(0x107) == datetime.date(2000, 8, 7)
        assert decode_date(0x198) == datetime.date(2000, 12, 24)
        # The app's own parse, kept here to show WHAT it breaks with:
        app_day, app_month = 0x3559 & 0xF, (0x3559 >> 4) & 0x1F
        assert (app_day, app_month) == (9, 21)  # month 21: garbage days

    def test_unwritten_slots_stay_fossils_not_dates(self):
        """The sweep's answered-but-never-dated RAM (month nibbles 13-15
        beside a day) decodes to an absent day. The Classic answers EVERY
        slot - absence is a decode verdict, never a Modbus exception."""
        for fossil in (0x1F8, 0x1E8, 0x1D8, 0x1C8, 0x1B8):
            assert decode_date(fossil) is None

    def test_float_time_splits_like_the_app(self):
        assert decode_float_time(3725) == {"hours": 1, "minutes": 2}

    def test_time_of_day_has_no_seconds(self):
        raw = 14 << 6 | 30
        assert decode_time_of_day(raw) == {"hour": 14, "minute": 30}


class TestStoreMerge:
    def test_scaled_categories_divide_and_keep_the_raw(self):
        store = self.mapped_store(0, [1234])
        day = store.as_dict()["days"][0]
        assert day["kwh"] == pytest.approx(123.4)
        assert day["kwh_raw"] == 1234

    def mapped_store(self, category, values):
        """A store holding one dated day plus one category's values."""
        store = Datalogger()
        dates = [date_raw(datetime.date(2026, 9, 11))] + [0] * 31
        store.merge_read(0, 3, newest_first_payload(dates))
        store.merge_read(0, category, newest_first_payload(values + [0] * 31))
        return store

    def test_every_scaled_category_matches_the_app(self):
        checks = {
            0: ("kwh", 1000, 100.0),
            4: ("high_power_kw", 3000, 3.0),
            5: ("high_temp_c", 235, 23.5),
            7: ("vpv", 2513, 251.3),
            8: ("vbatt", 512, 51.2),
        }
        for category, (field, raw, expected) in checks.items():
            store = self.mapped_store(category, [raw])
            assert store.as_dict()["days"][0][field] == pytest.approx(expected)

    def test_a_undated_day_is_reported_absent_not_as_zero(self):
        store = self.mapped_store(0, [999])
        answer = store.as_dict()
        assert len(answer["days"]) == 1
        assert "float_seconds" not in answer["days"][0]

    def test_the_categories_of_one_block_line_up_by_day(self):
        store = Datalogger()
        dates = [date_raw(datetime.date(2026, 9, d)) for d in (11, 10)] + [0] * 30
        store.merge_read(0, 3, newest_first_payload(dates))
        store.merge_read(0, 0, newest_first_payload([100, 200] + [0] * 30))
        days = store.as_dict()["days"]
        assert [day["date"] for day in days] == ["2026-09-11", "2026-09-10"]
        assert days[0]["kwh"] == pytest.approx(10.0)
        assert days[1]["kwh"] == pytest.approx(20.0)

    def test_a_short_read_merges_nothing(self):
        store = Datalogger()
        assert store.merge_read(0, 0, b"\x01" * 10) is False
        assert store.slots == {}

    def test_two_slots_holding_one_date_answer_one_day(self):
        """The API speaks dates; the slot numbering is the Classic's."""
        store = Datalogger()
        dated = [date_raw(datetime.date(2026, 9, 11))] + [0] * 31
        store.merge_read(0, 3, newest_first_payload(dated))
        store.merge_read(1, 3, newest_first_payload(dated))
        assert len(store.as_dict()["days"]) == 1


def run_sweep(api, monkeypatch):
    """A sweep at test speed: the pacing gap patched to zero."""
    monkeypatch.setattr(datalogger, "READ_GAP_SECONDS", 0)
    store = Datalogger()
    answer = asyncio.run(async_sweep(Hass(), api, store))
    return store, answer


class TestSweep:
    def dated_api(self, **kwargs):
        dates = [date_raw(datetime.date(2026, 9, 11))] + [0] * 31
        return RecordingInternalApi(payload=newest_first_payload(dates), **kwargs)

    def test_the_sweep_reads_the_whole_window(self, monkeypatch):
        api = self.dated_api()
        store, answer = run_sweep(api, monkeypatch)
        assert answer["sweep"]["reads"] == SWEEP_BLOCKS * len(SWEEP_CATEGORIES)
        assert api.internal_reads[0] == (LOGGER_FILE_DEVICE, READ_BYTES, day_address(3, 0), SWEEP_READ_RETRIES)

    def test_the_read_order_per_block_is_the_apps(self, monkeypatch):
        api = self.dated_api()
        run_sweep(api, monkeypatch)
        first_block = [a for _d, _l, a, _r in api.internal_reads][: len(SWEEP_CATEGORIES)]
        assert first_block == [day_address(c, 0) for c in SWEEP_CATEGORIES]

    def test_a_dated_day_comes_back(self, monkeypatch):
        _store, answer = run_sweep(self.dated_api(), monkeypatch)
        assert answer["days"][0]["date"] == "2026-09-11"

    def test_an_exception_skips_the_category_and_never_invents_data(self, monkeypatch):
        """The app decoded func-104 exceptions as data; this counts and skips."""
        missing = day_address(4, 1 * DAYS_PER_READ)
        api = self.dated_api(fail_addresses={missing})
        _store, answer = run_sweep(api, monkeypatch)
        assert answer["sweep"]["exceptions"] == 1
        assert answer["sweep"]["reads"] == SWEEP_BLOCKS * len(SWEEP_CATEGORIES)

    def test_a_sweep_of_a_silent_classic_answers_empty_not_wrong(self, monkeypatch):
        api = FakeApi()  # the base double answers internal reads with nothing
        _store, answer = run_sweep(api, monkeypatch)
        assert answer["days"] == []
        assert answer["sweep"]["exceptions"] == SWEEP_BLOCKS * len(SWEEP_CATEGORIES)

    def test_one_read_holds_the_lock_well_under_the_watchdog(self):
        """The same arithmetic the coordinator pins for its own reads.

        A sweep chunk bigger than one read would sit on the hub lock past
        OP_TIMEOUT while the poll waits, and the watchdog would reset the
        client mid-sweep.
        """
        worst_attempt = 3.0 + 2.0 + 3.0  # socket timeout + reconnect delay + connect
        assert SWEEP_READ_RETRIES * worst_attempt < OP_TIMEOUT

    def test_reads_are_paced_so_the_poll_can_interleave(self):
        """The gap is real and nonzero: 96 back-to-back reads would starve
        the coordinator's own poll against the one hub lock."""
        assert datalogger.READ_GAP_SECONDS > 0

    def test_the_sweep_flags_the_store_for_its_whole_run(self, monkeypatch):
        # The bridge answers GET /datalogger with `sweeping` while a sweep
        # runs, so a client tells "chart loading" from "nothing logged";
        # the flag is also the single-flight token for the next test.
        seen = []

        class FlagSpy(RecordingInternalApi):
            def read_internal(self, *args):
                seen.append(store.sweeping)
                return super().read_internal(*args)

        monkeypatch.setattr(datalogger, "READ_GAP_SECONDS", 0)
        store = Datalogger()
        # The store the bridge uses must be THIS store - else the spy
        # watches a different object than the one the flag is raised on.
        coordinator = SimpleNamespace(api=FlagSpy(payload=b"\x00" * 64), datalogger=store)
        assert store.as_dict()["sweeping"] is False
        answer = asyncio.run(
            bridge_module.async_bridge_datalogger(Hass(), coordinator)
        )
        assert len(seen) == SWEEP_BLOCKS * len(SWEEP_CATEGORIES)
        assert all(seen), "the flag must stand for every read of the sweep"
        # The answer that COMPLETES the sweep is written after the flag
        # fell: nobody is told "still loading" about data already in hand.
        assert answer["sweeping"] is False

    def test_a_caller_joining_a_running_sweep_stamps_nothing(self):
        # Mid-sweep, a second caller (the background collector, or another
        # PIN-gated refresh) gets the cache AS IT STANDS, flagged - joining
        # the pass, never stampeding a second one onto the one connection.
        api = RecordingInternalApi(payload=b"\x00" * 64)
        store = Datalogger()
        store.sweeping = True
        coordinator = SimpleNamespace(api=api, datalogger=store)
        answer = asyncio.run(
            bridge_module.async_bridge_datalogger(Hass(), coordinator)
        )
        assert answer["sweeping"] is True
        assert api.internal_reads == [], "the joiner put reads on the wire"
        assert store.sweeping is True, "the joiner must not clear the flag"
