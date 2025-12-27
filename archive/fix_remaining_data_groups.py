#!/usr/bin/env python3
"""
Fix remaining sensors that are looking in the wrong data group.
This focuses on the most critical ones from the user's output.
"""

import re

def fix_sensor_group(filename: str, sensor_name: str, old_group: str, new_group: str):
    """Fix a sensor to look in a different data group."""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Find the sensor class
    pattern = rf'class {sensor_name}\(MidniteSolarSensor\):(.*?)@property\s+def native_value'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        cls_content = match.group(0)
        
        # Check if it's using the old group
        if f'data["data"].get("{old_group}")' in cls_content:
            # Replace the data group reference
            new_content = content.replace(
                f'{old_group}_data = self.coordinator.data["data"].get("{old_group}")',
                f'{new_group}_data = self.coordinator.data["data"].get("{new_group}")'
            )
            
            with open(filename, 'w') as f:
                f.write(new_content)
            
            print(f"✅ Fixed {sensor_name}: {old_group} → {new_group}")
        else:
            print(f"❌ {sensor_name} not using {old_group}")
    else:
        print(f"⚠️  Could not find {sensor_name}")

if __name__ == '__main__':
    # Sensors that need to be moved from status to advanced_status
    advanced_status_sensors = [
        ('BATTERY_TEMP_PASSED_EEPROMSensor', 'status', 'advanced_status'),
        ('CTI_ME0Sensor', 'status', 'advanced_status'),
        ('CTI_ME1Sensor', 'status', 'advanced_status'),
        ('CTI_ME2Sensor', 'status', 'advanced_status'),
        ('DAY_LOG_COMB_CAT_INDEXSensor', 'status', 'advanced_status'),
    ]
    
    # Sensors that need to be moved from status to network_config
    network_config_sensors = [
        ('DNS_1_LSB_1Sensor', 'status', 'network_config'),
        ('DNS_1_LSB_2Sensor', 'status', 'network_config'),
        ('DNS_2_LSB_1Sensor', 'status', 'network_config'),
        ('DNS_2_LSB_2Sensor', 'status', 'network_config'),
        ('GATEWAY_ADDRESS_LSB_1Sensor', 'status', 'network_config'),
        ('GATEWAY_ADDRESS_LSB_2Sensor', 'status', 'network_config'),
        ('IP_ADDRESS_LSB_1Sensor', 'status', 'network_config'),
        ('IP_ADDRESS_LSB_2Sensor', 'status', 'network_config'),
        ('SUBNET_MASK_LSB_1Sensor', 'status', 'network_config'),
        ('SUBNET_MASK_LSB_2Sensor', 'status', 'network_config'),
    ]
    
    print("Fixing advanced_status sensors...")
    for sensor_name, old_group, new_group in advanced_status_sensors:
        fix_sensor_group('custom_components/midnite/sensor.py', sensor_name, old_group, new_group)
    
    print("\nFixing network_config sensors...")
    for sensor_name, old_group, new_group in network_config_sensors:
        fix_sensor_group('custom_components/midnite/sensor.py', sensor_name, old_group, new_group)
