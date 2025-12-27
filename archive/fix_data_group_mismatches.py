#!/usr/bin/env python3
"""
Fix sensors that are looking in the wrong data group.
"""

import re

def fix_sensor_data_group(filename: str, sensor_name: str, correct_group: str):
    """Fix a sensor to look in the correct data group."""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Find the sensor class and its native_value method
    pattern = rf'class {sensor_name}\(MidniteSolarSensor\):(.*?)@property\s+def native_value'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        cls_content = match.group(0)
        
        # Find what data group it's currently using
        groups = ['device_info', 'status', 'temperatures', 'energy',
                  'time_settings', 'diagnostics', 'setpoints',
                  'eeprom_settings', 'advanced_status', 'advanced_config',
                  'aux_control', 'voltage_offsets', 'temp_comp']
        
        current_group = None
        for group in groups:
            if f'.get("{group}")' in cls_content or f'.get("\"{group}\")' in cls_content:
                current_group = group
                break
        
        if current_group and current_group != correct_group:
            # Replace the data group
            old_pattern = f'{current_group}'
            new_content = content.replace(f'data["data"].get("{current_group}")', f'data["data"].get("{correct_group}")')
            
            with open(filename, 'w') as f:
                f.write(new_content)
            
            print(f"✅ Fixed {sensor_name}: {current_group} → {correct_group}")
        else:
            print(f"❌ No change needed for {sensor_name} (already in {correct_group})")
    else:
        print(f"⚠️  Could not find {sensor_name}")

if __name__ == '__main__':
    # Sensors that should be in aux_control but are looking elsewhere
    sensors_to_fix = [
        ('AUX1_VOLTS_HI_PV_ABSSensor', 'aux_control'),
        ('AUX2_A2D_D2ASensor', 'aux_control'),
        ('AUX2_VOLTS_HI_PV_ABSSensor', 'aux_control'),
    ]
    
    for sensor_name, correct_group in sensors_to_fix:
        fix_sensor_data_group('custom_components/midnite/sensor.py', sensor_name, correct_group)
