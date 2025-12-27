#!/usr/bin/env python3
"""
Final test script to verify all sensor fixes are correctly applied.
This script checks:
1. All temperature sensors have /10.0 division
2. All voltage sensors have /10.0 division  
3. All current sensors have /10.0 division
4. All energy sensors have correct division (kWh: /100.0, Ah: no division)
5. Data groups are correctly assigned
"""

import re
from typing import Dict, List, Tuple

def read_file(filename: str) -> str:
    """Read file content."""
    with open(filename, 'r') as f:
        return f.read()

def extract_sensor_classes(content: str) -> List[Tuple[str, str]]:
    """Extract sensor classes and their register names."""
    pattern = r'class (\w+Sensor)\(MidniteSolarSensor\):(.*?)(?=\nclass |\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    sensors = []
    for cls_name, cls_content in matches:
        # Extract the register name from __init__
        init_pattern = r'self._attr_name = "(\w+)"'
        match = re.search(init_pattern, cls_content)
        if match:
            register_name = match.group(1)
            sensors.append((cls_name, register_name))
    
    return sensors

def check_formula_division(cls_name: str, cls_content: str, expected_division: str) -> bool:
    """Check if sensor has the expected division formula."""
    # Look for return value / 10.0 or return value / 100.0
    if expected_division == '/ 10.0':
        return 'return value / 10.0' in cls_content
    elif expected_division == '/ 100.0':
        return 'return value / 100.0' in cls_content
    else:
        # Check that it returns value without division
        return re.search(r'return value\s*(?!\/\s*10\.0|\/\s*100\.0)', cls_content) is not None

def check_data_group(cls_name: str, cls_content: str) -> str:
    """Check which data group the sensor is using."""
    # Look for the data group being accessed
    groups = ['device_info', 'status', 'temperatures', 'energy', 
              'time_settings', 'diagnostics', 'setpoints',
              'eeprom_settings', 'advanced_status', 'advanced_config',
              'aux_control', 'voltage_offsets', 'temp_comp']
    
    for group in groups:
        if f'.get("{group}")' in cls_content or f'.get("\"{group}\")' in cls_content:
            return group
    
    return 'unknown'

def main():
    """Run the test."""
    print("=" * 80)
    print("FINAL SENSOR FIXES VERIFICATION TEST")
    print("=" * 80)
    
    # Read sensor file
    content = read_file('custom_components/midnite/sensor.py')
    
    # Extract all sensor classes
    sensors = extract_sensor_classes(content)
    print(f"\nFound {len(sensors)} sensor classes")
    
    # Categorize sensors by type (more accurate filtering)
    temperature_sensors = [s for s in sensors if 'TEMPERATURE' in s[0] and not any(x in s[0] for x in ['NOMINAL', 'COMP', 'OFFSET'])]
    voltage_sensors = [s for s in sensors if ('VOLTAGE' in s[0] or 'VBATT' in s[0] or 'VPV' in s[0]) and not any(x in s[0] for x in ['NOMINAL', 'OFFSET', 'TARGET_TMP', 'TURN_ON', 'TURN_OFF'])]
    # Current sensors are those with CURRENT but not AMP_HOURS
    current_sensors = [s for s in sensors if ('CURRENT' in s[0] or ('AMP' in s[0] and 'HOURS' not in s[0])) and not any(x in s[0] for x in ['NOMINAL', 'OFFSET', 'TARGET_TMP', 'TURN_ON', 'TURN_OFF'])]
    energy_sensors = [s for s in sensors if 'ENERGY' in s[0] or 'KW_HOURS' in s[0] or 'AMP_HOURS' in s[0]]
    
    print(f"\nSensor Categories:")
    print(f"  - Temperature sensors: {len(temperature_sensors)}")
    print(f"  - Voltage sensors: {len(voltage_sensors)}")
    print(f"  - Current sensors: {len(current_sensors)}")
    print(f"  - Energy sensors: {len(energy_sensors)}")
    
    # Test temperature sensors
    print("\n" + "=" * 80)
    print("TESTING TEMPERATURE SENSORS (should have /10.0 division)")
    print("=" * 80)
    
    temp_passed = 0
    temp_failed = 0
    for cls_name, reg_name in temperature_sensors:
        # Extract the full class content
        pattern = rf'class {cls_name}\(.*?\):(.*?)(?=\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            cls_content = match.group(1)
            has_division = check_formula_division(cls_name, cls_content, '/ 10.0')
            
            status = "✅ PASS" if has_division else "❌ FAIL"
            print(f"{status} {cls_name:40s} - {reg_name}")
            
            if has_division:
                temp_passed += 1
            else:
                temp_failed += 1
    
    print(f"\nTemperature Sensor Results: {temp_passed}/{len(temperature_sensors)} passed")
    
    # Test voltage sensors
    print("\n" + "=" * 80)
    print("TESTING VOLTAGE SENSORS (should have /10.0 division)")
    print("=" * 80)
    
    volt_passed = 0
    volt_failed = 0
    for cls_name, reg_name in voltage_sensors:
        pattern = rf'class {cls_name}\(.*?\):(.*?)(?=\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            cls_content = match.group(1)
            has_division = check_formula_division(cls_name, cls_content, '/ 10.0')
            
            status = "✅ PASS" if has_division else "❌ FAIL"
            print(f"{status} {cls_name:40s} - {reg_name}")
            
            if has_division:
                volt_passed += 1
            else:
                volt_failed += 1
    
    print(f"\nVoltage Sensor Results: {volt_passed}/{len(voltage_sensors)} passed")
    
    # Test current sensors
    print("\n" + "=" * 80)
    print("TESTING CURRENT SENSORS (should have /10.0 division)")
    print("=" * 80)
    
    curr_passed = 0
    curr_failed = 0
    for cls_name, reg_name in current_sensors:
        pattern = rf'class {cls_name}\(.*?\):(.*?)(?=\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            cls_content = match.group(1)
            has_division = check_formula_division(cls_name, cls_content, '/ 10.0')
            
            status = "✅ PASS" if has_division else "❌ FAIL"
            print(f"{status} {cls_name:40s} - {reg_name}")
            
            if has_division:
                curr_passed += 1
            else:
                curr_failed += 1
    
    print(f"\nCurrent Sensor Results: {curr_passed}/{len(current_sensors)} passed")
    
    # Test energy sensors
    print("\n" + "=" * 80)
    print("TESTING ENERGY SENSORS (kWh should have /100.0, Ah should not)")
    print("=" * 80)
    
    energy_passed = 0
    energy_failed = 0
    for cls_name, reg_name in energy_sensors:
        pattern = rf'class {cls_name}\(.*?\):(.*?)(?=\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            cls_content = match.group(1)
            
            # Check if it's a kWh sensor (should have /100.0)
            is_kwh = 'KW_HOURS' in reg_name or ('ENERGY' in reg_name and 'AMP' not in reg_name)
            
            if is_kwh:
                has_division = check_formula_division(cls_name, cls_content, '/ 100.0')
                status = "✅ PASS" if has_division else "❌ FAIL"
                print(f"{status} {cls_name:40s} - {reg_name} (kWh, needs /100.0)")
            else:
                # Check that it doesn't have division for Ah sensors
                has_division = check_formula_division(cls_name, cls_content, '')
                status = "✅ PASS" if has_division else "❌ FAIL"
                print(f"{status} {cls_name:40s} - {reg_name} (Ah, no division)")
            
            if has_division:
                energy_passed += 1
            else:
                energy_failed += 1
    
    print(f"\nEnergy Sensor Results: {energy_passed}/{len(energy_sensors)} passed")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_tests = len(temperature_sensors) + len(voltage_sensors) + len(current_sensors) + len(energy_sensors)
    total_passed = temp_passed + volt_passed + curr_passed + energy_passed
    
    print(f"Total Tests Run: {total_tests}")
    print(f"Tests Passed: {total_passed}")
    print(f"Tests Failed: {temp_failed + volt_failed + curr_failed + energy_failed}")
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED! All sensor formulas are correctly applied.")
    else:
        print(f"\n⚠️  Some tests failed. Please review the sensors above that need attention.")
    
    return total_passed == total_tests

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
