"""The Classic's onboard recent-history log: internal file device 6, function 104.

The register map's own end section (1.0 File Transfer) names it:
`modbus_file_minutes_log - Read Minutely Logs from EEprom`. The rows on 4256
hinted at it and Table 1.3.2-1 lists the categories: 0 power, 1 VPV, 2 Vbatt,
3 TimeStampLow, 4 TimeStampHigh, 5 charge stage, 6 output current, 7 kWh.
One read answers 64 bytes = 32 consecutive samples for one category as
little-endian u16, newest sample first, at byte offset `62 - 2n` - the bench
(FINDINGS section 52) walked the whole address window and found device 6
shaped EXACTLY like the day-log device 5, so this module REUSES
`datalogger`'s byte-level decode rather than forking a second copy of a
proven contract.

What the bench nailed down about the content (all of it pinned by tests):

- The address window spans 1024 sample slots, but retention on the bench unit
  is ~384 slots: reads PAST the depth do not fail, they SILENTLY ECHO the
  newest window (no Modbus exception ever appears). The only honest filter is
  the data: timestamps must strictly descend, one sample per slot; a repeat or
  a forward jump is the aliasing tail, and everything from there is dropped.
  Charting an unfiltered window would paint the same afternoon twenty times.
- Every value category stores the raw display-register value (bench-verified
  sample-by-sample against the live registers); the table's "/10" describes
  the display formula, exactly like the day categories, so scaled fields and
  `_raw` fields ship side by side.
- Timestamps carry no seconds (the date comes at midnight, hour+minute per
  sample), and the log keeps running while the Classic Rests when the
  LogAtNiteEn bit (0x4000 in 4187) is set - with it clear, only daylight
  hours log and the same ring stretches over more days. The collector here
  must assume NOTHING about the spacing: it is timestamp-driven throughout.
- The Classic auto-restarts daily on this bench (FINDINGS section 52
  addendum): the live connection blanks each morning and this store's full
  walk reruns on its own. A tick that finds the ring head older than the
  cache (or a gap it cannot bridge with a few head blocks) re-walks; the
  overlap a normal tick re-reads merges by timestamp.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from homeassistant.helpers.storage import Store

from .const import BRIDGE_API_VERSION, DOMAIN, REGISTER_MAP
from .coordinator import OP_TIMEOUT
from .datalogger import (
    READ_BYTES,
    READ_GAP_SECONDS,
    SWEEP_READ_RETRIES,
    decode_date,
    decode_time_of_day,
    unpack_newest_first,
)

_LOGGER = logging.getLogger(__name__)

# The recent-history log is internal file "device" 6 (map section 1.3.2).
RECENT_FILE_DEVICE = 6
# One read answers 64 bytes = 32 consecutive samples of one category.
SAMPLES_PER_READ = 32
# The address window spans 1024 sample slots ("data point before now"). The
# bench unit held ~384 and ECHOED past that; the walk reads at most all 32
# blocks and the timestamp chain decides where the truth actually ends.
WALK_BLOCKS = 1024 // SAMPLES_PER_READ
# The background collector's rhythm: a beat reads one timestamp pair (two
# reads) and merges whatever new samples it reveals. The classic's own ring
# shifts one sample per MinuteLogIntervalSec, so a two-minute beat is five
# times the growth rate at the 300 s default.
TICK_SECONDS = 120.0
# Re-anchor the whole window periodically whatever the ticks say: a full walk
# is a few dozen reads and the ticks are cheap insurance between them.
REWALK_SECONDS = 21600.0
# The first pass waits out the entry's startup polls (the day-log sweeper's
# warm-up, same reasoning).
WALK_WARM_SECONDS = 5.0
# A tick may bridge a gap this many head blocks wide before it prefers a full
# re-walk: five blocks covers an hour of missed collection at the 300 s
# default, and anything wider than that is a restart, not a gap.
TICK_MAX_BLOCKS = 5
# One extra slot of look-on when sizing a tick's blocks, for the partial
# minute the newest sample is always sitting in.
HEAD_MARGIN_SLOTS = 1
# "LogAtNiteEn" in Enable Flags 1 (Table 4187-1): logging continues while the
# Classic rests; the walk summary carries the bit so a client can tell why
# the night is there or not there.
LOG_AT_NITE_BIT = 0x4000

TS_LOW_CAT = 3
TS_HIGH_CAT = 4
STAGE_CAT = 5
# Category -> (field, divisor). The bench read every stored word against the
# live register of the same units: they are raw mirrors, and the /10 here is
# the map's own display formula, not a storage scale. The charge stage stays
# the raw 4120 code (its stage set is Table 4120-1, FINDINGS section 50).
VALUE_FIELDS: dict[int, tuple[str, float]] = {
    # 4119 is INTEGER Watts on its own map row ("[4119] Watts"), and the
    # stored cat-0 word is its raw mirror - so cat 0 needs no /10. (The
    # FINDINGS 52 note called it tenths; the mirror itself was right, the
    # unit label was the mistake. The user's live eyes caught it.)
    0: ("power_w", 1.0),
    1: ("vpv", 10.0),
    2: ("vbatt", 10.0),
    6: ("output_amps", 10.0),
    7: ("kwh", 10.0),
}
VALUE_CATS = (0, 1, 2, STAGE_CAT, 6, 7)

# Retry budget, the day-log sweep's own arithmetic (one bounded read per
# executor job so the live poll interleaves on the single connection and no
# job sits on the hub lock past OP_TIMEOUT).
WALK_READ_RETRIES = SWEEP_READ_RETRIES
assert WALK_READ_RETRIES * (3.0 + 2.0 + 3.0) < OP_TIMEOUT

MINUTE_LOG_INTERVAL = REGISTER_MAP["MINUTE_LOG_INTERVAL_SEC"]
ENABLE_FLAGS_1 = REGISTER_MAP["ENABLE_FLAGS_1"]

# RAM keeps a month of samples, measured against the store's OWN newest
# sample: the Classic restarts itself at dawn and its clock is the one this
# bench cannot set, so "older than" is ring-relative, never wall-clock.
RAM_RETENTION_SECONDS = 31 * 86400.0

# The file: Home Assistant's own .storage, one JSON per entry. The shape is
# columnar raw integers (the u16 words the Classic actually sent, the same
# the FINDINGS 52 walk reads) beside an ISO timestamp list - a few hundred
# bytes a day instead of a dictionary per sample, because this file rewrites
# whole. 12 months of 5-minute samples is a few megabytes, and the companion
# app is its only reader: nothing here is a Home Assistant entity.
# Version 2: the cat-0 scale correction (4119 is whole watts). Home
# Assistant's Store refuses to load a file whose version it does not know,
# so bumping this DISCARDS any file written under the old (wrong) scale
# and the next flush writes the honest one.
FILE_VERSION = 2
FLUSH_SECONDS = 3600.0
# (column name, sample field, scale) - columns store the RAW word; the
# scaled field is rebuilt on load exactly as the walk stores it.
COLUMNS: tuple[tuple[str, str, float], ...] = (
    # Same scale as VALUE_FIELDS above (they must agree or the file
    # rebuilds powers 10x off): 4119 is whole watts.
    ("power", "power_w", 1.0),
    ("vpv", "vpv", 10.0),
    ("vbatt", "vbatt", 10.0),
    ("amps", "output_amps", 10.0),
    ("kwh", "kwh", 10.0),
    ("stage", "stage", 1.0),
)


def sample_dt(record: dict[str, Any]) -> datetime | None:
    """The sample's classic-local datetime, or None if undecodable.

    The date comes from the TimeStampLow word (month 4 bits, day 5,
    year-2000 above - the FINDINGS section 46 layout) and the time from
    TimeStampHigh (hour, minute, no seconds). An impossible date (Feb 30,
    the empty-slot month nibble) is None: an absent sample, not a lie.
    """
    date = record.get("date")
    if date is None or "hour" not in record or "minute" not in record:
        return None
    try:
        return datetime(
            date.year, date.month, date.day, record["hour"], record["minute"]
        )
    except ValueError:
        return None


class RecentHistory:
    """Collected samples, keyed by their classic-local timestamp.

    Keyed by TIME, never by slot: a sample slot means "so many data points
    before now" and the ring shifts every interval, so a slot-keyed cache
    would go stale on its own. The same timestamp arriving twice (a tick's
    overlap re-reads the head on purpose) merges into one sample; the ring's
    echoes of an out-of-depth read never get in, because the walker drops
    anything its chain did not accept first.
    """

    def __init__(self) -> None:
        """Start empty; walks fill it."""
        self.samples: dict[datetime, dict[str, Any]] = {}
        self.walk: dict[str, Any] | None = None
        # True from the instant a walk starts until it lands: the single-
        # flight token AND the app's "history gathering in progress" signal.
        # A client that arrives mid-walk gets the cache flagged `collecting`
        # and waits honestly instead of stampeding a second walk onto the
        # one connection.
        self.collecting = False
        # A full walk has landed: until then every beat escalates to one.
        self.anchored = False
        self.last_full_walk = 0.0

    @property
    def newest(self) -> datetime | None:
        """The moment of the freshest collected sample."""
        return max(self.samples) if self.samples else None

    @property
    def oldest(self) -> datetime | None:
        """The moment of the oldest collected sample."""
        return min(self.samples) if self.samples else None

    def upsert(self, when: datetime, fields: dict[str, Any]) -> None:
        """Merge one sample's fields in, keeping any fields this read lacked."""
        self.samples.setdefault(when, {}).update(fields)

    def prune(self, window_seconds: float = RAM_RETENTION_SECONDS) -> int:
        """Drop samples older than the window, newest sample as the clock.

        The collector runs for months and the file may hand back a year;
        RAM's share is a month, counted against the store's own newest
        sample so a Classic whose clock drifted (it restarts daily and
        nobody can set its clock) prunes by SAMPLE distance, not by
        wall-clock guesses.
        """
        newest = self.newest
        if newest is None:
            return 0
        cutoff = newest - timedelta(seconds=window_seconds)
        stale = [when for when in self.samples if when < cutoff]
        for when in stale:
            del self.samples[when]
        return len(stale)

    def to_columns(self, keep_days: float | None = None) -> dict[str, Any]:
        """The file shape: ISO timestamps plus one raw-word column each.

        Values are the words the Classic stored (FINDINGS 52: raw mirrors of
        the live registers), so the file survives any later change of mind
        about display scaling, and a missing category is null, not a zero.
        """
        times = sorted(self.samples)
        if keep_days and times:
            cutoff = times[-1] - timedelta(days=keep_days)
            times = [when for when in times if when >= cutoff]
        columns: dict[str, list[Any]] = {name: [] for name, _, _ in COLUMNS}
        for when in times:
            sample = self.samples[when]
            for name, field, scale in COLUMNS:
                if field == "stage":
                    columns[name].append(sample.get(field))
                    continue
                raw = sample.get(f"{field}_raw")
                if raw is None and sample.get(field) is not None:
                    raw = round(sample[field] * scale)
                columns[name].append(raw)
        return {
            "v": FILE_VERSION,
            "interval_sec": (self.walk or {}).get("interval_sec"),
            "ts": [when.isoformat(timespec="minutes") for when in times],
            **columns,
        }

    def merge_columns(self, file: dict[str, Any]) -> int:
        """Fold a loaded file in; returns the number of samples added.

        Timestamps the store already holds keep what the wire said - the
        file is memory of past walks, and a fresh read of the same moment
        outranks the memory of it.
        """
        stamps = file.get("ts")
        if not isinstance(stamps, list):
            return 0
        added = 0
        for index, stamp in enumerate(stamps):
            try:
                when = datetime.fromisoformat(stamp)
            except (ValueError, TypeError):
                continue
            if when in self.samples:
                continue
            fields: dict[str, Any] = {}
            for name, field, scale in COLUMNS:
                values = file.get(name)
                raw = (
                    values[index]
                    if isinstance(values, list) and index < len(values)
                    else None
                )
                if raw is None:
                    continue
                if field == "stage":
                    # The stage column IS the 4120 code; there is no
                    # scaled twin of it. (Whole-watt power is NOT
                    # stage-like: it keeps its raw mirror field.)
                    fields[field] = int(raw)
                else:
                    fields[f"{field}_raw"] = int(raw)
                    fields[field] = int(raw) / scale
            if fields:
                self.upsert(when, fields)
                added += 1
        return added

    def as_dict(self) -> dict[str, Any]:
        """The API view: samples oldest first (a chart reads left to right)."""
        times = sorted(self.samples)
        return {
            "api_version": BRIDGE_API_VERSION,
            "collecting": self.collecting,
            "oldest": times[0].isoformat(timespec="minutes") if times else None,
            "newest": times[-1].isoformat(timespec="minutes") if times else None,
            "walk": self.walk,
            "samples": [
                {"ts": when.isoformat(timespec="minutes"), **self.samples[when]}
                for when in times
            ],
        }


def recent_address(category: int, slot: int) -> int:
    """The file address one category read starts at.

    The map's formula, section 1.3.2: "(category & 0x3F) << 10 |
    (sample & 0x3FF)".
    """
    return ((category & 0x3F) << 10) | (slot & 0x3FF)


async def _read_words(
    hass: Any, api: Any, category: int, block: int
) -> list[int] | None:
    """One paced function-104 read, answered as 32 words, or None.

    One read per executor job, exactly the day-log sweep's discipline: the
    hub lock goes back between reads so the live poll interleaves on this
    single-connection device, and a Modbus exception (the only answer shape
    the bench ever saw fail) counts as a failed read, never as data.
    """
    result = await hass.async_add_executor_job(
        api.read_internal,
        RECENT_FILE_DEVICE,
        READ_BYTES,
        recent_address(category, block * SAMPLES_PER_READ),
        WALK_READ_RETRIES,
    )
    await asyncio.sleep(READ_GAP_SECONDS)
    if result is None or result.isError():
        return None
    return unpack_newest_first(getattr(result, "payload", b""))


def _settings(coordinator: Any) -> tuple[int | None, bool]:
    """The walk's context: the current log interval and the LogAtNite bit."""
    data = (coordinator.data or {}).get("data", {}) if coordinator.data else {}
    settings = data.get("settings", {}) or {}
    interval = settings.get(MINUTE_LOG_INTERVAL)
    flags = settings.get(ENABLE_FLAGS_1)
    return interval, bool(flags & LOG_AT_NITE_BIT) if flags is not None else False


def _word_dt(low_word: int, high_word: int) -> datetime | None:
    """One sample's classic-local moment from its two timestamp words.

    An undecodable date (month nibble 0, Feb 30, the stale-RAM patterns the
    day-log bench learned to distrust) is None: the chain filter treats a
    slot that cannot say when it happened as untrustworthy, whatever else it
    contains.
    """
    date = decode_date(low_word)
    if date is None:
        return None
    return sample_dt({"date": date} | decode_time_of_day(high_word))


async def _chain(
    hass: Any,
    api: Any,
    *,
    floor: datetime | None,
    max_blocks: int,
) -> tuple[list[tuple[int, list[datetime]]], int, int, str, int]:
    """Read timestamp pairs newest-first and return the accepted blocks.

    The ring's own words for its content, filtered the only way the bench
    found honest: times must STRICTLY descend, one sample per slot. The walk
    ends with "caught-up" (the floor sample was reached - what a tick wanted
    all along), "echo" (a repeat or a jump back in time - the out-of-depth
    aliasing, which on this firmware answers with NO exception at all),
    "fail-read" (a Modbus exception did come back) or "end-of-window".
    A slot that cannot state its date lands in "echo" too: a ring that just
    powered up answers with words that decode to nothing, and nothing
    undecodable earns a place on a chart.

    Returns (accepted blocks newest-first, reads, exceptions, how it ended,
    the slot where it stopped).
    """
    accepted: list[tuple[int, list[datetime]]] = []
    reads = 0
    exceptions = 0
    prev: datetime | None = None
    for block in range(max_blocks):
        low = await _read_words(hass, api, TS_LOW_CAT, block)
        high = await _read_words(hass, api, TS_HIGH_CAT, block)
        reads += 2
        if low is None or high is None:
            exceptions += 1
            return accepted, reads, exceptions, "fail-read", block * SAMPLES_PER_READ
        times: list[datetime] = []
        stopped_at: int | None = None
        for slot in range(SAMPLES_PER_READ):
            when = _word_dt(low[slot], high[slot])
            if when is None or (prev is not None and when >= prev):
                stopped_at = block * SAMPLES_PER_READ + slot
                break
            if floor is not None and when <= floor:
                stopped_at = block * SAMPLES_PER_READ + slot
                accepted.append((block, times))
                return accepted, reads, exceptions, "caught-up", stopped_at
            times.append(when)
            prev = when
        if times:
            accepted.append((block, times))
        if stopped_at is not None:
            return accepted, reads, exceptions, "echo", stopped_at
    return accepted, reads, exceptions, "end-of-window", max_blocks * SAMPLES_PER_READ


async def _merge_values(
    hass: Any,
    api: Any,
    store: RecentHistory,
    accepted: list[tuple[int, list[datetime]]],
) -> tuple[int, int, int]:
    """Read the value categories for the accepted slots only.

    Values land on their TIMESTAMPS, never on slot numbers: the slot a
    sample sits in is the ring's private, sliding business (FINDINGS section
    52), and the only key that survives between reads is when the sample
    happened. A read that fails loses that category for those samples and
    counts an exception; the rest of the merge stands.
    """
    reads = 0
    exceptions = 0
    value_blocks = 0
    for block, times in accepted:
        if not times:
            # A block the chain caught up inside holds nothing new; paying
            # six reads for its echo-free but merged-already slots is the
            # boring beat's waste, not its design.
            continue
        for category in VALUE_CATS:
            words = await _read_words(hass, api, category, block)
            reads += 1
            if words is None:
                exceptions += 1
                continue
            value_blocks += 1
            for offset, when in enumerate(times):
                raw = words[offset]
                if category == STAGE_CAT:
                    store.upsert(when, {"stage": raw})
                else:
                    field, divisor = VALUE_FIELDS[category]
                    store.upsert(when, {field: raw / divisor, f"{field}_raw": raw})
    return reads, exceptions, value_blocks


async def async_full_walk(
    hass: Any,
    api: Any,
    store: RecentHistory,
    *,
    reason: str | None,
    interval_sec: int | None,
    log_at_nite: bool,
) -> dict[str, Any]:
    """Walk the window newest-first and merge everything the chain accepts.

    The walk reads at most the full 1024-slot address window and the chain
    decides where truth ends; the bench unit echoes its newest window from
    slot ~384 on, with exceptions never, so the walk stops at the first
    repeat rather than charting the same afternoon twenty times over.
    Accepted samples merge into the store by timestamp: a walk replaces what
    it re-reads and keeps whatever older history earlier walks collected
    while the ring still held it - the bridge, not the Classic, is the
    historian.
    """
    accepted, reads, exceptions, ended, stopped_at = await _chain(
        hass, api, floor=None, max_blocks=WALK_BLOCKS
    )
    value_reads, value_exceptions, value_blocks = await _merge_values(
        hass, api, store, accepted
    )
    store.prune()
    store.anchored = True
    store.last_full_walk = asyncio.get_running_loop().time()
    store.walk = {
        "kind": "full",
        "reason": reason,
        "reads": reads + value_reads,
        "exceptions": exceptions + value_exceptions,
        "timestamp_blocks": len(accepted),
        "value_blocks": value_blocks,
        "slots_collected": sum(len(times) for _, times in accepted),
        "chain_ended": ended,
        "tail_rejected_at": stopped_at if ended == "echo" else None,
        "interval_sec": interval_sec,
        "log_at_nite": log_at_nite,
        "walked_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    return store.walk


async def async_tick(
    hass: Any, coordinator: Any, store: RecentHistory
) -> dict[str, Any]:
    """Collect what the ring gained since the store's newest sample.

    A beat reads ONE timestamp pair and merges the samples newer than the
    cache head - two reads in the common case, none of the wire wasted. It
    escalates to a full walk when the store has nothing to build on (cold),
    when the interval setting is missing, when a periodic re-anchor is due,
    and when the head itself echoes (the ring rewrote under the cache: a
    boot or a roll, always re-walk after). A cache so old the ring gap
    outgrows the whole window re-walks too, so the summary re-baselines on
    the device's truth instead of quietly charting Swiss cheese.
    """
    interval, log_at_nite = _settings(coordinator)
    api = coordinator.api
    loop_time = asyncio.get_running_loop().time()
    if not store.anchored:
        reason = "cold"
    elif not interval or interval < 1:
        reason = "interval-unknown"
    elif store.last_full_walk and loop_time - store.last_full_walk > REWALK_SECONDS:
        reason = "periodic"
    else:
        reason = None
    if reason is not None:
        return await async_full_walk(
            hass,
            api,
            store,
            reason=reason,
            interval_sec=interval,
            log_at_nite=log_at_nite,
        )
    accepted, reads, exceptions, ended, _stopped_at = await _chain(
        hass, api, floor=store.newest, max_blocks=TICK_MAX_BLOCKS
    )
    if ended == "echo":
        return await async_full_walk(
            hass,
            api,
            store,
            reason="head-echoed",
            interval_sec=interval,
            log_at_nite=log_at_nite,
        )
    # The too-old question must be asked BEFORE the merge: the first
    # accepted time is the ring head, and merging first would compare the
    # ring head against itself. A cache this far behind the ring cannot be
    # bridged by head blocks at all - the middle of the story has already
    # rolled out of the device - so the whole window re-walks and the
    # summary re-baselines on the device's truth instead of Swiss cheese.
    new_samples = sum(len(times) for _, times in accepted)
    if new_samples and interval and store.newest is not None:
        gap = (accepted[0][1][0] - store.newest).total_seconds()
        if gap > WALK_BLOCKS * SAMPLES_PER_READ * interval:
            return await async_full_walk(
                hass,
                api,
                store,
                reason="cache-too-old",
                interval_sec=interval,
                log_at_nite=log_at_nite,
            )
    value_reads, value_exceptions, value_blocks = await _merge_values(
        hass, api, store, accepted
    )
    store.prune()
    store.walk = {
        "kind": "tick",
        "reason": None,
        "reads": reads + value_reads,
        "exceptions": exceptions + value_exceptions,
        "new_samples": new_samples,
        "value_blocks": value_blocks,
        "chain_ended": ended,
        "interval_sec": interval,
        "log_at_nite": log_at_nite,
        "walked_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    return store.walk


def recent_history_store_key(entry_id: str) -> str:
    """The .storage key of this entry's collected-history file."""
    return f"{DOMAIN}.recent_history.{entry_id}"


def _store_for(hass: Any, entry_id: str) -> Store:
    """Home Assistant's own JSON store for this entry's collected history."""
    return Store(hass, FILE_VERSION, recent_history_store_key(entry_id))


async def async_load_file(hass: Any, entry_id: str, store: RecentHistory) -> int:
    """Load the collected-history file into the store; samples added.

    Runs once at collector start, before the first walk: the file hands
    back the months the Classic's ~384-slot ring forgot long ago, and the
    walk then overwrites whatever timestamps they share (the wire outranks
    the memory). A file that will not load is a warning, not a failure:
    the collector simply starts from the ring again.
    """
    data = await _store_for(hass, entry_id).async_load()
    if not isinstance(data, dict):
        return 0
    added = store.merge_columns(data)
    store.prune()
    return added


async def async_flush_file(
    hass: Any, entry_id: str, store: RecentHistory, keep_days: float
) -> dict[str, Any]:
    """Write the file: samples inside the keep window, columnar raw words.

    The caller owns the rhythm (hourly, when something new landed, once on
    teardown); this just writes what the retention window still wants. An
    empty store writes nothing - the absence of a file and a file of
    nothing should not be distinguishable to the reader.
    """
    if not store.samples:
        return {"samples": 0, "written": False}
    data = store.to_columns(keep_days)
    await _store_for(hass, entry_id).async_save(data)
    return {"samples": len(data["ts"]), "written": True}
