#!/usr/bin/env python3
"""
Find all sensors that need their data group lookups fixed.

This script identifies sensors that are looking in "status_data" but should be
looking in other coordinator data groups based on their register addresses.
"""

import re

# Map of registers to their correct coordinator groups
REGISTER_TO_GROUP = {
    # device_info group
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
    
    # status group (these are already correct)
    4105: "status",      # DISP_AVG_VBATT
    4109: "status",      # COMBO_CHARGE_STAGE
    4110: "status",      # PV_INPUT_CURRENT
    4113: "status",      # STATUSROLL
    4114: "status",      # INFO_FLAGS_BITS3
    
    # temperatures group (fixed in this commit)
    4121: "temperatures", # BATT_TEMPERATURE
    4122: "temperatures", # FET_TEMPERATURE
    4123: "temperatures", # PCB_TEMPERATURE
    
    # energy group (fixed in this commit)
    4115: "energy",      # AMP_HOURS_DAILY
    4116: "energy",      # LIFETIME_KW_HOURS_1
    4117: "energy",      # LIFETIME_KW_HOURS_1_HIGH
    4118: "energy",      # LIFETIME_AMP_HOURS_1
    4119: "energy",      # LIFETIME_AMP_HOURS_1_HIGH
    
    # time_settings group (fixed in this commit)
    4124: "time_settings", # FLOAT_TIME_TODAY_SEC
    4125: "time_settings", # ABSORB_TIME
    4126: "time_settings", # EQUALIZE_TIME
    4127: "time_settings", # RESTART_TIME_MS
    
    # diagnostics group
    4128: "diagnostics",  # REASON_FOR_RESTING
    
    # setpoints group
    4130: "setpoints",   # ABSORB_SETPOINT_VOLTAGE
    4131: "setpoints",   # FLOAT_VOLTAGE_SETPOINT
    4132: "setpoints",   # EQUALIZE_VOLTAGE_SETPOINT
    4133: "setpoints",   # BATTERY_OUTPUT_CURRENT_LIMIT
    
    # eeprom_settings group
    4134: "eeprom_settings", # ABSORB_TIME_EEPROM
    4135: "eeprom_settings", # EQUALIZE_TIME_EEPROM
    4136: "eeprom_settings", # EQUALIZE_INTERVAL_DAYS_EEPROM
    
    # advanced_status group (already correct)
    4137: "advanced_status", # HIGHEST_VINPUT_LOG
    4138: "advanced_status", # JrAmpHourNET
    4139: "advanced_status", # MATCH_POINT_SHADOW
    
    # advanced_config group
    4140: "advanced_config", # MPPT_MODE
    4141: "advanced_config", # AUX_1_AND_2_FUNCTION
    4142: "advanced_config", # VARIMAX
    4143: "advanced_config", # ENABLE_FLAGS3
    
    # aux_control group
    4150: "aux_control",   # AUX1_VOLTS_LO_ABS
    4151: "aux_control",   # AUX1_VOLTS_HI_ABS
    4152: "aux_control",   # AUX1_DELAY_T_MS
    4153: "aux_control",   # AUX1_HOLD_T_MS
}

def analyze_sensors():
    """Analyze sensor.py to find sensors needing fixes."""
    
    with open('custom_components/midnite/sensor.py', 'r') as f:
        content = f.read()
    
    # Find all sensor classes
    sensor_classes = re.findall(r'class (\w+Sensor)\(.*?\):', content)
    
    print(f"Analyzing {len(sensor_classes)} sensor classes...\n")
    
    sensors_needing_fix = []
    sensors_already_correct = []
    sensors_not_in_map = []
    
    for class_name in sensor_classes:
        # Find the sensor's native_value method
        pattern = rf'class {re.escape(class_name)}\(.*?\):.*?@property\s+def native_value\(self\) -> Optional\[float\]:(.*?)(?=\n    @property|\nclass)'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            continue
        
        native_value_code = match.group(1)
        
        # Check which data group it's using
        if '.get("status")' in native_value_code:
            data_group = "status"
        elif '.get("temperatures")' in native_value_code:
            data_group = "temperatures"
        elif '.get("energy")' in native_value_code:
            data_group = "energy"
        elif '.get("time_settings")' in native_value_code:
            data_group = "time_settings"
        elif '.get("advanced_status")' in native_value_code:
            data_group = "advanced_status"
        elif '.get("device_info")' in native_value_code:
            data_group = "device_info"
        else:
            continue
        
        # Extract the register name
        reg_match = re.search(r'REGISTER_MAP\["(\w+)"\]', native_value_code)
        if not reg_match:
            continue
        
        reg_name = reg_match.group(1)
        
        # Check if this register is in our map
        # We need to know the register address, but we only have the name
        # For now, let's just identify sensors using wrong groups
        
        if data_group == "status":
            sensors_needing_fix.append({
                'name': class_name,
                'register': reg_name,
                'current_group': 'status',
                'note': 'Likely needs fixing - check if register is in status group'
            })
        else:
            sensors_already_correct.append({
                'name': class_name,
                'register': reg_name,
                'group': data_group
            })
    
    # Print results
    print("=" * 70)
    print("SENSORS USING STATUS GROUP (may need fixing):")
    print("=" * 70)
    for sensor in sensors_needing_fix:
        print(f"  {sensor['name']} - uses {sensor['register']}")
    
    print(f"\nTotal: {len(sensors_needing_fix)} sensors using status group")
    print("\nNote: Many of these may be correct if their registers are actually in the")
    print("      'status' coordinator group. Check REGISTER_TO_GROUP mapping above.")

if __name__ == "__main__":
    analyze_sensors()
