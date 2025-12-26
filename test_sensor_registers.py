#!/usr/bin/env python3
"""Test to verify which sensor registers are now being read."""

# Read the updated coordinator to see what's being read
import re

with open('custom_components/midnite/coordinator.py', 'r') as f:
    content = f.read()

# Extract all REGISTER_MAP references from REGISTER_GROUPS
matches = re.findall(r'REGISTER_MAP\["([^"]+)"\]', content)

read_registers = set(matches)

print("=" * 80)
print("SENSORS THAT SHOULD NOW WORK (registers being read):")
print("=" * 80)

# Sensors that should now work
working_sensors = {
    "KW_HOURS": "Energy to the battery (reset daily)",
    "STATUSROLL": "12-bit status value, updated once per second",
    "INFO_FLAGS_BITS3": "Classic system status flags (bitfield)",
    "RESTART_TIME_MS": "Time after which classic can wake up",
    "UNIT_SW_DATE_RO": "Software build date",
    "UNIT_SW_DATE_MONTH_DAY": "Software build month/day",
    "HIGHEST_VINPUT_LOG": "Highest input voltage seen (eeprom)",
    "JrAmpHourNET": "Whizbang jr. net amp-hours",
    "MATCH_POINT_SHADOW": "Current wind power curve step (1-16)",
}

for reg_name, description in working_sensors.items():
    status = "✓ READING" if reg_name in read_registers else "✗ NOT READING"
    print(f"{reg_name:30} - {description:50} [{status}]")

print("\n" + "=" * 80)
print("SENSORS STILL SHOWING 'UNKNOWN' (not in basic/advanced groups):")
print("=" * 80)

# Sensors that are still not being read (debug category or not needed)
unknown_sensors = {
    "RESERVED_4105": "Unimplemented - avoid writing",
}

for reg_name, description in unknown_sensors.items():
    status = "✓ READING" if reg_name in read_registers else "✗ NOT READING (Debug category)"
    print(f"{reg_name:30} - {description:50} [{status}]")

print("\n" + "=" * 80)
print("SENSORS ALREADY WORKING (were already being read):")
print("=" * 80)

# Sensors that were already working
already_working = {
    "DISP_AVG_VBATT": "Average battery voltage",
    "DISP_AVG_VPV": "Average PV input voltage",
    "IBATT_DISPLAY_S": "Average battery current",
    "WATTS": "Average power to the battery",
    "PV_INPUT_CURRENT": "Average PV input current",
    "VOC_LAST_MEASURED": "Last measured open-circuit voltage",
}

for reg_name, description in already_working.items():
    status = "✓ READING" if reg_name in read_registers else "✗ NOT READING"
    print(f"{reg_name:30} - {description:50} [{status}]")
