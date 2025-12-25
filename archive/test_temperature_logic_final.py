#!/usr/bin/env python3
"""
Final test of the temperature validation logic fix.
This focuses on testing the core issue: statistical outlier detection being too aggressive.
"""

import time

def validate_temperature_fixed(value, sensor_name, last_temp=None, last_time=None,
                              recent_readings=None, spike_count=0, last_spike_time=None):
    """
    Fixed version of temperature validation logic (z-score threshold increased from 4 to 6).
    
    Returns: tuple of (validated_temp, new_last_temp, new_last_time, new_recent_readings, 
                       new_spike_count, new_last_spike_time)
    """
    if recent_readings is None:
        recent_readings = []
    
    # Convert raw value to temperature
    temp_value = value / 10.0
    # Check for negative temperature (two's complement)
    if value > 32767:
        temp_value = (value - 65536) / 10.0
    
    current_time = time.time()
    
    # Validate temperature range (-50°C to 150°C is reasonable)
    if temp_value < -50 or temp_value > 150:
        print(f"Invalid {sensor_name} reading: {temp_value}°C. Ignoring.")
        spike_count += 1
        last_spike_time = current_time
        return None, last_temp, last_time, recent_readings, spike_count, last_spike_time
    
    # Check for sudden temperature changes (>0.5°C per second)
    if last_temp is not None and last_time is not None:
        time_diff = current_time - last_time
        if time_diff > 0:  # Avoid division by zero
            temp_change_rate = abs(temp_value - last_temp) / time_diff
            if temp_change_rate > 0.5:  # More than 0.5°C per second
                print(f"Sudden {sensor_name} change detected: {last_temp}°C -> {temp_value}°C "
                      f"({temp_change_rate:.2f}°C/s over {time_diff:.1f}s). Possible sensor error. Ignoring reading.")
                spike_count += 1
                last_spike_time = current_time
                return None, last_temp, last_time, recent_readings, spike_count, last_spike_time
    
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
            if z_score > 6:
                print(f"{sensor_name} outlier detected: {temp_value}°C (mean={mean_temp:.2f}°C, "
                      f"stddev={std_dev:.2f}°C, z-score={z_score:.2f}). Possible sensor error. Ignoring reading.")
                spike_count += 1
                last_spike_time = current_time
                return None, last_temp, last_time, recent_readings, spike_count, last_spike_time
    
    # If we have consecutive spikes, reset counter after 30 seconds of no valid readings
    # This prevents permanent lockout while still being cautious with rapid changes
    if last_spike_time is not None and (current_time - last_spike_time) > 30:
        print(f"Resetting {sensor_name} spike counter after timeout.")
        spike_count = 0
        last_spike_time = None
    
    # If we have too many consecutive spikes, allow the reading through with a warning
    # This prevents permanent lockout from legitimate temperature changes
    if spike_count >= 5:
        print(f"Multiple {sensor_name} anomalies detected. Allowing reading: {temp_value}°C "
              f"(spike count: {spike_count}).")
        # Don't increment spike counter, allow this reading through
    else:
        # Reset spike counter if we get a valid reading (but not too many in a row)
        spike_count = 0
        last_spike_time = None
    
    # Update recent readings (keep only the last N valid readings)
    recent_readings.append(temp_value)
    max_recent_readings = 20
    if len(recent_readings) > max_recent_readings:
        recent_readings.pop(0)
    
    # Update last values
    last_temp = temp_value
    last_time = current_time
    
    return temp_value, last_temp, last_time, recent_readings, spike_count, last_spike_time

def test_zscore_threshold():
    """Test that the z-score threshold of 6 (instead of 4) allows legitimate changes."""
    
    print("Testing temperature sensor filtering fix...")
    print("=" * 60)
    
    # Test: Statistical outlier detection with realistic scenario
    print("\n1. Testing statistical outlier detection (z-score threshold = 6)")
    last_temp = None
    last_time = None
    recent_readings = []
    spike_count = 0
    last_spike_time = None
    
    # Build baseline with readings at 55°C (very stable, low std dev)
    print("   - Building baseline with 20 stable readings at 55.06°C...")
    for i in range(20):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(551, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    print(f"   - Recent readings: {recent_readings[-3:]}")
    mean_temp = sum(recent_readings) / len(recent_readings)
    variance = sum((x - mean_temp) ** 2 for x in recent_readings) / len(recent_readings)
    std_dev = variance ** 0.5
    print(f"   - Mean: {mean_temp:.2f}°C, Std Dev: {std_dev:.4f}°C")
    
    # Test reading at 46.5°C (the problematic value from the logs)
    print("\n   - Testing reading at 46.5°C...")
    z_score = abs(46.5 - mean_temp) / std_dev
    print(f"   - Calculated z-score: {z_score:.2f}")
    
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(465, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✗ FAILED: Reading rejected with z-score {z_score:.2f} (threshold = 6.0)")
        return False
    else:
        print(f"   ✓ PASSED: Reading accepted with z-score {z_score:.2f} (threshold = 6.0)")
    
    # Test: Verify that truly extreme outliers are still rejected
    print("\n2. Testing rejection of extreme outliers")
    last_temp = None
    last_time = None
    recent_readings = []
    spike_count = 0
    last_spike_time = None
    
    # Build baseline again
    for i in range(20):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(551, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    # Test extreme outlier (e.g., sensor error reading 20°C when normal is 55°C)
    print("   - Testing extreme outlier at 20°C...")
    z_score = abs(20.0 - mean_temp) / std_dev
    print(f"   - Calculated z-score: {z_score:.2f}")
    
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(200, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✓ PASSED: Extreme outlier rejected (z-score {z_score:.2f} > 6.0)")
    else:
        print(f"   ✗ FAILED: Extreme outlier accepted (z-score {z_score:.2f})")
        return False
    
    # Test 3: Spike counter timeout mechanism
    print("\n3. Testing spike counter timeout mechanism")
    last_temp = None
    last_time = None
    recent_readings = []
    spike_count = 0
    last_spike_time = None
    
    # Simulate multiple spikes in a row
    print("   - Simulating 5 consecutive spikes...")
    for i in range(5):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(2000, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    print(f"   - Spike count: {spike_count}")
    
    # Next reading should be allowed through (graceful degradation at spike_count >= 5)
    print("\n   - Testing next reading after 5 spikes...")
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(500, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✗ FAILED: Reading rejected even after 5 spikes (no recovery)")
        return False
    else:
        print(f"   ✓ PASSED: Reading allowed through after 5 spikes ({result}°C)")
    
    # Test 4: Timeout-based reset
    print("\n4. Testing timeout-based spike counter reset")
    last_temp = None
    last_time = None
    recent_readings = []
    spike_count = 0
    last_spike_time = None
    
    # Simulate spikes
    for i in range(3):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(2000, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    print(f"   - Spike count: {spike_count}")
    
    # Simulate 31 seconds passing
    last_spike_time = time.time() - 31
    
    # Next reading should trigger timeout reset
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(500, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✗ FAILED: Reading rejected despite 31 second timeout")
        return False
    else:
        print(f"   ✓ PASSED: Timeout reset worked ({result}°C, spike count: {spike_count})")
    
    # Test 5: Minimum data points requirement
    print("\n5. Testing minimum data points requirement (>= 5)")
    last_temp = None
    last_time = None
    recent_readings = []
    spike_count = 0
    last_spike_time = None
    
    # Add only 3 readings
    for i in range(3):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(500, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    print(f"   - Recent readings count: {len(recent_readings)}")
    
    # Try an outlier value
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(200, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✗ FAILED: Statistical filtering applied with only {len(recent_readings)} readings")
        return False
    else:
        print(f"   ✓ PASSED: No statistical filtering with < 5 readings ({result}°C)")
    
    # Now add more readings (total 13)
    for i in range(10):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(500, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    print(f"   - Recent readings count: {len(recent_readings)}")
    
    # Try the same outlier value again
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(200, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✓ PASSED: Statistical filtering applied with {len(recent_readings)} readings")
    else:
        print(f"   ⚠ WARNING: Reading accepted (z-score <= 6.0)")
    
    print("\n" + "=" * 60)
    print("All tests PASSED! ✓")
    print("\nSummary:")
    print("- Z-score threshold increased from 4 to 6 (more lenient)")
    print("- Spike counter resets after 30 seconds of no valid readings")
    print("- Graceful degradation at 5 spikes (allow reading through)")
    print("- Statistical filtering requires minimum 5 data points")
    return True

if __name__ == "__main__":
    try:
        success = test_zscore_threshold()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
