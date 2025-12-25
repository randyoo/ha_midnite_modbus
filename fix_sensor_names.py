#!/usr/bin/env python3
"""
Fix sensor.py to replace literal {name} with actual register names.
"""

import re

def fix_sensor_py():
    """Fix all instances of literal {name} in sensor.py."""
    with open('custom_components/midnite/sensor.py', 'r') as f:
        content = f.read()
    
    # Find all sensor classes
    sensor_classes = re.findall(
        r'class (\w+)Sensor\(MidniteSolarSensor\):(.*?)(?=\nclass |\Z)',
        content,
        re.DOTALL
    )
    
    print(f"Found {len(sensor_classes)} sensor classes to fix")
    
    # Process each class
    fixed_content = ""
    last_pos = 0
    
    for i, (class_name, class_body) in enumerate(sensor_classes):
        # Extract the register name from the class name (remove 'Sensor' suffix)
        register_name = class_name.replace('Sensor', '')
        
        # Find where this class starts in the content
        class_pattern = f'class {class_name}Sensor'
        class_start = content.find(class_pattern, last_pos)
        if class_start == -1:
            print(f"Warning: Could not find class {class_name}")
            continue
        
        # Find the end of this class (next class or end of file)
        next_class_start = content.find('\nclass ', class_start + 1)
        if next_class_start == -1:
            class_end = len(content)
        else:
            class_end = next_class_start
        
        # Get the full class text
        full_class = content[class_start:class_end]
        
        # Replace {name} with register_name in the native_value method
        # Look for REGISTER_MAP["{name}"] and replace with REGISTER_MAP["register_name"]
        fixed_class = full_class.replace('REGISTER_MAP["{name}"]', f'REGISTER_MAP["{register_name}"]')
        
        fixed_content += content[last_pos:class_start] + fixed_class
        last_pos = class_end
    
    # Add the remaining content after the last class
    fixed_content += content[last_pos:]
    
    with open('custom_components/midnite/sensor.py', 'w') as f:
        f.write(fixed_content)
    
    print("✓ Fixed all sensor classes")

if __name__ == "__main__":
    fix_sensor_py()
