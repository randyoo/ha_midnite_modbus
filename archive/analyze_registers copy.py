#!/usr/bin/env python3
"""Analyze which registers are being read vs which sensors expect."""

import json
import re

# Load the register map
with open('archive/registers.json', 'r') as f:
    REGISTERS_DATA = json.load(f)
REGISTER_MAP = {v['address']: k for k, v in REGISTERS_DATA.items()}

# Manually define REGISTER_GROUPS from coordinator.py
REGISTER_GROUPS = {
    "device_info": [
        4103,  # UNIT_ID
        4111,  # DEVICE_ID_LSW
        4112,  # DEVICE_ID_MSW
        4115,  # UNIT_NAME_0
        4116,  # UNIT_NAME_1
        4117,  # UNIT_NAME_2
        4118,  # UNIT_NAME_3
        4106,  # MAC_ADDRESS_PART_1
        4107,  # MAC_ADDRESS_PART_2
        4108,  # MAC_ADDRESS_PART_3
        4119,  # UNIT_SW_DATE_RO
        4120,  # UNIT_SW_DATE_MONTH_DAY
    ],
    "status": [
        4105,  # DISP_AVG_VBATT
        4106,  # DISP_AVG_VPV (duplicate)
        4107,  # IBATT_DISPLAY_S (duplicate)
        4108,  # WATTS
        4109,  # COMBO_CHARGE_STAGE
        4110,  # PV_INPUT_CURRENT
        4111,  # VOC_LAST_MEASURED
        4112,  # KW_HOURS
        4113,  # STATUSROLL
        4114,  # INFO_FLAGS_BITS3
    ],
    "temperatures": [
        4121,  # BATT_TEMPERATURE
        4122,  # FET_TEMPERATURE
        4123,  # PCB_TEMPERATURE
    ],
    "energy": [
        4115,  # AMP_HOURS_DAILY
        4116,  # LIFETIME_KW_HOURS_1
        4117,  # LIFETIME_KW_HOURS_1 + 1
        4118,  # LIFETIME_AMP_HOURS_1
        4119,  # LIFETIME_AMP_HOURS_1 + 1
    ],
    "time_settings": [
        4124,  # FLOAT_TIME_TODAY_SEC
        4125,  # ABSORB_TIME
        4126,  # EQUALIZE_TIME
        4127,  # RESTART_TIME_MS
    ],
    "diagnostics": [
        4128,  # REASON_FOR_RESTING
    ],
    "setpoints": [
        4130,  # ABSORB_SETPOINT_VOLTAGE
        4131,  # FLOAT_VOLTAGE_SETPOINT
        4132,  # EQUALIZE_VOLTAGE_SETPOINT
        4133,  # BATTERY_OUTPUT_CURRENT_LIMIT
    ],
    "eeprom_settings": [
        4134,  # ABSORB_TIME_EEPROM
        4135,  # EQUALIZE_TIME_EEPROM
        4136,  # EQUALIZE_INTERVAL_DAYS_EEPROM
    ],
    "advanced_status": [
        4137,  # HIGHEST_VINPUT_LOG
        4138,  # JrAmpHourNET
        4139,  # MATCH_POINT_SHADOW
        4140,  # MINUTE_LOG_INTERVAL_SEC
        4141,  # MODBUS_PORT_REGISTER
        4142,  # MPP_W_LAST
    ],
}

# Get all registers from coordinator groups
all_read_registers = set()
for group_name, registers in REGISTER_GROUPS.items():
    for reg in registers:
        if reg in REGISTER_MAP:
            all_read_registers.add(reg)

print(f"Total registers being read by coordinator: {len(all_read_registers)}")
print("\nRegisters by group:")
for group_name, registers in sorted(REGISTER_GROUPS.items()):
    group_regs = [r for r in registers if r in REGISTER_MAP]
    print(f"  {group_name}: {len(group_regs)} registers")

# Now check which sensors are defined
print("\n" + "="*60)
print("SENSOR ANALYSIS")
print("="*60)

# Read sensor.py to find all sensor classes
with open('custom_components/midnite/sensor.py', 'r') as f:
    sensor_content = f.read()

# Find all class definitions that end with "Sensor"
sensor_classes = re.findall(r'class (\w+Sensor)\(.*?\):', sensor_content)

print(f"\nTotal sensor classes defined: {len(sensor_classes)}")

# Check which registers these sensors expect
print("\nRegisters expected by sensors:")
expected_registers = set()
for class_name in sensor_classes:
    # Find the REGISTER_MAP key used in this sensor's native_value method
    match = re.search(r'class ' + re.escape(class_name) + r'\(.*?\):(.*?)@property', sensor_content, re.DOTALL)
    if match:
        content = match.group(1)
        # Look for REGISTER_MAP["..."]
        reg_match = re.search(r'REGISTER_MAP\["(\w+)"\]', content)
        if reg_match:
            reg_name = reg_match.group(1)
            # Find the address for this register name
            for addr, name in REGISTER_MAP.items():
                if name == reg_name:
                    expected_registers.add(addr)
                    break

print(f"  Sensors expect data from {len(expected_registers)} unique registers")

# Find which registers are NOT being read but sensors expect
not_read = expected_registers - all_read_registers
print(f"\nRegisters NOT being read but sensors expect: {len(not_read)}")
if not_read:
    for reg in sorted(not_read):
        print(f"  {reg} ({REGISTER_MAP.get(reg, 'unknown')})")

# Find which registers ARE being read but no sensor uses them
read_but_not_used = all_read_registers - expected_registers
print(f"\nRegisters being read but no sensor uses: {len(read_but_not_used)}")
if read_but_not_used:
    for reg in sorted(read_but_not_used):
        print(f"  {reg} ({REGISTER_MAP.get(reg, 'unknown')})")
