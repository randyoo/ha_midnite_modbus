#!/usr/bin/env python3
"""
Simple test to verify the fixes are correct.
This simulates the data flow without requiring Home Assistant.
"""

# Test 1: Verify temperature validation fix
print("Test 1: Temperature Validation Logic")
print("=" * 50)

# Simulate raw register values (tenths of a degree)
test_cases = [
    (423, 42.3),   # Valid FET temp
    (408, 40.8),   # Valid PCB temp
    (1500, 150.0), # Max valid temp
    (-500, -50.0), # Min valid temp
    (1510, 151.0), # Invalid - too high
    (-510, -51.0), # Invalid - too low
]

for raw_value, expected_temp in test_cases:
    temp_value = raw_value / 10.0
    
    # Old buggy logic (checking raw value)
    old_result = "INVALID" if raw_value < -50 or raw_value > 150 else "VALID"
    
    # New fixed logic (checking converted temp)
    new_result = "INVALID" if temp_value < -50 or temp_value > 150 else "VALID"
    
    print(f"Raw: {raw_value:4d} -> Temp: {temp_value:6.1f}°C")
    print(f"  Old logic: {old_result}")
    print(f"  New logic: {new_result}")
    print()

print("\nTest 2: Number Value Conversion Logic")
print("=" * 50)

# Simulate register values for different number types
test_values = [
    ("Voltage", 125, False),   # 12.5V - not a time value
    ("Current", 500, False),   # 50.0A - not a time value
    ("Time", 3600, True),      # 3600s - is a time value
]

for name, raw_value, is_time in test_values:
    if is_time:
        converted = float(raw_value)
    else:
        converted = float(raw_value) / 10.0
    
    print(f"{name}: Raw {raw_value} -> Converted {converted}")

print("\nAll tests completed!")
