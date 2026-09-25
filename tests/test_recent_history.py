"""The Classic's onboard recent-history log (internal file device 6).

FINDINGS section 52 is the bench contract this suite pins: device 6 answers
device-5-shaped reads (64 bytes = 32 little-endian u16, newest sample first
at byte offset `62 - 2n`), timestamps must STRICTLY descend one sample per
slot, and reads past the ring's ~384-sample retention do not fail - they
ECHO the newest window with no Modbus exception at all. A client that trusts
slots over timestamps would chart the same afternoon twenty times, so the
walk's chain filter is the product, and these tests are its proof.

The synthetic ring below reproduces the firmware's signature lies: slots the
ring never held answer with words whose month nibble is 0 (undecodable), and
`echo_from` makes every block that STARTS at or past the depth answer a copy
of block zero - the bench's aliasing, exception-free. Date words follow the
FINDINGS section 46 layout: month in 4 low bits, day in the next 5,
year-2000 above.
"""

from __future__ import annotations

import asyncio
import datetime
from types import SimpleNamespace

from fakes import FakeApi, ModbusResult
from midnite_solar import bridge as bridge_module, recent_history
from midnite_solar.recent_history import (
    RECENT_FILE_DEVICE,
    SAMPLES_PER_READ,
    TICK_MAX_BLOCKS,
    RecentHistory,
    _chain,
    _word_dt,
    async_full_walk,
    async_tick,
    recent_address,
)
import pytest

from homeassistant.core import Hass

RING_START = datetime.datetime(2026, 9, 25, 11, 42)
INTERVAL = 300


def date_word(when: datetime.date) -> int:
    return ((when.year - 2000) & 0x7F) << 9 | (when.day & 0x1F) << 4 | when.month & 0x0F


def time_word(when: datetime) -> int:
    return (when.hour & 0x1F) << 6 | when.minute & 0x3F


def sample_words(when: datetime, category: int) -> int:
    """One sample's word for one category, raw-mirror values (FINDINGS 52)."""
    if category == 3:
        return date_word(when.date())
    if category == 4:
        return time_word(when)
    # Values ride a per-hour ramp so samples differ; stage is a 4120 code.
    if category == 5:
        return 0x0303 + (when.minute % 2)
    return 500 + category * 100 + when.hour


class RingApi(FakeApi):
    """FakeApi answering device-6 reads slot by slot from an in-memory ring.

    `samples` is newest-first (datetime, raw category overrides). Slots the
    ring never held answer undecodable (month nibble 0); with `echo_from`
    set, a block that STARTS at or past the depth answers a copy of block
    zero - the bench unit's silent aliasing, exception-free. `fail_addresses`
    holds (category, block) pairs that answer with a Modbus exception.
    """

    def __init__(self, samples, *, echo_from=None, fail_addresses=()):
        super().__init__()
        self.samples = list(samples)
        self.echo_from = echo_from
        self.fail_addresses = set(fail_addresses)

    def _raw(self, index: int, category: int) -> int:
        when, raws = self.samples[index]
        if category in raws:
            return raws[category]
        return sample_words(when, category)

    def read_internal(self, device, length, address=0, retries: int = 5):
        self.internal_reads.append((device, length, address, retries))
        category, first_slot = address >> 10, address & 0x3FF
        if (category, first_slot // SAMPLES_PER_READ) in self.fail_addresses:
            result = ModbusResult(error=True)
            result.payload = b""
            return result
        words = []
        for offset in range(SAMPLES_PER_READ):
            slot = first_slot + offset
            if (
                self.samples
                and self.echo_from is not None
                and first_slot >= self.echo_from
            ):
                words.append(self._raw(offset, category))
            elif slot < len(self.samples):
                words.append(self._raw(slot, category))
            else:
                words.append(0)
        buf = bytearray(64)
        for n, word in enumerate(words):
            buf[62 - 2 * n] = word & 0xFF
            buf[63 - 2 * n] = (word >> 8) & 0xFF
        result = ModbusResult()
        result.payload = bytes(buf)
        return result


def ring(n: int, *, start=RING_START, step=INTERVAL, **kwargs) -> RingApi:
    samples = [(start - datetime.timedelta(seconds=step * i), {}) for i in range(n)]
    return RingApi(samples, **kwargs)


def settings_coordinator(api, interval=INTERVAL, flags=0x4000):
    """A coordinator whose polled settings carry interval and LogAtNite."""
    return SimpleNamespace(
        api=api,
        data={"data": {"settings": {4136: interval, 4187: flags}}},
    )


class TestAddressing:
    def test_the_address_is_the_category_shifted_and_the_slot_masked(self):
        # Map section 1.3.2: "(category & 0x3F) << 10 | (sample & 0x3FF)".
        assert recent_address(0, 0) == 0
        assert recent_address(7, 0) == 7 << 10
        assert recent_address(3, 96) == (3 << 10) + 96
        assert recent_address(4, 1024 + 5) == (4 << 10) | 5

    def test_the_device_number_is_six(self):
        assert RECENT_FILE_DEVICE == 6


class TestWordDecoding:
    def test_a_slot_that_cannot_state_its_date_is_no_sample(self):
        # The month nibble 0 is the empty-slot pattern; a real date decodes.
        assert _word_dt(0x0000, time_word(RING_START)) is None
        assert _word_dt(date_word(RING_START.date()), time_word(RING_START)) == (
            RING_START
        )

    def test_impossible_dates_decode_to_none(self):
        feb30 = ((2026 - 2000) & 0x7F) << 9 | 30 << 4 | 2
        assert _word_dt(feb30, time_word(RING_START)) is None


class TestFullWalk:
    def collect(self, api, *, reason="cold"):
        store = RecentHistory()

        async def go():
            return await async_full_walk(
                Hass(),
                api,
                store,
                reason=reason,
                interval_sec=INTERVAL,
                log_at_nite=True,
            )

        return asyncio.run(go()), store

    def test_the_chain_stops_at_the_first_echo_and_the_walk_is_priced(self):
        # 100 real samples, then holes: the walk accepts 100, records where
        # the truth ended, and pays one timestamp pair per walked block plus
        # values for the accepted blocks only - never values past the depth.
        walk, _store = self.collect(ring(100))
        assert walk["kind"] == "full"
        assert walk["slots_collected"] == 100
        assert walk["chain_ended"] == "echo"
        assert walk["tail_rejected_at"] == 100
        # 4 timestamp blocks (8 reads; the 4th pair finds the first hole)
        # + values for the accepted blocks only (4 blocks x 6 categories).
        assert walk["reads"] == 8 + 24
        assert walk["exceptions"] == 0

    def test_accepted_samples_merge_with_scaled_and_raw_fields(self):
        # FINDINGS 52: every stored word is the raw display-register value;
        # the /10 is the display formula, and the charge stage stays a code.
        _walk, store = self.collect(ring(2))
        sample = store.as_dict()["samples"][-1]
        # cat 0's synthetic word is 500 + the hour: the stored raw is the
        # 4119-scale tenths, and the scaled field is the display value.
        # 4119 is whole watts: the raw mirror needs no /10 (the map's own
        # row says "[4119] Watts"; a /10 there showed the user a 10x dim
        # chart, which is how this got pinned).
        assert sample["power_w"] == pytest.approx(511)
        assert sample["power_w_raw"] == 511
        assert sample["stage"] == 0x0303 + (RING_START.minute % 2)
        assert "stage_raw" not in sample

    def test_the_ring_that_answers_nothing_collects_nothing_but_anchors(self):
        # A freshly powered Classic answers words that decode to nothing;
        # the walk must anchor (so ticks stop stampeding full walks) with
        # nothing collected.
        walk, store = self.collect(RingApi([]))
        assert walk["slots_collected"] == 0
        assert walk["chain_ended"] == "echo"
        assert store.anchored is True

    def test_a_failing_timestamp_pair_ends_the_walk_with_the_earlier_kept(
        self,
    ):
        # A Modbus exception on one pair (the only answer shape that ever
        # carries one) fails the chain, not the walk: block 0 stands, the
        # exception is counted, and no values are read past the failure.
        api = ring(80, fail_addresses={(4, 1)})
        walk, store = self.collect(api)
        assert walk["chain_ended"] == "fail-read"
        assert walk["exceptions"] == 1
        assert walk["slots_collected"] == SAMPLES_PER_READ
        assert len(store.samples) == SAMPLES_PER_READ

    def test_undated_slots_between_samples_end_the_walk(self):
        # The chain must be strictly descending: an undecodable hole at slot
        # 5 ends the walk there, and slots 6+ never get values read.
        holes = [
            (RING_START - datetime.timedelta(seconds=INTERVAL * i), {})
            for i in range(8)
        ]
        holes[5] = (holes[5][0], {3: 0x0000})
        walk, store = self.collect(RingApi(holes))
        assert walk["slots_collected"] == 5
        assert walk["tail_rejected_at"] == 5
        assert len(store.samples) == 5

    def test_the_walk_merges_by_timestamp_and_keeps_older_history(self):
        # The bridge, not the Classic, is the historian: a second walk must
        # not evict samples an earlier walk kept from a shallower ring.
        store = RecentHistory()
        asyncio.run(
            async_full_walk(
                Hass(),
                ring(64),
                store,
                reason="cold",
                interval_sec=INTERVAL,
                log_at_nite=False,
            )
        )
        assert len(store.samples) == 64
        asyncio.run(
            async_full_walk(
                Hass(),
                ring(96),
                store,
                reason="periodic",
                interval_sec=INTERVAL,
                log_at_nite=False,
            )
        )
        assert len(store.samples) == 96


class TestTick:
    def tick(
        self,
        api,
        *,
        n_cached=0,
        old_full_walk=0.0,
        interval=INTERVAL,
    ):
        """Cache the OLDEST `n_cached` samples of the ring, then beat.

        A real store trails the ring from behind: its head is some older
        sample and the ring head is the newest, so the cache is built from
        the tail of the newest-first sample list, newest-trailing like the
        truth.
        """
        store = RecentHistory()
        coordinator = settings_coordinator(api, interval=interval)

        async def go():
            for when, _raws in api.samples[-n_cached:] if n_cached else []:
                store.upsert(when, {"power_w": 0})
            if n_cached:
                store.anchored = True
                store.last_full_walk = asyncio.get_running_loop().time()
                store.last_full_walk -= old_full_walk
            return await async_tick(Hass(), coordinator, store)

        return asyncio.run(go()), store

    def test_a_cold_store_walks_the_window(self):
        walk, _store = self.tick(ring(8))
        assert walk["kind"] == "full"
        assert walk["reason"] == "cold"

    def test_a_boring_beat_costs_one_timestamp_pair_and_no_values(self):
        api = ring(8)
        walk, _store = self.tick(api, n_cached=8)
        assert walk["kind"] == "tick"
        assert walk["new_samples"] == 0
        assert walk["chain_ended"] == "caught-up"
        assert walk["reads"] == 2
        assert len(api.internal_reads) == 2

    def test_a_beat_merges_only_the_samples_newer_than_the_cache_head(self):
        api = ring(10)
        walk, store = self.tick(api, n_cached=4)
        assert walk["new_samples"] == 6
        assert walk["reads"] == 2 + 6  # one pair, then values for block 0
        assert len(store.samples) == 10

    def test_a_dead_head_under_a_cache_re_anchors(self):
        # A warm store whose ring head block decodes to nothing: the ring
        # rewrote (a boot blanks it), and the tick re-walks instead of
        # ticking on air.
        walk, _store = self.tick(RingApi([]), n_cached=8)
        assert walk["kind"] == "full"
        assert walk["reason"] == "head-echoed"

    def test_a_head_that_jumps_back_in_time_re_anchors(self):
        # The aliasing signature itself: the head block DESCENDS then
        # repeats - a forward jump mid-block is the ring echoing its newest
        # window, and no exception ever announces it.
        api = ring(8)
        # Corrupt block 0's timestamps so slot 2 reads LATER than slot 1.
        api.samples[2] = (
            api.samples[2][0],
            {4: time_word(RING_START + datetime.timedelta(minutes=8))},
        )

        async def go():
            store = RecentHistory()
            for when, _raws in api.samples:
                store.upsert(when - datetime.timedelta(seconds=4 * INTERVAL), {})
            store.anchored = True
            store.last_full_walk = asyncio.get_running_loop().time()
            return await async_tick(Hass(), settings_coordinator(api), store)

        walk = asyncio.run(go())
        assert walk["kind"] == "full"
        assert walk["reason"] == "head-echoed"

    def test_a_gap_the_head_blocks_cannot_bridge_re_walks(self):
        # Five blocks is a tick's reach; a cache older than the whole window
        # gets a full re-anchor instead of quietly charting Swiss cheese.
        far = [
            (
                RING_START - datetime.timedelta(seconds=INTERVAL * i),
                {},
            )
            for i in range(32 * TICK_MAX_BLOCKS + 4)
        ]
        api = RingApi(far)
        cached_head = RING_START - datetime.timedelta(seconds=INTERVAL * (1024 + 100))

        async def go():
            store = RecentHistory()
            store.upsert(cached_head, {"power_w": 0})
            store.anchored = True
            store.last_full_walk = asyncio.get_running_loop().time()
            return await async_tick(Hass(), settings_coordinator(api), store)

        walk = asyncio.run(go())
        assert walk["kind"] == "full"
        assert walk["reason"] == "cache-too-old"

    def test_the_periodic_re_anchor_fires_when_due(self):
        api = ring(8)
        walk, _store = self.tick(
            api, n_cached=8, old_full_walk=recent_history.REWALK_SECONDS + 1
        )
        assert walk["kind"] == "full"
        assert walk["reason"] == "periodic"

    def test_a_missing_interval_setting_re_walks(self):
        walk, _store = self.tick(ring(8), n_cached=8, interval=None)
        assert walk["kind"] == "full"
        assert walk["reason"] == "interval-unknown"


class TestChain:
    def test_the_floor_stops_before_the_overlap_not_after(self):
        # caught-up means the tick found its own newest sample in the ring;
        # everything the chain returns is strictly newer than the floor.
        api = ring(8)

        async def go():
            return await _chain(Hass(), api, floor=RING_START, max_blocks=1)

        accepted, reads, exceptions, ended, stopped = asyncio.run(go())
        assert (reads, exceptions, ended) == (2, 0, "caught-up")
        assert accepted == [(0, [])]
        assert stopped == 0

    def test_a_mid_block_floor_returns_only_the_newer_slots(self):
        api = ring(8)
        floor = RING_START - datetime.timedelta(seconds=5 * INTERVAL)

        async def go():
            return await _chain(Hass(), api, floor=floor, max_blocks=1)

        accepted, reads, _exc, ended, stopped = asyncio.run(go())
        assert (reads, ended) == (2, "caught-up")
        assert accepted[0][1] == [
            RING_START - datetime.timedelta(seconds=step * INTERVAL)
            for step in range(5)
        ]
        assert stopped == 5


class TestBridgeCollection:
    def collect(self, api, *, collecting=False):
        store = RecentHistory()
        store.collecting = collecting
        coordinator = SimpleNamespace(
            api=api,
            data={"data": {"settings": {4136: INTERVAL, 4187: 0}}},
            recent_history=store,
        )

        async def go():
            return await bridge_module.async_bridge_recent_history(Hass(), coordinator)

        return asyncio.run(go()), coordinator

    def test_a_call_that_arrives_mid_collection_joins_it(self):
        # The single-flight token: the in-flight collection's reads are the
        # ONE set on the wire; the joiner gets the cache flagged `collecting`
        # and puts nothing on the wire itself.
        api = ring(8)
        answer, coordinator = self.collect(api, collecting=True)
        assert answer["collecting"] is True
        assert api.internal_reads == []
        assert coordinator.recent_history.collecting is True

    def test_a_collection_clears_its_flag_before_it_answers(self):
        answer, coordinator = self.collect(ring(8))
        assert answer["collecting"] is False
        assert coordinator.recent_history.collecting is False
        assert len(answer["samples"]) == 8

    def test_the_summary_carries_the_settings_that_frame_the_chart(self):
        answer, _coordinator = self.collect(ring(4))
        walk = answer["walk"]
        assert walk["interval_sec"] == INTERVAL
        assert walk["log_at_nite"] is False

    def test_samples_come_back_oldest_first(self):
        answer, _ = self.collect(ring(3))
        stamps = [sample["ts"] for sample in answer["samples"]]
        assert stamps == sorted(stamps)


class TestPrune:
    def test_a_month_of_history_is_measured_from_the_newest_sample(self):
        # The Classic restarts daily and nobody can set its clock: RAM
        # retention counts sample distance, never wall-clock guesses.
        store = RecentHistory()
        old = RING_START - datetime.timedelta(days=40)
        store.upsert(RING_START, {"power_w": 1.0})
        store.upsert(old, {"power_w": 1.0})
        assert store.prune() == 1
        assert store.newest == store.oldest == RING_START

    def test_the_fresh_side_of_the_window_survives(self):
        store = RecentHistory()
        edge = RING_START - datetime.timedelta(days=30, hours=23)
        store.upsert(RING_START, {"power_w": 1.0})
        store.upsert(edge, {"power_w": 1.0})
        assert store.prune() == 0


class TestColumns:
    def build(self):
        store = RecentHistory()
        for i in range(3):
            when = RING_START - datetime.timedelta(seconds=INTERVAL * i)
            store.upsert(
                when,
                {
                    "power_w": float(525 - i),
                    "power_w_raw": 525 - i,
                    "vpv": 162.1 - i,
                    "vpv_raw": 1621 - int(i * 10),
                    "stage": 0x0303,
                },
            )
        return store

    def test_the_file_is_timestamps_plus_raw_word_columns(self):
        file = self.build().to_columns()
        assert file["v"] == recent_history.FILE_VERSION
        # Oldest first: the file is a chart, and charts read left to right.
        assert file["ts"] == [
            "2026-09-25T11:32",
            "2026-09-25T11:37",
            "2026-09-25T11:42",
        ]
        assert file["power"] == [523, 524, 525]
        assert file["stage"] == [0x0303, 0x0303, 0x0303]

    def test_a_category_a_sample_lacks_is_null_not_zero(self):
        file = self.build().to_columns()
        # vbatt was never collected for any sample: a column of nulls.
        assert file["vbatt"] == [None, None, None]

    def test_the_keep_window_is_counted_from_the_newest_sample(self):
        store = self.build()
        ancient = RING_START - datetime.timedelta(days=800)
        store.upsert(ancient, {"power_w": 0.0, "power_w_raw": 0})
        file = store.to_columns(keep_days=365)
        assert "2025-.."[:5] not in "".join(file["ts"])
        assert len(file["ts"]) == 3

    def test_the_round_trip_restores_the_walk_fields_exactly(self):
        store = self.build()
        rebuilt = RecentHistory()
        assert rebuilt.merge_columns(store.to_columns()) == 3
        assert rebuilt.samples == store.samples

    def test_the_wire_outranks_the_memory_of_the_same_moment(self):
        # A loaded file never overwrites what the ring just said about the
        # same minute; and a file with a corrupt stamp skips it, not dies.
        store = self.build()
        file = store.to_columns()
        file["ts"].append("not a time")
        rebuilt = RecentHistory()
        rebuilt.upsert(RING_START, {"power_w": 99.0})
        assert rebuilt.merge_columns(file) == 2  # RING_START kept, two added
        assert rebuilt.samples[RING_START]["power_w"] == 99.0


class TestFileEngine:
    def test_the_file_rounds_trips_through_ha_storage(self):
        store = TestColumns().build()
        hass = Hass()

        async def go():
            saved = await recent_history.async_flush_file(
                hass, "entry-1", store, keep_days=365
            )
            fresh = RecentHistory()
            added = await recent_history.async_load_file(hass, "entry-1", fresh)
            return saved, added, fresh

        saved, added, fresh = asyncio.run(go())
        assert saved == {"samples": 3, "written": True}
        assert added == 3
        assert fresh.samples == store.samples

    def test_an_empty_store_writes_no_file_at_all(self):
        hass = Hass()

        async def go():
            return await recent_history.async_flush_file(
                hass, "entry-1", RecentHistory(), keep_days=365
            )

        assert asyncio.run(go()) == {"samples": 0, "written": False}
        assert hass.stored_files == {}

    def test_the_key_is_namespaced_per_entry(self):
        key = recent_history.recent_history_store_key("entry-1")
        assert key == f"{recent_history.DOMAIN}.recent_history.entry-1"

    def test_a_missing_file_loads_zero_not_raises(self):
        hass = Hass()

        async def go():
            return await recent_history.async_load_file(
                hass, "entry-1", RecentHistory()
            )

        assert asyncio.run(go()) == 0
