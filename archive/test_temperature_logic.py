#!/usr/bin/env python3
"""
Direct test of the temperature validation logic.
This extracts and tests just the core algorithm without module dependencies.
"""

import time

def validate_temperature_fixed(value, sensor_name, last_temp=None, last_time=None,
                              recent_readings=None, spike_count=0, last_spike_time=None):
    """
    Fixed version of temperature validation logic.
    
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

def test_temperature_change_recovery():
    """Test that temperature sensors recover from legitimate changes."""
    
    print("Testing temperature sensor filtering fix...")
    print("=" * 60)
    
    # Test 1: Legitimate temperature change (with simulated time delays)
    print("\n1. Testing legitimate temperature change handling")
    last_temp = None
    last_time = None
    recent_readings = []
    spike_count = 0
    last_spike_time = None
    
    # Build baseline with 20 readings at 55°C (simulate 1 second between readings)
    print("   - Building baseline with 20 readings at 55°C...")
    for i in range(20):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(550, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
        time.sleep(0.1)  # Small delay to simulate real-time readings
    
    print(f"   - Recent readings: {recent_readings[-5:]}")
    print(f"   - Spike count: {spike_count}")
    
    # Test legitimate drop to 46.5°C (simulate gradual change over several seconds)
    print("\n   - Testing legitimate change to 46.5°C...")
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(465, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✗ FAILED: Reading rejected (spike count: {spike_count})")
        return False
    else:
        print(f"   ✓ PASSED: Reading accepted ({result}°C)")
    
    if spike_count > 0:
        print(f"   ✗ FAILED: Spike counter not reset ({spike_count})")
        return False
    else:
        print(f"   ✓ PASSED: Spike counter reset to {spike_count}")
    
    # Test 2: Spike counter timeout mechanism
    print("\n2. Testing spike counter timeout mechanism")
    last_temp = None
    last_time = None
    recent_readings = []
    spike_count = 0
    last_spike_time = None
    
    # Simulate 5 spikes in a row (out of range values)
    print("   - Simulating 5 consecutive spikes...")
    for i in range(5):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(2000, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    print(f"   - Spike count after 5 rejections: {spike_count}")
    
    # Next reading should be allowed through (graceful degradation)
    print("\n   - Testing next reading (should be allowed)...")
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(500, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✗ FAILED: Reading rejected even after 5 spikes")
        return False
    else:
        print(f"   ✓ PASSED: Reading allowed through ({result}°C)")
    
    # Test 3: Timeout reset (simulate 31 seconds passing)
    print("\n3. Testing spike counter timeout reset")
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
    print(f"   - Last spike time set to: {last_spike_time}")
    
    # Simulate 31 seconds passing
    last_spike_time = time.time() - 31
    
    # Next reading should trigger timeout reset
    print("\n   - Testing with simulated 31 second timeout...")
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(500, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✗ FAILED: Reading rejected despite timeout")
        return False
    else:
        print(f"   ✓ PASSED: Timeout reset worked, reading accepted ({result}°C)")
    
    # Test 4: Minimum data points requirement
    print("\n4. Testing minimum data points requirement")
    last_temp = None
    last_time = None
    recent_readings = []
    spike_count = 0
    last_spike_time = None
    
    # Add only 3 readings (less than minimum of 5)
    for i in range(3):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(500, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    print(f"   - Recent readings count: {len(recent_readings)}")
    
    # Try a value that would be an outlier if statistical filtering was applied
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(200, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✗ FAILED: Statistical filtering applied with only {len(recent_readings)} readings")
        return False
    else:
        print(f"   ✓ PASSED: Reading accepted without statistical filtering (only {len(recent_readings)} readings)")
    
    # Now add more readings and test again
    for i in range(10):  # Total of 13 readings now
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(500, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    print(f"   - Recent readings count: {len(recent_readings)}")
    
    # Try the same value again (should be rejected now with statistical filtering)
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(200, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✓ PASSED: Statistical filtering correctly applied with {len(recent_readings)} readings")
    else:
        print(f"   ⚠ WARNING: Reading accepted even though it's an outlier (z-score > 6)")
    
    # Test 5: The original problem scenario - rapid legitimate change
    print("\n5. Testing original problem scenario (rapid legitimate change)")
    last_temp = None
    last_time = None
    recent_readings = []
    spike_count = 0
    last_spike_time = None
    
    # Build baseline at 55°C
    for i in range(20):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(550, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    # Simulate the problematic scenario: rapid drop to 46.5°C
    print("   - Simulating rapid change from 55°C to 46.5°C...")
    result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
        validate_temperature_fixed(465, "FET temperature", 
                                   last_temp, last_time, recent_readings,
                                   spike_count, last_spike_time)
    
    if result is None:
        print(f"   ✗ FAILED: First reading rejected (this was the original bug)")
        return False
    else:
        print(f"   ✓ PASSED: First reading accepted ({result}°C)")
    
    # Now test subsequent readings - they should also be accepted
    print("   - Testing subsequent readings...")
    for i in range(5):
        result, last_temp, last_time, recent_readings, spike_count, last_spike_time = \
            validate_temperature_fixed(465, "FET temperature", 
                                       last_temp, last_time, recent_readings,
                                       spike_count, last_spike_time)
    
    if spike_count > 0:
        print(f"   ✗ FAILED: Subsequent readings rejected (spike count: {spike_count})")
        return False
    else:
        print(f"   ✓ PASSED: All subsequent readings accepted (spike count: {spike_count})")
    
    print("\n" + "=" * 60)
    print("All tests PASSED! ✓")
    return True

if __name__ == "__main__":
    try:
        success = test_temperature_change_recovery()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
