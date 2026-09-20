"""Pure value conversions for Midnite Classic Modbus registers.

Every conversion the integration performs on the wire lives here so it can be
unit tested without a device, a Modbus client, or a Home Assistant instance.
Conversions are quoted from the Classic MODBUS register map (Rev C.4/C.5,
"MidNite Solar MODBUS Network Spec"), which is the authority for all scaling,
word order and force-flag bit positions.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Optional, Tuple

# Register holding the low 16 bits of the write-only Force Flag Bits, and the
# register holding the high 16 bits: "4160 / 4161 W Force Flag Bits
# ([4161] << 16) + [4160]".
FORCE_FLAG_BITS_LOW_REGISTER = 4160
FORCE_FLAG_BITS_HIGH_REGISTER = 4161


def scaled_value(raw: int, divisor: float = 10.0) -> float:
    """Convert a signed 16-bit register to a user-facing value.

    The Classic reports scaled quantities as tenths, and negative values as a
    two's complement 16-bit integer (register map: "([4132] /10)").
    """
    return signed16(raw) / divisor


def scaled_register(value: float, divisor: float = 10.0) -> int:
    """Convert a user-facing value to the register integer to write.

    Rounds rather than truncates, so 57.6 V becomes 576 and not 575.
    """
    return int(round(value * divisor))


def signed16(raw: int) -> int:
    """Interpret a 16-bit register as a signed value."""
    return raw - 65536 if raw > 32767 else raw


def combine32(low: int, high: int) -> int:
    """Combine two 16-bit registers into a 32-bit value.

    The register map always spells this "([hi] << 16) + [lo]", so the lower
    address carries the low word.
    """
    return (high << 16) | low


def byte_of(value: int, index: int) -> int:
    """Return byte `index` of a 16-bit register, 0 being the low byte.

    The wind power tables pack two 8-bit steps per register, e.g. 4301 is
    "WindPowerTableV(stp 1) << 8) + WindPowerTableV(stp 0)".
    """
    return (value >> (8 * index)) & 0xFF


def pack_byte_pair(current: int, index: int, byte: int) -> int:
    """Replace one byte of a packed register, leaving the other byte alone.

    Needed because a wind power table step shares its register with a
    neighbouring step: writing the whole register would clobber the neighbour.
    """
    if not 0 <= index <= 1:
        raise ValueError(f"byte index {index} out of range for a 16-bit register")
    if not 0 <= byte <= 255:
        raise ValueError(f"byte {byte} out of range for an 8-bit field")
    if index == 0:
        return (current & 0xFF00) | byte
    return (current & 0x00FF) | (byte << 8)


def force_flag_write(flag_value: int) -> Tuple[int, int]:
    """Return (register, value) needed to raise a Force Flag Bit.

    Table 4160-1 lists the flags as 32-bit values spread over registers 4160
    (low word) and 4161 (high word), and notes you "can write to low or hi 16
    bits independently if wanted". Anything at or above 0x10000 therefore has
    to go to 4161, otherwise it is truncated by the 16-bit register.
    """
    if not 0 < flag_value <= 0xFFFFFFFF:
        raise ValueError(f"force flag {flag_value:#x} is not a 32-bit value")
    if flag_value <= 0xFFFF:
        return FORCE_FLAG_BITS_LOW_REGISTER, flag_value
    return FORCE_FLAG_BITS_HIGH_REGISTER, flag_value >> 16


def format_ipv4(low: int, high: int) -> str:
    """Format an IPv4 address held in two registers.

    The register map composes the address as
    "[20483]MSB . [20483]LSB . [20482]MSB . [20482]LSB", so the higher register
    supplies the first octet and each register is read high byte first.
    """
    return ".".join(
        str(byte)
        for word in (high, low)
        for byte in ((word >> 8) & 0xFF, word & 0xFF)
    )


class TemperatureFilter:
    """Rejects implausible temperature readings without ever locking out.

    A temperature probe on the Classic is read every scan interval and a bogus
    reading (the Classic reports nonsense such as a few hundred degrees when the
    probe is unplugged or the read is torn) would otherwise be recorded as
    history. Two cheap checks remove almost all of it:

    * an absolute range check, and
    * a median check: a reading must be within ``max_deviation`` of the median
      of the last accepted readings.

    A reading that fails is rejected, but only ``max_rejections`` times in a
    row. After that the filter is wrong and the device is right, so the reading
    is accepted with a warning. An earlier attempt at statistical (z-score)
    filtering had no such escape and could refuse good data indefinitely.
    """

    def __init__(
        self,
        min_value: float = -50.0,
        max_value: float = 150.0,
        max_deviation: float = 15.0,
        max_rejections: int = 5,
        window: int = 12,
    ) -> None:
        """Initialize the filter."""

        self.min_value = min_value
        self.max_value = max_value
        self.max_deviation = max_deviation
        self.max_rejections = max_rejections
        self._accepted: Deque[float] = deque(maxlen=window)
        self._rejections = 0

    @property
    def rejected(self) -> int:
        """Return how many readings are rejected in this run."""
        return self._rejections

    def _median(self) -> float:
        """Return the median of the accepted readings."""
        ordered = sorted(self._accepted)
        mid = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / 2

    def apply(self, value: float) -> Optional[float]:
        """Return the value to publish, or None when the reading is rejected."""
        if not self.min_value <= value <= self.max_value:
            return self._reject(value, f"out of range ({value:.1f} °C)")
        if len(self._accepted) >= 3:
            median = self._median()
            if abs(value - median) > self.max_deviation:
                return self._reject(
                    value, f"deviates from median {median:.1f} °C by {abs(value - median):.1f} °C"
                )
        self._rejections = 0
        self._accepted.append(value)
        return value

    def _reject(self, value: float, reason: str) -> Optional[float]:
        """Count a rejection, or give up and restart the baseline here.

        When the escape hatch fires the filter starts a fresh baseline at this
        reading: if it kept the old readings the median would sit between the
        two clusters and every later reading would be rejected as well.
        """
        self._rejections += 1
        if self._rejections > self.max_rejections:
            self._accepted.clear()
            self._accepted.append(value)
            self._rejections = 0
            return value
        return None


def serial_from_registers(msb: int, lsb: int) -> int:
    """Combine the two read-only serial number registers.

    The map gives "28673 28674 R Classic serial number ([28673] << 16) +
    [28674]", so the lower address carries the high word here.
    """
    return (msb << 16) | lsb


def unlock_values(serial: int) -> Tuple[int, int]:
    """Return the two words to write to 20492/20493 to unlock Ethernet writes.

    The map's example: "the serial number is: 0x12345678 (hex) -> 20492 = MSB
    (Serial number) 0x1234, 20493 = LSB (Serial number) 0x5678".
    """
    return (serial >> 16) & 0xFFFF, serial & 0xFFFF


def info_flag_set(flags: int, mask: int) -> bool:
    """Return True if an Info Flag Bit from Table 4130-1 is set."""
    return bool(flags & mask)
