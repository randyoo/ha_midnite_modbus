"""Tests for the pure register conversions in register_values.py.

Run with: python -m pytest tests
No Home Assistant install and no Midnite Classic are required.
"""

from __future__ import annotations

import os
import sys

import pytest

COMPONENT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "custom_components",
    "midnite_solar",
)
sys.path.insert(0, COMPONENT)

from register_values import (  # noqa: E402
    TemperatureFilter,
    byte_of,
    combine32,
    force_flag_write,
    format_ipv4,
    format_mac_from_registers,
    pack_byte_pair,
    scaled_register,
    scaled_value,
    signed16,
)


class TestScaling:
    """Register map: scaled quantities are tenths, e.g. "([4149] /10) Volts"."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (576, 57.6),  # Absorb set point 57.6 V
            (0, 0.0),
            (1, 0.1),
            (65535, -0.1),  # -1 in two's complement
            (64536, -100.0),  # -1000 tenths = -100.0
        ],
    )
    def test_scaled_value_is_signed_tenths(self, raw, expected):
        assert scaled_value(raw) == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("value", "raw"),
        [
            (57.6, 576),
            (14.5, 145),
            (0.0, 0),
            (12.0, 120),
        ],
    )
    def test_scaled_register_rounds_tenths(self, value, raw):
        assert scaled_register(value) == raw

    def test_register_conversion_rounds_not_truncates(self):
        """The docstring promises rounding; only a halfway value proves it.

        57.6 * 10 happens to land on 576.0, so int() and round() agree there and a
        truncating mutation survives. 28.35 * 10 is 283.5: truncating writes 283,
        rounding writes 284. That is where the difference is visible.
        """
        assert scaled_register(28.35) == 284
        assert int(28.35 * 10) == 283, "truncation really does go low - the test means something"
        # Plain tenths still land exactly.
        assert scaled_register(57.6) == 576
        assert scaled_register(28.3) == 283
        assert scaled_register(48.0) == 480

    @pytest.mark.parametrize(("raw", "expected"), [(0, 0), (32767, 32767), (32768, -32768), (65535, -1)])
    def test_signed16(self, raw, expected):
        assert signed16(raw) == expected


class TestWordOrder:
    """Register map spells 32-bit values "([hi] << 16) + [lo]"."""

    def test_low_address_is_the_low_word(self):
        # Lifetime kW-hours: (([4127] << 16) + [4126])
        assert combine32(low=0x0001, high=0x0002) == 0x00020001

    def test_byte_of_matches_packed_wind_table(self):
        # 4301 = "WindPowerTableV(stp 1) << 8) + WindPowerTableV(stp 0)"
        register = 0x0A14  # stp0 = 0x14 (20 V), stp1 = 0x0A (10 V)
        assert byte_of(register, 0) == 20
        assert byte_of(register, 1) == 10

    def test_pack_byte_pair_leaves_the_other_step_alone(self):
        assert pack_byte_pair(0x0A14, 0, 0x1E) == 0x0A1E
        assert pack_byte_pair(0x0A14, 1, 0x0B) == 0x0B14

    @pytest.mark.parametrize("index", [-1, 2])
    def test_pack_byte_pair_rejects_bad_index(self, index):
        with pytest.raises(ValueError):
            pack_byte_pair(0x0A14, index, 0x01)

    def test_pack_byte_pair_rejects_out_of_range_byte(self):
        with pytest.raises(ValueError):
            pack_byte_pair(0x0A14, 0, 256)


class TestForceFlagWord:
    """Table 4160-1: "can write to low or hi 16 bits independently if wanted"."""

    def test_low_word_flag_goes_to_4160(self):
        assert force_flag_write(0x00000004) == (4160, 0x0004)

    def test_high_word_flag_goes_to_4161(self):
        # ForceResetFaultsF is 0x00800000, which cannot fit in one register.
        assert force_flag_write(0x00800000) == (4161, 0x0080)

    def test_top_of_low_word_still_4160(self):
        assert force_flag_write(0x0000FFFF) == (4160, 0xFFFF)

    def test_rejects_non_32bit(self):
        with pytest.raises(ValueError):
            force_flag_write(0)
        with pytest.raises(ValueError):
            force_flag_write(1 << 32)


class TestMacAddress:
    """Map: "[4108]MSB:[4108]LSB:[4107]MSB:[4107]LSB:[4106]MSB:[4106]LSB"."""

    def test_the_bench_mac_decodes_high_register_first(self):
        """The WIFI175 that prints 60:1D:0F:00:CC:DD (192.168.88.24, 2026-09)."""
        assert format_mac_from_registers(0xCCDD, 0x0F00, 0x601D) == "60:1d:0f:00:cc:dd"

    def test_the_answer_is_canonical_for_unique_id_comparison(self):
        """Home Assistant compares unique ids as strings: lower case, colons."""
        mac = format_mac_from_registers(0xABCD, 0xEF01, 0x2345)
        assert mac == "23:45:ef:01:ab:cd"


class TestIpv4:
    """A real Classic stores the address reversed from how the map prints it.

    Bench-confirmed on 192.168.88.24: 20482=0xA8C0, 20483=0x1858. The lower-numbered
    register holds the first two octets and each register reads low byte first; the
    map's literal "[20483]MSB . ... . [20482]LSB" order renders the same unit as a
    reversed 24.88.168.192.
    """

    def test_lower_register_supplies_the_first_octet(self):
        # 192.168.1.2 -> lower register (20482) = 0xA8C0, higher (20483) = 0x0201
        assert format_ipv4(low=0xA8C0, high=0x0201) == "192.168.1.2"

    def test_the_bench_observed_address(self):
        # The exact registers read back from 192.168.88.24.
        assert format_ipv4(low=0xA8C0, high=0x1858) == "192.168.88.24"

    def test_dhcp_style_address(self):
        assert format_ipv4(low=0xA8C0, high=0x161C) == "192.168.28.22"


class TestTemperatureFilter:
    """Noise rejection that can never lock out a sensor."""

    def test_stable_readings_pass(self):
        filt = TemperatureFilter()
        assert [filt.apply(v) for v in (25.0, 25.2, 24.9, 25.1)] == [25.0, 25.2, 24.9, 25.1]

    def test_absurd_reading_is_dropped(self):
        filt = TemperatureFilter()
        for value in (25.0, 25.1, 25.0):
            filt.apply(value)
        assert filt.apply(2500.0) is None
        assert filt.rejected == 1

    def test_out_of_range_is_dropped_even_when_warm(self):
        filt = TemperatureFilter()
        assert filt.apply(150.5) is None
        assert filt.apply(-50.5) is None
        assert filt.apply(150.0) == 150.0

    def test_short_spikes_do_not_move_the_baseline(self):
        """Three good readings and alternating spikes must keep reporting good data."""
        filt = TemperatureFilter()
        published = []
        for value in (25.0, 25.0, 25.0, 25.0, 400.0, 25.0, 400.0, 25.0):
            result = filt.apply(value)
            if result is not None:
                published.append(result)
        assert published[-1] == 25.0
        assert max(published) < 100.0

    def test_genuine_change_is_admitted_and_lockout_is_impossible(self):
        """After max_rejections the filter accepts, so bad data cannot be cached forever."""
        filt = TemperatureFilter(max_rejections=5)
        for value in (25.0, 25.0, 25.0):
            filt.apply(value)
        results = [filt.apply(60.0) for _ in range(7)]
        assert any(result == 60.0 for result in results)
        assert filt.apply(60.5) == 60.5

    def test_baseline_restarts_after_the_escape_hatch(self):
        """Once the filter admits the new level it must not fight it afterwards."""
        filt = TemperatureFilter(max_rejections=2)
        for value in (25.0, 25.1, 25.0):
            filt.apply(value)
        assert [filt.apply(48.0) for _ in range(4)] == [None, None, 48.0, 48.0]
        assert filt.apply(48.2) == 48.2
        assert filt.rejected == 0

    def test_recovery_after_the_probe_comes_back(self):
        filt = TemperatureFilter()
        for value in (25.0, 25.1, 25.0, 300.0, 300.0, 300.0, 300.0, 300.0, 300.0, 25.0):
            filt.apply(value)
        assert filt.apply(25.2) == 25.2
