#!/usr/bin/env python3
"""Script to categorize Midnite Solar registers."""

import json
from typing import List, Dict, Any

# Load the registers
with open('registers_fixed.json') as f:
    data = json.load(f)

# Define categories
CATEGORIES = {
    'default': 'Basic functionality - always enabled',
    'advanced': 'Advanced features for power users',
    'debug': 'Debugging and diagnostic information'
}

# List of already implemented registers (from const.py)
implemented_registers = [
    "UNIT_ID", "UNIT_SW_DATE_RO", "UNIT_SW_DATE_MONTH_DAY", "INFO_FLAGS_BITS3",
    "MAC_ADDRESS_PART_1", "MAC_ADDRESS_PART_2", "MAC_ADDRESS_PART_3", 
    "STATUSROLL", "RESTART_TIME_MS", "DISP_AVG_VBATT", "DISP_AVG_VPV",
    "IBATT_DISPLAY_S", "KW_HOURS", "WATTS", "COMBO_CHARGE_STAGE",
    "PV_INPUT_CURRENT", "VOC_LAST_MEASURED", "HIGHEST_VINPUT_LOG",
    "AMP_HOURS_DAILY", "LIFETIME_KW_HOURS_1", "LIFETIME_AMP_HOURS_1",
    "BATT_TEMPERATURE", "FET_TEMPERATURE", "PCB_TEMPERATURE", 
    "NITE_MINUTES_NO_PWR", "FLOAT_TIME_TODAY_SEC", "ABSORB_TIME",
    "REASON_FOR_RESET", "EQUALIZE_TIME", "ABSORB_SETPOINT_VOLTAGE",
    "FLOAT_VOLTAGE_SETPOINT", "EQUALIZE_VOLTAGE_SETPOINT",
    "BATTERY_OUTPUT_CURRENT_LIMIT", "ABSORB_TIME_EEPROM", 
    "EQUALIZE_TIME_EEPROM", "EQUALIZE_INTERVAL_DAYS_EEPROM",
    "FORCE_FLAG_BITS", "UNIT_NAME_0", "UNIT_NAME_1", "UNIT_NAME_2",
    "UNIT_NAME_3", "DEVICE_ID_LSW", "DEVICE_ID_MSW", "REASON_FOR_RESTING"
]

# Categorize registers
categorized = {
    'default': [],
    'advanced': [],
    'debug': []
}

for reg in data['registers']:
    name = reg.get('name')
    
    # Skip if already implemented
    if name in implemented_registers:
        continue
    
    address = int(reg.get('address', 0))
    access = reg.get('access', '')
    description = reg.get('description', '')
    
    # Determine category based on register characteristics
    if 'RESERVED' in name or 'DEBUG' in name:
        category = 'debug'
    elif 'FLAGS' in name and 'FORCE' not in name:
        category = 'advanced'
    elif address >= 20480:  # Network settings
        category = 'advanced'
    elif 'TIME' in name or 'TEMPERATURE' in description or 'CURRENT' in description:
        category = 'advanced'
    elif 'SETPOINT' in name or 'LIMIT' in name or 'VOLTAGE' in description:
        category = 'advanced'
    elif 'WIND' in name or 'HYDRO' in name or 'SYNCH' in name:
        category = 'advanced'
    elif 'AUX' in name:
        category = 'advanced'
    elif 'EEPROM' in description and ('CALIBRATION' in description or 'FACTORY' in description):
        category = 'debug'
    else:
        # Default to advanced for most read-only registers
        category = 'advanced'
    
    categorized[category].append({
        'address': address,
        'name': name,
        'access': access,
        'description': description,
        'category': category
    })

# Print summary
print("=" * 80)
print("REGISTER CATEGORIZATION SUMMARY")
print("=" * 80)
for cat, desc in CATEGORIES.items():
    print(f"\n{cat.upper()} ({desc})")
    print(f"Count: {len(categorized[cat])}")
    if categorized[cat]:
        for reg in sorted(categorized[cat], key=lambda x: x['address']):
            print(f"  - {reg['name']} (addr: {reg['address']}, access: {reg['access']})")

# Save categorized data
with open('categorized_registers.json', 'w') as f:
    json.dump({
        'categories': CATEGORIES,
        'registers': categorized
    }, f, indent=2)

print("\n" + "=" * 80)
print("Categorization complete! Saved to categorized_registers.json")
print("=" * 80)
