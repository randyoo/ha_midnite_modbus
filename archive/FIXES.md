# Charge Stage Sensor Fixes

## Problem
The "Charge Stage" sensor was constantly showing "rest" even when the raw register value changed to 1027 or 1028, indicating different charge states.

## Root Cause
1. **Incorrect CHARGE_STAGES mapping**: The dictionary had wrong key-value pairs (sequential keys 0-7 instead of actual device values)
2. **Wrong bit extraction**: The code was trying to extract the charge stage from bits 12-15, but according to the specification, it should be extracted from the high byte (bits 8-15)

## Solution

### 1. Fixed CHARGE_STAGES mapping in `const.py`
Updated the dictionary to match the actual device values from registers2.json:
```python
CHARGE_STAGES = {
    0: "Resting",      # 0x00
    3: "Absorb",       # 0x03
    4: "BulkMPPT",     # 0x04
    5: "Float",        # 0x05
    6: "FloatMppt",    # 0x06
    7: "Equalize",     # 0x07
    10: "HyperVoc",    # 0x0A
    18: "EqMppt"       # 0x12
}
```

### 2. Added INTERNAL_STATES mapping in `const.py`
Added support for decoding the internal state from the low byte:
```python
INTERNAL_STATES = {
    0: "Resting",
    1: "Waking/Starting (state 1)",
    2: "Waking/Starting (state 2)",
    3: "MPPT / Regulating Voltage (state 3)",
    4: "MPPT / Regulating Voltage (state 4)",
    6: "MPPT / Regulating Voltage (state 6)"
}
```

### 3. Fixed ChargeStageSensor in `sensor.py`
- Changed bit extraction from `(raw_value >> 12) & 0x0F` to `(raw_value >> 8) & 0xFF`
- This correctly extracts the high byte (MSB) for charge stage
- Changed logging from INFO to DEBUG level

### 4. Added InternalStateSensor in `sensor.py`
- New sensor that decodes the internal state from the low byte (LSB)
- Uses `(raw_value & 0xFF)` to extract internal state value
- Provides additional visibility into the device's operational state

## Verification

Tested with example values:
- Raw value: 1027 (0x403) → Charge Stage: BulkMPPT, Internal State: MPPT / Regulating Voltage (state 3)
- Raw value: 1028 (0x404) → Charge Stage: BulkMPPT, Internal State: MPPT / Regulating Voltage (state 4)

All test cases pass successfully.

## Technical Details

According to the Midnite Solar specification (registers2.json):
- Register 4120: COMBO_CHARGE_STAGE
- Format: 16-bit register with two bytes
- High byte (MSB) = Charge Stage: `(value >> 8) & 0xFF`
- Low byte (LSB) = Internal State: `value & 0xFF`

This matches the metadata note in registers2.json:
```
"endianness": "16‑bit registers, bits numbered LSB‑0 (little‑endian). Use [addr]MSB and [addr]LSB as shown in the spec."
"byte_order_note": "[addr]MSB = (value >> 8) & 0xFF ; [addr]LSB = value & 0xFF"
```
