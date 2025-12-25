#!/usr/bin/env python3
"""
Test to verify the temperature validation fix.
This simulates the temperature conversion and validation logic.
"""

def test_temperature_validation():
    """Test that temperature validation works correctly with the fix."""
    
    print("Testing Temperature Validation Fix")
    print("=" * 60)
    
    # Test cases: (raw_register_value, expected_temp_celsius, should_be_valid)
    test_cases = [
        # Valid temperatures
        (423, 42.3, True),   # 42.3°C - typical FET temp
        (408, 40.8, True),   # 40.8°C - typical PCB temp
        (250, 25.0, True),   # 25.0°C - default battery temp when no sensor
        (1500, 150.0, True), # 150.0°C - max valid temp
        (-500, -50.0, True), # -50.0°C - min valid temp
        
        # Invalid temperatures (should be rejected)
        (1510, 151.0, False), # 151.0°C - too high
        (-510, -51.0, False), # -51.0°C - too low
        
        # Edge case from the bug report
        (65051, 6505.1, False), # 6505.1°C - absurd temperature
    ]
    
    print("\nTest Results:")
    print("-" * 60)
    
    all_passed = True
    for raw_value, expected_temp, should_be_valid in test_cases:
        # Simulate the conversion logic from sensor.py
        temp_value = raw_value / 10.0
        
        # Check for negative temperature (two's complement)
        if temp_value > 32767:
            temp_value = temp_value - 65536
        
        # NEW FIXED VALIDATION: Check converted temp_value, not raw value
        is_valid = (-50 <= temp_value <= 150)
        
        # Determine if test passed
        test_passed = (is_valid == should_be_valid)
        status = "✓ PASS" if test_passed else "✗ FAIL"
        
        print(f"{status} | Raw: {raw_value:6d} → Temp: {temp_value:7.1f}°C")
        print(f"      | Expected valid: {should_be_valid}, Got valid: {is_valid}")
        
        if not test_passed:
            all_passed = False
    
    print("-" * 60)
    
    if all_passed:
        print("✓ All tests PASSED!")
        return True
    else:
        print("✗ Some tests FAILED!")
        return False


def test_old_buggy_logic():
    """Test the old buggy validation logic to show what was wrong."""
    
    print("\n\nComparing OLD (Buggy) vs NEW (Fixed) Logic")
    print("=" * 60)
    
    test_cases = [
        (423, 42.3),   # Valid FET temp
        (408, 40.8),   # Valid PCB temp
        (1500, 150.0), # Max valid temp
    ]
    
    print("\nOLD LOGIC (checking raw value):")
    for raw_value, expected_temp in test_cases:
        is_valid_old = (-50 <= raw_value <= 150)
        status = "✓ VALID" if is_valid_old else "✗ INVALID"
        print(f"{status} | Raw: {raw_value:6d} → Temp: {expected_temp:7.1f}°C")
    
    print("\nNEW LOGIC (checking converted temp_value):")
    for raw_value, expected_temp in test_cases:
        is_valid_new = (-50 <= expected_temp <= 150)
        status = "✓ VALID" if is_valid_new else "✗ INVALID"
        print(f"{status} | Raw: {raw_value:6d} → Temp: {expected_temp:7.1f}°C")
    
    print("\nThe old logic incorrectly rejected valid temperatures!")


if __name__ == "__main__":
    success = test_temperature_validation()
    test_old_buggy_logic()
    
    if not success:
        exit(1)
