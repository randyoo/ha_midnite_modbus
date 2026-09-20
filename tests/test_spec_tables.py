"""Spec-conformance tests for the tables in const.py.

Each expectation below is transcribed from the Classic MODBUS register map
("MidNite Solar MODBUS Network Spec" Rev C.4/C.5, classic_register_map_Rev-C5
December-8-2013.pdf) with the table it comes from, so a wrong constant is a
test failure rather than a wrong write to the hardware.
"""

from __future__ import annotations

import os
import sys

COMPONENT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "custom_components",
    "midnite_solar",
)
sys.path.insert(0, COMPONENT)

from const import FORCE_FLAGS, REGISTER_MAP  # noqa: E402

from register_values import force_flag_write  # noqa: E402

# Table 4160-1 "ForceFlagsBits (Write Only)". The spec lists 32-bit values; the
# reserved rows are listed so a flag cannot silently be moved onto one of them.
SPEC_FORCE_FLAGS = {
    "ForceEEpromUpdateWriteF": 0x00000004,
    "ForceEEpromInitReadF": 0x00000008,
    "ForceResetInfoFlags": 0x00000010,
    "ForceFloatF": 0x00000020,
    "ForceBulkF": 0x00000040,
    "ForceEqualizeF": 0x00000080,
    "ForceNiteF": 0x00000100,
    "ForceSweepF": 0x00000800,
    "ResetAeqCounts": 0x00010000,
    "ForceResetFaultsF": 0x00800000,
}

SPEC_RESERVED_FORCE_FLAGS = frozenset(
    [0x00000001, 0x00000002, 0x00000200, 0x00000400, 0x00001000, 0x00002000,
     0x00004000, 0x00008000, 0x00020000, 0x00040000, 0x00080000, 0x00100000,
     0x00200000, 0x00400000, 0x01000000]
)

# Spec name -> const.py key.
SPEC_NAME_TO_CONST = {
    "ForceEEpromUpdateWriteF": "ForceEEpromUpdate",
    "ForceEEpromInitReadF": "ForceEEpromInitRead",
    "ForceResetInfoFlags": "ForceResetInfoFlags",
    "ForceFloatF": "ForceFloat",
    "ForceBulkF": "ForceBulk",
    "ForceEqualizeF": "ForceEqualize",
    "ForceNiteF": "ForceNite",
    "ForceSweepF": "ForceSweep",
    "ResetAeqCounts": "ResetAeqCounts",
    "ForceResetFaultsF": "ForceResetFaults",
}


class TestForceFlags:
    """Table 4160-1."""

    def test_every_documented_flag_is_present(self):
        assert set(SPEC_NAME_TO_CONST.values()) <= set(FORCE_FLAGS)

    def test_bit_positions_match_the_spec_table(self):
        mismatches = {
            spec_name: (FORCE_FLAGS[const_key], spec_value.bit_length() - 1)
            for spec_name, const_key in SPEC_NAME_TO_CONST.items()
            for spec_value in [SPEC_FORCE_FLAGS[spec_name]]
            if FORCE_FLAGS[const_key] != spec_value.bit_length() - 1
        }
        assert not mismatches, "const key -> (code bit, spec bit)"

    def test_no_flag_sits_on_a_reserved_bit(self):
        reserved = {1 << bit for bit in range(32) if (1 << bit) in SPEC_RESERVED_FORCE_FLAGS}
        offenders = {
            name: hex(1 << bit) for name, bit in FORCE_FLAGS.items() if (1 << bit) in reserved
        }
        assert not offenders

    def test_flags_are_not_duplicated_across_names(self):
        positions = list(FORCE_FLAGS.values())
        assert len(positions) == len(set(positions))

    def test_low_word_flags_write_register_4160(self):
        for spec_name, const_key in SPEC_NAME_TO_CONST.items():
            register, _ = force_flag_write(1 << FORCE_FLAGS[const_key])
            expected = 4161 if SPEC_FORCE_FLAGS[spec_name] > 0xFFFF else 4160
            assert register == expected, spec_name

    def test_high_word_flags_survive_the_split(self):
        """A flag above 0xFFFF must keep its value once split over two registers."""
        for spec_name, const_key in SPEC_NAME_TO_CONST.items():
            spec_value = SPEC_FORCE_FLAGS[spec_name]
            register, word = force_flag_write(1 << FORCE_FLAGS[const_key])
            assert (word << (0 if register == 4160 else 16)) == spec_value, spec_name


class TestForceFlagRegisters:
    """Registers 4160/4161: "W Force Flag Bits ([4161] << 16) + [4160]"."""

    def test_both_force_registers_are_mapped(self):
        assert REGISTER_MAP["FORCE_FLAG_BITS"] == 4160
        assert REGISTER_MAP["FORCE_FLAG_BITS_HIGH"] == 4161
