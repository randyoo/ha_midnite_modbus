#!/usr/bin/env python3
"""
Simple analysis script to find sensors needing fixes.
Uses hardcoded register-to-group mapping based on registers_clean.json analysis.
"""

import re

# Hardcoded mapping based on registers_clean.json analysis
REGISTER_TO_GROUP = {
    # device_info group (registers 4103, 4106-4108, 4111-4120)
    'UNIT_ID': 'device_info',
    'MAC_ADDRESS_PART_1': 'device_info',
    'MAC_ADDRESS_PART_2': 'device_info',
    'MAC_ADDRESS_PART_3': 'device_info',
    'DEVICE_ID_LSW': 'device_info',
    'DEVICE_ID_MSW': 'device_info',
    'UNIT_NAME_0': 'device_info',
    'UNIT_NAME_1': 'device_info',
    'UNIT_NAME_2': 'device_info',
    'UNIT_NAME_3': 'device_info',
    'UNIT_SW_DATE_RO': 'device_info',
    'UNIT_SW_DATE_MONTH_DAY': 'device_info',
    
    # status group (registers 4105, 4109-4110, 4113-4114)
    'DISP_AVG_VBATT': 'status',
    'COMBO_CHARGE_STAGE': 'status',
    'PV_INPUT_CURRENT': 'status',
    'STATUSROLL': 'status',
    'INFO_FLAGS_BITS3': 'status',
    'WATTS': 'status',
    
    # temperatures group (registers 4121-4123) - need /10 formula
    'BATT_TEMPERATURE': 'temperatures',
    'FET_TEMPERATURE': 'temperatures',
    'PCB_TEMPERATURE': 'temperatures',
    
    # energy group (registers 4115-4119)
    'AMP_HOURS_DAILY': 'energy',
    'LIFETIME_KW_HOURS_1': 'energy',
    'LIFETIME_KW_HOURS_1_HIGH': 'energy',
    'LIFETIME_AMP_HOURS_1': 'energy',
    'LIFETIME_AMP_HOURS_1_HIGH': 'energy',
    
    # time_settings group (registers 4124-4127)
    'FLOAT_TIME_TODAY_SEC': 'time_settings',
    'ABSORB_TIME': 'time_settings',
    'EQUALIZE_TIME': 'time_settings',
    'RESTART_TIME_MS': 'time_settings',
    
    # diagnostics group (register 4128)
    'REASON_FOR_RESTING': 'diagnostics',
    
    # setpoints group (registers 4130-4133, 4148-4151) - need /10 formula
    'ABSORB_SETPOINT_VOLTAGE': 'setpoints',
    'FLOAT_VOLTAGE_SETPOINT': 'setpoints',
    'EQUALIZE_VOLTAGE_SETPOINT': 'setpoints',
    'BATTERY_OUTPUT_CURRENT_LIMIT': 'setpoints',
    
    # eeprom_settings group (registers 4134-4136, 4154-4157) - need /10 formula
    'ABSORB_TIME_EEPROM': 'eeprom_settings',
    'EQUALIZE_TIME_EEPROM': 'eeprom_settings',
    'EQUALIZE_INTERVAL_DAYS_EEPROM': 'eeprom_settings',
    
    # advanced_status group (registers 4137-4139)
    'HIGHEST_VINPUT_LOG': 'advanced_status',
    'JrAmpHourNET': 'advanced_status',
    'MATCH_POINT_SHADOW': 'advanced_status',
    
    # advanced_config group (registers 4140-4143, 4164-4182)
    'MPPT_MODE': 'advanced_config',
    'AUX_1_AND_2_FUNCTION': 'advanced_config',
    'VARIMAX': 'advanced_config',
    'ENABLE_FLAGS3': 'advanced_config',
    
    # aux_control group (registers 4150, 4166-4181) - need /10 formula
    'AUX1_VOLTS_LO_ABS': 'aux_control',
    'AUX1_VOLTS_HI_ABS': 'aux_control',
    'AUX1_DELAY_T_MS': 'aux_control',
    'AUX1_HOLD_T_MS': 'aux_control',
}

# Registers that need division by 10 based on formulas in registers_clean.json
REGISTERS_NEEDING_DIVISION_BY_10 = {
    'BATT_TEMPERATURE', 'FET_TEMPERATURE', 'PCB_TEMPERATURE',
    'DISP_AVG_VBATT', 'DISP_AVG_VPV', 'IBATT_DISPLAY_S', 'KW_HOURS',
    'PV_INPUT_CURRENT', 'VOC_LAST_MEASURED', 'ABSORB_SETPOINT_VOLTAGE',
    'FLOAT_VOLTAGE_SETPOINT', 'EQUALIZE_VOLTAGE_SETPOINT',
    'BATTERY_OUTPUT_CURRENT_LIMIT', 'AUX1_VOLTS_LO_ABS', 'AUX1_VOLTS_HI_ABS',
    'VBATT_OFFSET', 'VPV_OFFSET', 'VPV_TARGET_RD', 'VPV_TARGET_WR',
    'MIN_SWP_VOLTAGE_EEPROM', 'MAX_INPUT_CURRENT_EEPROMS',
}

# Registers that need division by 100 based on formulas in registers_clean.json
REGISTERS_NEEDING_DIVISION_BY_100 = {
    'LIFETIME_KW_HOURS_1', 'LIFETIME_KW_HOURS_1_HIGH',
}

def analyze_sensors():
    """Analyze sensor.py to find sensors needing fixes."""
    
    with open('custom_components/midnite/sensor.py', 'r') as f:
        content = f.read()
    
    # Find all sensor classes
    sensor_classes = re.findall(r'class (\w+Sensor)\(.*?\):', content)
    
    print(f"Analyzing {len(sensor_classes)} sensor classes...\n")
    
    sensors_needing_group_fix = []
    sensors_needing_formula_fix = []
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
            current_group = "status"
        elif '.get("temperatures")' in native_value_code:
            current_group = "temperatures"
        elif '.get("energy")' in native_value_code:
            current_group = "energy"
        elif '.get("time_settings")' in native_value_code:
            current_group = "time_settings"
        elif '.get("advanced_status")' in native_value_code:
            current_group = "advanced_status"
        elif '.get("device_info")' in native_value_code:
            current_group = "device_info"
        else:
            continue
        
        # Extract the register name
        reg_match = re.search(r'REGISTER_MAP\["(\w+)"\]', native_value_code)
        if not reg_match:
            continue
        
        reg_name = reg_match.group(1)
        
        # Check if this register is in our map
        if reg_name not in REGISTER_TO_GROUP:
            sensors_not_in_map.append({
                'name': class_name,
                'register': reg_name,
                'note': 'Register not in mapping - may need coordinator update'
            })
            continue
        
        correct_group = REGISTER_TO_GROUP[reg_name]
        
        # Check if data group is correct
        needs_group_fix = current_group != correct_group
        
        # Check formula requirements
        needs_division_by_10 = reg_name in REGISTERS_NEEDING_DIVISION_BY_10 and 'return value / 10.0' not in native_value_code
        needs_division_by_100 = reg_name in REGISTERS_NEEDING_DIVISION_BY_100 and 'return value / 100.0' not in native_value_code
        
        if needs_group_fix:
            sensors_needing_group_fix.append({
                'name': class_name,
                'register': reg_name,
                'current_group': current_group,
                'correct_group': correct_group,
                'needs_division_by_10': needs_division_by_10,
                'needs_division_by_100': needs_division_by_100
            })
        elif needs_division_by_10 or needs_division_by_100:
            sensors_needing_formula_fix.append({
                'name': class_name,
                'register': reg_name,
                'current_group': current_group,
                'needs_division_by_10': needs_division_by_10,
                'needs_division_by_100': needs_division_by_100
            })
        else:
            sensors_already_correct.append({
                'name': class_name,
                'register': reg_name,
                'group': current_group
            })
    
    # Print results
    print("=" * 70)
    print("SENSORS NEEDING DATA GROUP FIX:")
    print("=" * 70)
    for sensor in sensors_needing_group_fix:
        formula_notes = []
        if sensor['needs_division_by_10']:
            formula_notes.append("/10.0 division")
        if sensor['needs_division_by_100']:
            formula_notes.append("/100.0 division")
        
        formula_note = f" (also needs: {', '.join(formula_notes)})" if formula_notes else ""
        print(f"  {sensor['name']} - uses {sensor['register']}")
        print(f"    Current: {sensor['current_group']}, Should be: {sensor['correct_group']}{formula_note}")
        print()
    
    if sensors_needing_formula_fix:
        print("=" * 70)
        print("SENSORS NEEDING FORMULA FIX:")
        print("=" * 70)
        for sensor in sensors_needing_formula_fix:
            formula_notes = []
            if sensor['needs_division_by_10']:
                formula_notes.append("/10.0 division")
            if sensor['needs_division_by_100']:
                formula_notes.append("/100.0 division")
            
            print(f"  {sensor['name']} - uses {sensor['register']}")
            print(f"    Group: {sensor['current_group']}, Needs: {', '.join(formula_notes)}")
            print()
    
    if sensors_not_in_map:
        print("=" * 70)
        print("SENSORS WITH REGISTERS NOT IN MAPPING:")
        print("=" * 70)
        for sensor in sensors_not_in_map:
            print(f"  {sensor['name']} - uses {sensor['register']}")
            print()
    
    print("=" * 70)
    print("SUMMARY:")
    print("=" * 70)
    print(f"Sensors needing data group fix: {len(sensors_needing_group_fix)}")
    print(f"Sensors needing formula fix: {len(sensors_needing_formula_fix)}")
    print(f"Sensors already correct: {len(sensors_already_correct)}")
    print(f"Sensors with unmapped registers: {len(sensors_not_in_map)}")

if __name__ == "__main__":
    analyze_sensors()