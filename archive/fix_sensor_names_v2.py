#!/usr/bin/env python3
"""
Fix sensor.py to replace literal {name} with actual register names - Version 2.
This version properly handles the template substitution.
"""

import re

def fix_sensor_py():
    """Fix all instances of literal {name} in sensor.py by parsing each class."""
    with open('custom_components/midnite/sensor.py', 'r') as f:
        lines = f.readlines()
    
    # Track which class we're in and what its register name is
    current_class = None
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Check if this is a sensor class definition
        class_match = re.match(r'class (\w+)Sensor\(MidniteSolarSensor\):', line)
        if class_match:
            current_class = class_match.group(1).replace('Sensor', '')
            fixed_lines.append(line)
            continue
        
        # If we're in a sensor class and find REGISTER_MAP["{name}"], replace it
        if current_class and 'REGISTER_MAP["{name}"]' in line:
            # Replace the literal {name} with the actual register name
            fixed_line = line.replace('REGISTER_MAP["{name}"]', f'REGISTER_MAP["{current_class}"]')
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    with open('custom_components/midnite/sensor.py', 'w') as f:
        f.writelines(fixed_lines)
    
    print("✓ Fixed all sensor classes")

if __name__ == "__main__":
    fix_sensor_py()
