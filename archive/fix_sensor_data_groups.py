#!/usr/bin/env python3
"""
Fix sensor data groups - update sensors to look in the correct coordinator data group.

This script will:
1. Identify which register group each sensor's register belongs to
2. Update the sensor's native_value method to query the correct data group
3. Handle special cases like DNS registers that aren't being read yet
"""

import re

# Map of register addresses to their coordinator groups
REGISTER_TO_GROUP = {
    # device_info group (4103, 4106-4108, 4111-4112, 4115-4118, 4119-4120)
    4103: "device_info",
    4106: "device_info",  # MAC_ADDRESS_PART_1
    4107: "device_info",  # MAC_ADDRESS_PART_2
    4108: "device_info",  # MAC_ADDRESS_PART_3
    4111: "device_info",  # DEVICE_ID_LSW
    4112: "device_info",  # DEVICE_ID_MSW
    4115: "device_info",  # UNIT_NAME_0
    4116: "device_info",  # UNIT_NAME_1
    4117: "device_info",  # UNIT_NAME_2
    4118: "device_info",  # UNIT_NAME_3
    4119: "device_info",  # UNIT_SW_DATE_RO
    4120: "device_info",  # UNIT_SW_DATE_MONTH_DAY
    
    # status group (4105, 4108-4114)
    4105: "status",      # DISP_AVG_VBATT
    4108: "status",      # WATTS (also in device_info for MAC_ADDRESS_PART_3 - conflict!)
    4109: "status",      # COMBO_CHARGE_STAGE
    4110: "status",      # PV_INPUT_CURRENT
    4111: "status",      # VOC_LAST_MEASURED (also device_info for DEVICE_ID_LSW - conflict!)
    4112: "status",      # KW_HOURS (also device_info for DEVICE_ID_MSW - conflict!)
    4113: "status",      # STATUSROLL
    4114: "status",      # INFO_FLAGS_BITS3
    
    # temperatures group (4121-4123)
    4121: "temperatures", # BATT_TEMPERATURE
    4122: "temperatures", # FET_TEMPERATURE
    4123: "temperatures", # PCB_TEMPERATURE
    
    # energy group (4115-4119)
    4115: "energy",      # AMP_HOURS_DAILY (also device_info for UNIT_NAME_0 - conflict!)
    4116: "energy",      # LIFETIME_KW_HOURS_1 (also device_info for UNIT_NAME_1 - conflict!)
    4117: "energy",      # LIFETIME_KW_HOURS_1_HIGH (also device_info for UNIT_NAME_2 - conflict!)
    4118: "energy",      # LIFETIME_AMP_HOURS_1 (also device_info for UNIT_NAME_3 - conflict!)
    4119: "energy",      # LIFETIME_AMP_HOURS_1_HIGH (also device_info for UNIT_SW_DATE_RO - conflict!)
    
    # time_settings group (4124-4127)
    4124: "time_settings", # FLOAT_TIME_TODAY_SEC
    4125: "time_settings", # ABSORB_TIME
    4126: "time_settings", # EQUALIZE_TIME
    4127: "time_settings", # RESTART_TIME_MS
    
    # diagnostics group (4128)
    4128: "diagnostics",  # REASON_FOR_RESTING
    
    # setpoints group (4130-4133)
    4130: "setpoints",   # ABSORB_SETPOINT_VOLTAGE
    4131: "setpoints",   # FLOAT_VOLTAGE_SETPOINT
    4132: "setpoints",   # EQUALIZE_VOLTAGE_SETPOINT
    4133: "setpoints",   # BATTERY_OUTPUT_CURRENT_LIMIT
    
    # eeprom_settings group (4134-4136)
    4134: "eeprom_settings", # ABSORB_TIME_EEPROM
    4135: "eeprom_settings", # EQUALIZE_TIME_EEPROM
    4136: "eeprom_settings", # EQUALIZE_INTERVAL_DAYS_EEPROM
    
    # advanced_status group (4137-4142)
    4137: "advanced_status", # HIGHEST_VINPUT_LOG
    4138: "advanced_status", # JrAmpHourNET
    4139: "advanced_status", # MATCH_POINT_SHADOW
    4140: "advanced_status", # MINUTE_LOG_INTERVAL_SEC
    4141: "advanced_status", # MODBUS_PORT_REGISTER
    4142: "advanced_status", # MPP_W_LAST
}

def fix_sensor_file():
    """Read sensor.py, fix data group references, and write back."""
    
    with open('custom_components/midnite/sensor.py', 'r') as f:
        content = f.read()
    
    # Find all sensor classes
    sensor_classes = re.findall(r'class (\w+Sensor)\(.*?\):', content)
    
    print(f"Found {len(sensor_classes)} sensor classes")
    
    # Process each sensor class
    for class_name in sensor_classes:
        # Find the sensor's __init__ and native_value methods
        pattern = rf'class {re.escape(class_name)}\(.*?\):.*?(?=class \w+Sensor\(|$)'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            continue
        
        sensor_code = match.group(0)
        
        # Extract the register name used in this sensor
        reg_match = re.search(r'REGISTER_MAP\["(\w+)"\]', sensor_code)
        if not reg_match:
            continue
        
        reg_name = reg_match.group(1)
        print(f"  Processing {class_name} (uses {reg_name})")
        
        # For now, let's just identify which sensors need fixing
        # We'll do the actual fix manually to be safe
    
    print("\nAnalysis complete. Sensors that need fixing will be identified above.")

if __name__ == "__main__":
    fix_sensor_file()
