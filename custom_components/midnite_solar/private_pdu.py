"""The Classic's two private "internal file" Modbus functions.

The Midnite Solar AIR app sets the Classic's clock (and reads its daily
datalogger) through two non-standard function codes on the SAME plain Modbus
TCP port - not through any special registers. The frame, everything after the
unit byte, is

    request : [func][device u8][len u8 clamped to 128][0xFFFF u16][address u32 BE][data...]
    response: [func][device u8][len u8][0xFFFF u16][address u32 BE][data...]

decoded from the decompiled app in air-app-reverse/PROTOCOL.md (citing
modbus/CmdReadInternal.as, CmdWriteInternal.as, RspReadInternal.as there). The
0xFFFF field is a constant marker the app writes blindly and reads without
checking; when a response echoes a length of 0 the app takes every remaining
byte, and this decode does the same.

Function codes 104 and 105 are standard Modbus "Read FIFO Queue" and "Write
Coil", so these classes must be registered on THIS client's own framer decoder
(instance level), never on pymodbus' class-level table - a global registration
would take Write Coil decoding away from every other integration in the
process.
"""

from __future__ import annotations

import struct

from pymodbus.pdu import ModbusPDU

# The app always writes 0xFFFF to the marker field (CmdReadInternal.as:19) and
# reads it back unvalidated (RspReadInternal.as:22).
INTERNAL_MARKER = 0xFFFF
# The Classic clamps the length byte to 128 (CmdReadInternal.as:11-15,
# CmdWriteInternal.as:13-16).
INTERNAL_MAX_LENGTH = 128


class ReadInternalPDU(ModbusPDU):
    """Function 104: read one of the Classic's internal files."""

    function_code = 104

    def __init__(self, device: int = 0, length: int = 0, address: int = 0) -> None:
        """Build a request; the decoder reuses this class for the response."""
        super().__init__(dev_id=1)
        self.device = device
        self.length = length
        self.file_address = address
        self.payload = b""

    def encode(self) -> bytes:
        """Encode the request frame after the unit byte."""
        return struct.pack(
            ">BBHI",
            self.device,
            min(self.length, INTERNAL_MAX_LENGTH),
            INTERNAL_MARKER,
            self.file_address,
        )

    def decode(self, data: bytes) -> None:
        """Decode the echoed header and take the payload bytes."""
        if len(data) >= 8:
            self.device = data[0]
            echoed = data[1]
            self.payload = data[8:]
            if echoed:
                self.payload = self.payload[:echoed]


class WriteInternalPDU(ModbusPDU):
    """Function 105: write one of the Classic's internal files (the clock)."""

    function_code = 105

    def __init__(self, device: int = 0, data: bytes = b"", address: int = 0) -> None:
        """Build a request; the decoder reuses this class for the response."""
        super().__init__(dev_id=1)
        self.device = device
        self.data = bytes(data)[:INTERNAL_MAX_LENGTH]
        self.length = len(self.data)
        self.file_address = address
        self.payload = b""

    def encode(self) -> bytes:
        """Encode the request frame after the unit byte, payload included."""
        return (
            struct.pack(
                ">BBHI",
                self.device,
                self.length,
                INTERNAL_MARKER,
                self.file_address,
            )
            + self.data
        )

    def decode(self, data: bytes) -> None:
        """Decode the echoed header; a write response carries no payload."""
        if len(data) >= 8:
            self.device = data[0]
            echoed = data[1]
            self.payload = data[8:]
            if echoed:
                self.payload = self.payload[:echoed]


def register_private_pdus(client) -> None:
    """Teach one client's decoder these two function codes, nothing global.

    A stand-in client without a framer (the hardware-free suite's recorder)
    simply skips it, which is also what keeps the registration client-scoped.
    """
    decoder = getattr(getattr(client, "framer", None), "decoder", None)
    if decoder is not None:
        decoder.register(ReadInternalPDU)
        decoder.register(WriteInternalPDU)
