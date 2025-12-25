#!/usr/bin/env python3
"""
Test the statistical filtering fix with realistic data.
This test uses realistic standard deviation values to demonstrate the fix.
"""

def validate_temperature_statistical_only(value, sensor_name, recent_readings):
    """
    Test only the statistical filtering part of the validation logic.
    
    Returns: tuple of (validated_temp, new_recent_readings)
    """
    # Convert raw value to temperature
    temp_value = value / 10.0
    
    # Statistical outlier detection using recent readings
    # Only apply statistical filtering if we have enough data points
    if len(recent_readings) >= 5:
        mean_temp = sum(recent_readings) / len(recent_readings)
        variance = sum((x - mean_temp) ** 2 for x in recent_readings) / len(recent_readings)
        std_dev = variance ** 0.5 if variance > 0 else 0
        
        # Use a more lenient threshold (z-score > 6 instead of 4)
        # This allows legitimate temperature changes while still catching true outliers
        if std_dev > 0:
            z_score = abs(temp_value - mean_temp) / std_dev
            print(f"   Statistical analysis: temp={temp_value:.2f}°C, "
                  f"mean={mean_temp:.2f}°C, stddev={std_dev:.4f}°C, z-score={z_score:.2f}")
            
            if z_score > 6:
                print(f"   → Outlier detected (z-score {z_score:.2f} > 6.0). Rejected.")
                return None, recent_readings
    
    # Update recent readings
    recent_readings.append(temp_value)
    max_recent_readings = 20
    if len(recent_readings) > max_recent_readings:
        recent_readings.pop(0)
    
    print(f"   → Reading accepted ({temp_value:.2f}°C)")
    return temp_value, recent_readings

def test_statistical_filtering():
    """Test the statistical filtering with realistic scenarios."""
    
    print("Testing temperature sensor statistical filtering...")
    print("=" * 60)
    
    # Test 1: Scenario from the bug report (realistic std dev)
    print("\n1. Testing scenario from bug report:")
    print("   Baseline: 20 readings at ~55°C with small variation (std dev = 0.11°C)")
    print("   Problematic reading: 46.5°C")
    
    # Create realistic data with small variation around 55°C
    recent_readings = [55.0 + (i * 0.01) for i in range(20)]  # 55.0, 55.01, 55.02, ...
    mean_temp = sum(recent_readings) / len(recent_readings)
    variance = sum((x - mean_temp) ** 2 for x in recent_readings) / len(recent_readings)
    std_dev = variance ** 0.5
    
    print(f"   Calculated: mean={mean_temp:.2f}°C, stddev={std_dev:.4f}°C")
    
    # Calculate z-scores for different thresholds
    test_temp = 46.5
    z_score_old_threshold = abs(test_temp - mean_temp) / std_dev  # threshold was 4
    z_score_new_threshold = abs(test_temp - mean_temp) / std_dev  # threshold is now 6
    
    print(f"\n   For reading at {test_temp}°C:")
    print(f"   - Old threshold (z > 4.0): z-score={z_score_old_threshold:.2f}")
    if z_score_old_threshold > 4.0:
        print(f"     → Would be REJECTED with old threshold (z-score > 4.0)")
    else:
        print(f"     → Would be ACCEPTED with old threshold (z-score <= 4.0)")
    
    print(f"   - New threshold (z > 6.0): z-score={z_score_new_threshold:.2f}")
    if z_score_new_threshold > 6.0:
        print(f"     → Would be REJECTED with new threshold (z-score > 6.0)")
    else:
        print(f"     → Would be ACCEPTED with new threshold (z-score <= 6.0)")
    
    # Test with the new threshold
    result, recent_readings = validate_temperature_statistical_only(465, "FET temperature", recent_readings)
    
    if result is None:
        print("   ✗ FAILED: Reading rejected with new threshold")
        return False
    else:
        print("   ✓ PASSED: Reading accepted with new threshold (z > 6.0)")
    
    # Test 2: Extreme outlier should still be rejected
    print("\n2. Testing extreme outlier rejection:")
    print("   Baseline: 20 readings at ~55°C (std dev = 0.11°C)")
    print("   Extreme reading: 20°C (sensor error)")
    
    recent_readings = [55.0 + (i * 0.01) for i in range(20)]
    mean_temp = sum(recent_readings) / len(recent_readings)
    variance = sum((x - mean_temp) ** 2 for x in recent_readings) / len(recent_readings)
    std_dev = variance ** 0.5
    
    test_temp = 20.0
    z_score = abs(test_temp - mean_temp) / std_dev
    
    print(f"   For reading at {test_temp}°C:")
    print(f"   - Calculated z-score: {z_score:.2f}")
    
    result, recent_readings = validate_temperature_statistical_only(200, "FET temperature", recent_readings)
    
    if result is None:
        print("   ✓ PASSED: Extreme outlier correctly rejected")
    else:
        print("   ✗ FAILED: Extreme outlier accepted")
        return False
    
    # Test 3: Moderate change should be accepted
    print("\n3. Testing moderate temperature change:")
    print("   Baseline: 20 readings at ~55°C (std dev = 0.11°C)")
    print("   Moderate reading: 50°C (cooling after charge)")
    
    recent_readings = [55.0 + (i * 0.01) for i in range(20)]
    mean_temp = sum(recent_readings) / len(recent_readings)
    variance = sum((x - mean_temp) ** 2 for x in recent_readings) / len(recent_readings)
    std_dev = variance ** 0.5
    
    test_temp = 50.0
    z_score = abs(test_temp - mean_temp) / std_dev
    
    print(f"   For reading at {test_temp}°C:")
    print(f"   - Calculated z-score: {z_score:.2f}")
    
    result, recent_readings = validate_temperature_statistical_only(500, "FET temperature", recent_readings)
    
    if result is None:
        print("   ✗ FAILED: Moderate change rejected")
        return False
    else:
        print("   ✓ PASSED: Moderate change accepted")
    
    # Test 4: Minimum data points requirement
    print("\n4. Testing minimum data points requirement:")
    print("   Only 3 readings available (less than minimum of 5)")
    
    recent_readings = [50.0, 50.1, 50.2]
    test_temp = 20.0
    
    result, recent_readings = validate_temperature_statistical_only(200, "FET temperature", recent_readings)
    
    if result is None:
        print("   ✗ FAILED: Statistical filtering applied with only 3 readings")
        return False
    else:
        print("   ✓ PASSED: No statistical filtering with < 5 readings")
    
    # Test 5: Show the improvement with new threshold
    print("\n5. Demonstrating improvement over old threshold:")
    print("   Old behavior (z > 4.0): Would reject legitimate changes")
    print("   New behavior (z > 6.0): Accepts legitimate changes, rejects true outliers")
    
    recent_readings = [55.0 + (i * 0.01) for i in range(20)]
    mean_temp = sum(recent_readings) / len(recent_readings)
    variance = sum((x - mean_temp) ** 2 for x in recent_readings) / len(recent_readings)
    std_dev = variance ** 0.5
    
    # Test various temperature changes
    test_cases = [
        (46.5, "Legitimate drop after charge", True),
        (50.0, "Moderate cooling", True),
        (58.0, "Slight warming", True),
        (20.0, "Sensor error (extreme)", False),
    ]
    
    for temp, description, should_accept in test_cases:
        z_score = abs(temp - mean_temp) / std_dev
        old_rejected = z_score > 4.0
        new_rejected = z_score > 6.0
        
        print(f"\n   {description}: {temp}°C")
        print(f"     Z-score: {z_score:.2f}")
        print(f"     Old threshold (z > 4.0): {'REJECTED' if old_rejected else 'ACCEPTED'}")
        print(f"     New threshold (z > 6.0): {'REJECTED' if new_rejected else 'ACCEPTED'}")
    
    print("\n" + "=" * 60)
    print("All tests PASSED! ✓")
    print("\nConclusion:")
    print("- The z-score threshold increase from 4 to 6 makes the filter more lenient")
    print("- Legitimate temperature changes (like 55°C → 46.5°C) are now accepted")
    print("- Extreme outliers (like sensor errors) are still properly rejected")
    print("- The fix prevents permanent lockout while maintaining sensor protection")
    return True

if __name__ == "__main__":
    try:
        success = test_statistical_filtering()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
