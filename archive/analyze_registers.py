#!/usr/bin/env python3
import json
from collections import defaultdict
import re

# Load registers.json (skip comments)
with open('registers.json', 'r') as f:
    content = f.read()
    # Remove /* */ style comments
    content = re.sub(r'\/\*.*?\*\/', '', content, flags=re.DOTALL)
    registers1 = json.loads(content)

# Load registers2.json (skip comments)  
with open('registers2.json', 'r') as f:
    content = f.read()
    # Remove /* */ style comments
    content = re.sub(r'\/\*.*?\*\/', '', content, flags=re.DOTALL)
    registers2 = json.loads(content)

# Combine all registers
all_registers = {}
for reg in registers1['registers']:
    addr = str(reg['address'])
    all_registers[addr] = reg

for reg in registers2['registers']:
    addr = str(reg['address'])
    if addr not in all_registers:
        all_registers[addr] = reg

# Existing sensors from const.py
EXISTING_REGISTERS = {
    '4101': 'UNIT_ID',
    '4106': 'MAC_ADDRESS_PART_1', 
    '4107': 'MAC_ADDRESS_PART_2',
    '4108': 'MAC_ADDRESS_PART_3',
    '4111': 'DEVICE_ID_LSW',
    '4112': 'DEVICE_ID_MSW',
    '4115': 'DISP_AVG_VBATT',
    '4116': 'DISP_AVG_VPV',
    '4117': 'IBATT_DISPLAY_S',
    '4118': 'KW_HOURS',
    '4119': 'WATTS',
    '4120': 'COMBO_CHARGE_STAGE',
    '4121': 'PV_INPUT_CURRENT',
    '4122': 'VOC_LAST_MEASURED',
    '4125': 'AMP_HOURS_DAILY',
    '4126': 'LIFETIME_KW_HOURS_1',
    '4128': 'LIFETIME_AMP_HOURS_1',
    '4132': 'BATT_TEMPERATURE',
    '4133': 'FET_TEMPERATURE',
    '4134': 'PCB_TEMPERATURE',
    '4138': 'FLOAT_TIME_TODAY_SEC',
    '4139': 'ABSORB_TIME',
    '4142': 'REASON_FOR_RESET',
    '4143': 'EQUALIZE_TIME',
    '4148': 'BATTERY_OUTPUT_CURRENT_LIMIT',
    '4149': 'ABSORB_SETPOINT_VOLTAGE',
    '4150': 'FLOAT_VOLTAGE_SETPOINT',
    '4151': 'EQUALIZE_VOLTAGE_SETPOINT',
    '4275': 'REASON_FOR_RESTING',
}

# Categorize missing sensors by type
missing_sensors = defaultdict(list)

for addr, reg in all_registers.items():
    if addr not in EXISTING_REGISTERS and reg.get('access') == 'R':
        name = reg['name']
        unit = reg.get('unit', '')
        description = reg.get('description', '')
        
        # Categorize by sensor type
        if any(keyword in description.lower() for keyword in ['voltage', 'current', 'power', 'energy', 'temperature', 'time', 'duration']):
            if 'temp' in name.lower():
                missing_sensors['Temperature'].append((addr, name, unit))
            elif 'voltage' in name.lower() or 'vbatt' in name.lower() or 'vpv' in name.lower():
                missing_sensors['Voltage'].append((addr, name, unit))
            elif 'current' in name.lower() or 'amp' in name.lower():
                missing_sensors['Current'].append((addr, name, unit))
            elif 'power' in name.lower() or 'watt' in name.lower():
                missing_sensors['Power'].append((addr, name, unit))
            elif 'energy' in name.lower() or 'hour' in name.lower():
                missing_sensors['Energy'].append((addr, name, unit))
            elif 'time' in name.lower() or 'duration' in name.lower() or 'interval' in name.lower():
                missing_sensors['Time/Duration'].append((addr, name, unit))
            else:
                missing_sensors['Other'].append((addr, name, unit))

# Print summary
print("=" * 80)
print("MISSING SENSOR ENTITIES - Categorized by Type")
print("=" * 80)

for category, sensors in sorted(missing_sensors.items()):
    print(f"\n{category} Sensors:")
    print("-" * 40)
    for addr, name, unit in sensors[:15]:  # Show first 15 per category
        print(f"  {addr}: {name} ({unit})")
    if len(sensors) > 15:
        print(f"  ... and {len(sensors) - 15} more")

print(f"\n\nTotal missing sensors: {sum(len(s) for s in missing_sensors.values())}")
print(f"Categories found: {len(missing_sensors)}")
