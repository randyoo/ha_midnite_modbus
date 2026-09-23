"""The Classic's own daily datalogger: internal file device 5, function 104.

The AIR app's history charts read this from the Classic itself (not from its
local log files - PROTOCOL.md section 9 keeps those apart). One private read
of 64 bytes returns 32 consecutive days for one category as little-endian
u16, newest day first: "day n of the read = LE u16 at byte offset 62 - 2n"
(`DataMenu.as:1194,1204`).

The decode lives here, pure, so the byte-order and divisor quirks are unit
tested without a device; only `async_sweep` touches the hub, and it does so
one paced read at a time (see the retry arithmetic pinned in
tests/test_datalogger.py).

Bench verdict (2026-09-22, FINDINGS section 41; date layout CORRECTED
2026-09-23 by FINDINGS section 46): the cat-3 date packs MONTH in 4 low bits,
DAY in the next 5, year-2000 above - the app's parseTsLow NAMES the fields
backwards but its printed m/d/yyyy is right, and the anchor dates
2026-09-21/22/23 prove the layout. decode_date follows that. And no slot in the whole
384-slot window ever answered with a Modbus exception: unwritten slots come
back as stale RAM whose date fails to decode, so "exception means absent"
still stands as the rule (the app decoded such a response as data and showed
garbage - `LocalStatusPanel.as:919-921` never checks isException; skipping
instead of guessing is the one app behaviour this module refuses to copy).
The cat-6 time still shows no seconds.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any, Dict, Optional

from .const import BRIDGE_API_VERSION
from .coordinator import OP_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# The datalogger is internal file "device" 5 (PROTOCOL.md section 6).
LOGGER_FILE_DEVICE = 5
# One read answers 64 bytes = 32 consecutive days of one category.
DAYS_PER_READ = 32
READ_BYTES = 64
# Day slots live in a 1024-slot window: "(catIndex & 0x3F) << 10 |
# (daySlot & 0x3FF)" (DataMenu.as:513). The app sweeps 379, but the bench
# (2026-09-22) answers slot 383 too and the answered range ends exactly at
# twelve full blocks: the ring is 384 slots, and that is what a refresh
# reads.
SWEEP_DAY_SLOTS = 384
SWEEP_BLOCKS = -(-SWEEP_DAY_SLOTS // DAYS_PER_READ)  # 12 blocks

# The app's per-block read order (`DataMenu.as:256-313`): date first, then
# the rest. Category 1 (Ah per day) is the app's orphan - defined but never
# read there - so it is not swept either.
SWEEP_CATEGORIES = (3, 6, 0, 2, 4, 5, 7, 8)

# Retry budget, the same arithmetic the coordinator pins: one attempt
# against a half-dead port can burn the socket timeout (3 s) plus a full
# reconnect (2 s delay + a 3 s connect) - 2 attempts are ~16.8 s, under the
# OP_TIMEOUT that would otherwise reset the client under the sweep. A chunk
# larger than ONE read would sit on the hub lock past that cap, so the sweep
# asks for exactly one read per executor job.
SWEEP_READ_RETRIES = 2
assert SWEEP_READ_RETRIES * (3.0 + 2.0 + 3.0) < OP_TIMEOUT

# Yield the loop (and with it the hub lock) between reads so the coordinator
# poll can interleave with a sweep on this single-connection device instead
# of timing out against it.
READ_GAP_SECONDS = 0.05

# Category divisors and field names, from the app's table
# (`DataMenu.as:256-313,443-510`): "kWh per day /10", "high power /1000
# (W->kW)", "high temp /10", "Vpv /10", "Vbatt /10". The raw register value
# is kept beside the scaled one; nothing here guesses a unit the app did not
# document.
SCALED_CATEGORIES = {
    0: ("kwh", 10.0),
    4: ("high_power_kw", 1000.0),
    5: ("high_temp_c", 10.0),
    7: ("vpv", 10.0),
    8: ("vbatt", 10.0),
}


def day_address(category: int, day_slot: int) -> int:
    """The file address one category read starts at.

    Map (DataMenu.as:513): "(catIndex & 0x3F) << 10 | (daySlot & 0x3FF)".
    """
    return ((category & 0x3F) << 10) | (day_slot & 0x3FF)


def unpack_newest_first(payload: bytes) -> Optional[list]:
    """Split one 64-byte read into its 32 days, newest day first.

    Day n is the little-endian u16 at byte offset 62 - 2n
    (`DataMenu.as:1194,1204`). A short payload is not data, it is a torn or
    empty response, so it yields None rather than a shifted calendar.
    """
    if len(payload) != READ_BYTES:
        return None
    return [
        payload[READ_BYTES - 2 - 2 * n] | (payload[READ_BYTES - 1 - 2 * n] << 8)
        for n in range(DAYS_PER_READ)
    ]


def decode_date(raw: int) -> Optional[datetime.date]:
    """The category-3 date: MONTH in 4 bits, DAY in the next 5, year above.

    The packing is month(4)@0 day(5)@4 year(7)@9 - the AIR app's own bit
    ops (`parseTsLow`, `DataMenu.as:1402-1408`) with its variable NAMES
    corrected: it extracts the low nibble as "day" and the next five as
    "month", then prints them as day + "/" + month + "/" + year, so its
    DISPLAY reads m/d/yyyy and comes out right (0x3559 prints
    "9/21/2026" = September 21 2026). §41 trusted those variable names and
    reversed the field widths; the reversal rested on dates that FINDINGS
    45/46 later proved mis-decodes of this same layout.

    The ground-truth anchor, first real dates this ring ever had: the raws
    0x3559/0x3569/0x3579 decode to 2026-09-21/22/23 - the three days the
    bench KNOWS this Classic ran (the §41 sweep, the §44 clock experiment,
    the 2026-09-23 deploy day, energies to match) - and the y2k entries
    become consecutive daily runs (2000-07-02..25, 2000-08-02..25) with
    solar-plausible 5-8 kWh, not §41's "pairs twice a month". Even §41's
    five "undated RAM fossils" 0x1F8..0x1B8 are real: 2000-08-27..31.
    A day over 31 cannot exist in 5 bits; Feb 30 and an empty slot
    (month nibble 0) decode to None: an absent day, not a lie.
    """
    month = raw & 0x0F
    day = (raw >> 4) & 0x1F
    year = 2000 + ((raw >> 9) & 0x7F)
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def decode_time_of_day(raw: int) -> Dict[str, int]:
    """The category-6 time: minute low 6 bits, hour next 5, no seconds
    (`DataMenu.as:1242-1247`)."""
    return {"minute": raw & 0x3F, "hour": (raw >> 6) & 0x1F}


def decode_float_time(seconds: int) -> Dict[str, int]:
    """The category-2 float time, seconds -> hours and minutes
    (`DataMenu.as` "hh = v/3600; mm = v%3600/60")."""
    return {"hours": seconds // 3600, "minutes": (seconds % 3600) // 60}


class Datalogger:
    """Swept day records, keyed by date, plus the last sweep's summary."""

    def __init__(self) -> None:
        """Start empty; a sweep fills it."""
        # day slot -> {"date": date, category fields...}
        self.slots: Dict[int, Dict[str, Any]] = {}
        self.sweep: Optional[Dict[str, Any]] = None
        # True from the instant a sweep starts until it lands (the sweep
        # itself is the only writer). It is the single-flight token AND the
        # API's "chart loading" answer: while set, GET /datalogger says
        # `sweeping` so a watching client waits honestly instead of
        # painting an empty cache, and a second caller JOINS the running
        # sweep instead of stampeding a second one onto this
        # single-connection device.
        self.sweeping = False

    def merge_read(self, block: int, category: int, payload: bytes) -> bool:
        """Fold one category's 32-day read into the store.

        Returns False when the payload was not 64 bytes (nothing merged);
        individual undecodable days are simply not stamped.
        """
        values = unpack_newest_first(payload)
        if values is None:
            return False
        first_slot = block * DAYS_PER_READ
        for offset, raw in enumerate(values):
            slot = first_slot + offset
            record = self.slots.setdefault(slot, {})
            if category == 3:
                date = decode_date(raw)
                if date is not None:
                    record["date"] = date
            elif category == 2:
                record["float_seconds"] = raw
                record.update(decode_float_time(raw))
            elif category == 6:
                record.update(decode_time_of_day(raw))
            else:
                field, divisor = SCALED_CATEGORIES[category]
                record[field] = raw / divisor
                record[f"{field}_raw"] = raw
        return True

    def as_dict(self) -> Dict[str, Any]:
        """The API view: dated days, newest first, plus the sweep summary.

        Keyed by DATE, not slot: the slot a day sits in is the Classic's
        business, and a (bench-open) firmware that ever stored one day in two
        slots would otherwise answer the client with that day twice.
        """
        by_date: Dict[str, Dict[str, Any]] = {}
        for record in self.slots.values():
            date = record.get("date")
            if date is None:
                continue
            day = by_date.setdefault(date.isoformat(), {})
            day.update({k: v for k, v in record.items() if k != "date"})
        days = [{"date": iso, **fields} for iso, fields in by_date.items()]
        days.sort(key=lambda day: day["date"], reverse=True)
        return {
            "api_version": BRIDGE_API_VERSION,
            "days": days,
            "sweep": self.sweep,
            "sweeping": self.sweeping,
        }


async def async_sweep(hass: Any, api: Any, store: Datalogger) -> Dict[str, Any]:
    """Read the whole datalogger: one 64-byte read per block and category.

    Every read is its own executor job with a small gap: the hub lock is one
    read at a time, so the coordinator's poll can interleave on this
    single-connection device, and no single job can sit on the lock past the
    coordinator's OP_TIMEOUT (SWEEP_READ_RETRIES pins that). Reads that
    answer with a Modbus exception are counted and skipped - the days are
    reported as absent, never as zeros.
    """
    reads = 0
    exceptions = 0
    for block in range(SWEEP_BLOCKS):
        for category in SWEEP_CATEGORIES:
            address = day_address(category, block * DAYS_PER_READ)
            result = await hass.async_add_executor_job(
                api.read_internal,
                LOGGER_FILE_DEVICE,
                READ_BYTES,
                address,
                SWEEP_READ_RETRIES,
            )
            reads += 1
            if result is None or result.isError():
                exceptions += 1
            elif not store.merge_read(block, category, getattr(result, "payload", b"")):
                exceptions += 1
            await asyncio.sleep(READ_GAP_SECONDS)
    store.sweep = {
        "reads": reads,
        "exceptions": exceptions,
        "blocks": SWEEP_BLOCKS,
        "read_slots": SWEEP_DAY_SLOTS,
    }
    return store.as_dict()
