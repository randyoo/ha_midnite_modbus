#!/usr/bin/env python3
"""
Find registers that sensors are trying to read but aren't in coordinator groups.
"""

import re

def find_sensor_registers(filename: str):
    """Find all sensor register names and their data groups."""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Find all sensor classes
    pattern = r'class (\w+Sensor)\(MidniteSolarSensor\):(.*?)@property\s+def native_value'
    matches = re.findall(pattern, content, re.DOTALL)
    
    sensors = []
    for cls_name, cls_content in matches:
        # Extract register name
        reg_pattern = r'REGISTER_MAP\["(\w+)"\]'
        reg_match = re.search(reg_pattern, cls_content)
        if reg_match:
            register_name = reg_match.group(1)
        else:
            continue
        
        # Extract data group
        groups = ['device_info', 'status', 'temperatures', 'energy',
                  'time_settings', 'diagnostics', 'setpoints',
                  'eeprom_settings', 'advanced_status', 'advanced_config',
                  'aux_control', 'voltage_offsets', 'temp_comp']
        
        data_group = None
        for group in groups:
            if f'.get("{group}")' in cls_content or f'.get("\"{group}\")' in cls_content:
                data_group = group
                break
        
        sensors.append((cls_name, register_name, data_group))
    
    return sensors

def load_coordinator_groups(filename: str):
    """Load coordinator register groups."""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Extract REGISTER_GROUPS dictionary
    pattern = r'REGISTER_GROUPS = \{(.*?)\}'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}
    
    groups_content = match.group(1)
    # This is a simplified parser - in reality you'd use ast or proper parsing
    groups = {}
    current_group = None
    for line in groups_content.split('\n'):
        if ':' in line and '[' not in line:
            # Group name line
            group_match = re.match(r'"(\w+)":', line)
            if group_match:
                current_group = group_match.group(1)
                groups[current_group] = []
        elif current_group and 'REGISTER_MAP[' in line:
            reg_match = re.search(r'REGISTER_MAP\["(\w+)"\]', line)
            if reg_match:
                groups[current_group].append(reg_match.group(1))
    
    return groups

def main():
    """Main function."""
    print("Finding missing registers...")
    
    # Find all sensors and their registers
    sensors = find_sensor_registers('custom_components/midnite/sensor.py')
    
    # Load coordinator groups
    coord_groups = load_coordinator_groups('custom_components/midnite/coordinator.py')
    
    print(f"\nFound {len(sensors)} sensors")
    print(f"Coordinator has {len(coord_groups)} register groups")
    
    # Find registers not in coordinator
    missing_registers = {}
    for cls_name, reg_name, data_group in sensors:
        if data_group and data_group in coord_groups:
            if reg_name not in coord_groups[data_group]:
                if data_group not in missing_registers:
                    missing_registers[data_group] = []
                if reg_name not in missing_registers[data_group]:
                    missing_registers[data_group].append(reg_name)
    
    print("\n" + "="*80)
    print("MISSING REGISTERS BY GROUP")
    print("="*80)
    
    for group, registers in sorted(missing_registers.items()):
        print(f"\n{group}:")
        for reg in sorted(registers):
            print(f"  - {reg}")
    
    print(f"\nTotal missing registers: {sum(len(r) for r in missing_registers.values())}")

if __name__ == '__main__':
    main()
