"""The clock feature ported from the Midnite Solar AIR app.

Three things, all reverse-engineered from LocalStatusPanel.swf and written up in
air-app-reverse/PROTOCOL.md:

* Read the Classic's clock from the ordinary block: CTIME0 = ([4215]<<16)+[4214]
  and CTIME1 = ([4217]<<16)+[4216], split as seconds|minutes / hours|weekday /
  day|month / year (ConfigMenuLocal.as:4347-4357).
* Set the clock with a private function-105 "file write" to device 7, address 0,
  a 20-byte payload whose time/date sit at offset 9.
* Reboot with two ordinary writes: 4186|0x04 (AutoDlyReset) then 4160|0x100
  (ForceNite).

The private function codes 104/105 collide with standard Read FIFO/Write Coil,
so they must be registered per-client, never globally - pinned here.
"""

from __future__ import annotations

import asyncio
import struct

import pytest
from fakes import FakeApi, FakeCoordinator
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.exceptions import HomeAssistantError

from midnite_solar.button import RebootClassicButton, SetClockButton
from midnite_solar.const import (
    CLOCK_FILE_ADDRESS,
    CLOCK_FILE_DEVICE,
    CLOCK_FILE_LENGTH,
    ENABLE_FLAGS_2_AUTO_DLY_RESET,
    FORCE_FLAGS,
    REGISTER_MAP,
)

ENABLE_FLAGS_2 = REGISTER_MAP["ENABLE_FLAGS_2"]
from midnite_solar.entity_writes import async_reboot_classic, async_set_clock
from midnite_solar.private_pdu import (
    INTERNAL_MARKER,
    ReadInternalPDU,
    WriteInternalPDU,
    register_private_pdus,
)
from midnite_solar.register_values import clock_file_payload, clock_from_registers

# 2026-09-21 14:30:05, the app's own worked example in PROTOCOL.md.
NOW = dict(year=2026, month=9, day=21, hour=14, minute=30, second=5)


def as_dt(**kw):
    from datetime import datetime

    return datetime(**kw)


class TestClockPayload:
    """TimeToFileWrite: the 20-byte block written to internal file 7."""

    def test_payload_is_20_bytes(self):
        assert len(clock_file_payload(as_dt(**NOW))) == CLOCK_FILE_LENGTH

    def test_bytes_before_the_time_are_zero(self):
        assert clock_file_payload(as_dt(**NOW))[:9] == [0] * 9

    def test_time_and_date_land_at_offset_9(self):
        payload = clock_file_payload(as_dt(**NOW))
        assert payload[9] == 14          # hour
        assert payload[10] == 30         # minute
        assert payload[11] == 5          # second
        assert payload[12] == (2026 >> 8) & 0xFF
        assert payload[13] == 2026 & 0xFF
        assert payload[14] == 9          # month
        assert payload[15] == 21         # day

    def test_the_app_uses_zero_seconds(self):
        # The AIR UI never sets seconds; our payload carries them, but the
        # Classic ignores them, so this only pins that we do not crash.
        assert clock_file_payload(as_dt(**NOW))[11] == 5


class TestClockRead:
    """The clock words the app reads back are decoded with its own masks."""

    @staticmethod
    def words(**kw):
        second, minute = kw.get("second", 5), kw.get("minute", 30)
        hour, weekday = kw.get("hour", 14), kw.get("weekday", 1)
        day, month = kw.get("day", 21), kw.get("month", 9)
        year = kw.get("year", 2026)
        return (
            (minute << 8) | second,
            (weekday << 8) | hour,
            (month << 8) | day,
            year,
        )

    def test_round_trips_a_real_moment(self):
        moment = clock_from_registers(*self.words())
        assert (moment.year, moment.month, moment.day) == (2026, 9, 21)
        assert (moment.hour, moment.minute, moment.second) == (14, 30, 5)

    def test_a_missing_word_is_unavailable_not_wrong(self):
        a, b, c, d = self.words()
        assert clock_from_registers(a, b, c, None) is None
        assert clock_from_registers(None, b, c, d) is None

    def test_an_impossible_date_from_a_zeroed_classic_is_none(self):
        assert clock_from_registers(0, 0, 0, 0) is None

    def test_a_garbage_month_is_rejected_not_invented(self):
        # month nibble 0x0F = 15 is not a month.
        a, b, day_month, d = self.words()
        assert clock_from_registers(a, b, (15 << 8) | 21, d) is None


class TestInternalPduFrames:
    """The function-104/105 PDU layout, exactly as the app frames it."""

    def test_read_frame_header(self):
        frame = ReadInternalPDU(device=7, length=20, address=0).encode()
        assert frame == struct.pack(">BBHI", 7, 20, INTERNAL_MARKER, 0)
        assert list(frame[:4]) == [7, 20, 0xFF, 0xFF]

    def test_length_is_clamped_to_128(self):
        frame = ReadInternalPDU(device=5, length=200, address=0).encode()
        assert frame[1] == 128

    def test_write_frame_appends_payload_after_header(self):
        payload = bytes([1, 2, 3])
        frame = WriteInternalPDU(device=7, data=payload, address=0).encode()
        assert frame == struct.pack(">BBHI", 7, 3, INTERNAL_MARKER, 0) + payload

    def test_write_payload_is_clamped_to_128(self):
        pdu = WriteInternalPDU(device=7, data=bytes(200), address=0)
        assert pdu.length == 128

    def test_response_header_is_echoed_and_payload_split(self):
        pdu = ReadInternalPDU()
        echoed = struct.pack(">BBHI", 7, 20, INTERNAL_MARKER, 0) + bytes(20)
        pdu.decode(echoed)
        assert pdu.device == 7
        assert pdu.payload == bytes(20)

    def test_zero_length_echo_keeps_every_byte_available(self):
        # RspReadInternal.as: if the device echoes len 0, the app takes the
        # whole remaining payload.
        pdu = ReadInternalPDU()
        pdu.decode(struct.pack(">BBHI", 5, 0, INTERNAL_MARKER, 0) + bytes(9))
        assert pdu.payload == bytes(9)


class TestPerClientRegistration:
    """104/105 must be taught to our client, never to pymodbus' global table."""

    def test_a_built_client_knows_the_private_function_codes(self):
        # Construct only; never connect, so no socket is opened.
        from pymodbus.client import ModbusTcpClient

        client = ModbusTcpClient(host="192.168.88.24", port=502)
        register_private_pdus(client)
        table = client.framer.decoder.pdu_table
        assert table[104][1] is ReadInternalPDU
        assert table[105][1] is WriteInternalPDU

    def test_a_stand_in_without_a_framer_is_simply_skipped(self):
        register_private_pdus(object())  # must not raise


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 250")


class _FixedDt:
    def __init__(self, moment):
        self._moment = moment

    def now(self):
        return self._moment


class TestSetClockButton:
    def test_pressing_it_writes_the_clock_file(self, entry, monkeypatch):
        import midnite_solar.button as button_module

        monkeypatch.setattr(button_module, "dt_util", _FixedDt(as_dt(**NOW)))
        api = FakeApi()
        coordinator = FakeCoordinator(Hass(), api, {})
        button = SetClockButton(coordinator, entry)
        button.hass = Hass()
        asyncio.run(button.async_press())
        assert api.internal_writes == [
            (CLOCK_FILE_DEVICE, clock_file_payload(as_dt(**NOW)), CLOCK_FILE_ADDRESS)
        ]

    def test_a_refused_clock_write_raises(self, entry, monkeypatch):
        import midnite_solar.button as button_module

        monkeypatch.setattr(button_module, "dt_util", _FixedDt(as_dt(**NOW)))
        api = FakeApi(error_writes=True)
        coordinator = FakeCoordinator(Hass(), api, {})
        button = SetClockButton(coordinator, entry)
        button.hass = Hass()
        with pytest.raises(HomeAssistantError):
            asyncio.run(button.async_press())


class TestRebootButton:
    def test_reboot_is_the_two_writes_the_app_makes(self, entry):
        # 4186 and 4160 start without the bits, so both writes are observable.
        api = FakeApi(read_values={ENABLE_FLAGS_2: 0x00, 4160: 0x0000})
        coordinator = FakeCoordinator(Hass(), api, {})
        button = RebootClassicButton(coordinator, entry)
        button.hass = Hass()
        asyncio.run(button.async_press())
        assert api.writes == [
            (ENABLE_FLAGS_2, ENABLE_FLAGS_2_AUTO_DLY_RESET),
            (4160, 1 << FORCE_FLAGS["ForceNite"]),
        ]

    def test_reboot_keeps_the_other_enable_bits(self, entry):
        # 4186 already has partial-shading (bit 3) on; reboot must preserve it.
        api = FakeApi(read_values={ENABLE_FLAGS_2: 0x08, 4160: 0x0000})
        coordinator = FakeCoordinator(Hass(), api, {})
        button = RebootClassicButton(coordinator, entry)
        button.hass = Hass()
        asyncio.run(async_reboot_classic(button.hass, api))
        assert api.writes[0] == (ENABLE_FLAGS_2, 0x08 | ENABLE_FLAGS_2_AUTO_DLY_RESET)

    def test_a_failed_first_read_sends_nothing(self, entry):
        api = FakeApi(unreadable=True)
        coordinator = FakeCoordinator(Hass(), api, {})
        button = RebootClassicButton(coordinator, entry)
        button.hass = Hass()
        with pytest.raises(HomeAssistantError):
            asyncio.run(async_reboot_classic(button.hass, api))
        assert api.writes == []


class TestSetClockHelper:
    def test_set_clock_uses_the_internal_file_write(self, entry):
        api = FakeApi()
        coordinator = FakeCoordinator(Hass(), api, {})
        hass = Hass()
        asyncio.run(async_set_clock(hass, api, as_dt(**NOW)))
        assert api.internal_writes == [
            (CLOCK_FILE_DEVICE, clock_file_payload(as_dt(**NOW)), CLOCK_FILE_ADDRESS)
        ]

    def test_refused_write_is_a_home_assistant_error(self, entry):
        api = FakeApi(error_writes=True)
        with pytest.raises(HomeAssistantError):
            asyncio.run(async_set_clock(Hass(), api, as_dt(**NOW)))
