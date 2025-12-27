#!/usr/bin/env python3
"""
Script to fix remaining formula issues in sensor.py
"""

import re

def fix_sensor_formula(filename: str, sensor_name: str, register_name: str):
    """Fix a specific sensor's formula."""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Find the sensor class and its native_value method
    pattern = rf'class {sensor_name}\(MidniteSolarSensor\):(.*?)@property\s+def native_value\(self\):.*?return value(?!\s*\/\s*10\.0)'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        # Replace return value with return value / 10.0
        new_content = content.replace(
            f'return value\n                return None',
            'return value / 10.0\n                return None'
        )
        
        with open(filename, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Fixed {sensor_name}")
    else:
        print(f"❌ Could not find {sensor_name}")

if __name__ == '__main__':
    sensors_to_fix = [
        ('VBATT_REG_SET_P_TEMP_COMPSensor', 'VBATT_REG_SET_P_TEMP_COMP'),
        ('OUTPUT_VBATT_RAWSensor', 'OUTPUT_VBATT_RAW'),
        ('INPUT_VPV_RAWSensor', 'INPUT_VPV_RAW'),
        ('VPV_TARGET_RD_TMPSensor', 'VPV_TARGET_RD_TMP'),
    ]
    
    for sensor_name, reg_name in sensors_to_fix:
        fix_sensor_formula('custom_components/midnite/sensor.py', sensor_name, reg_name)
