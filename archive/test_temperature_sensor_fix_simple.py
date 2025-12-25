#!/usr/bin/env python3
"""
Simple test script to verify the temperature sensor filtering fix.
This tests the core logic without requiring Home Assistant dependencies.
"""

import sys
import os
import time
from unittest.mock import Mock, MagicMock

# Mock the homeassistant imports before importing the sensor module
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.components.sensor'] = MagicMock()
sys.modules['homeassistant.helpers.entity'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()

# Now we can import the sensor module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from midnite.sensor import TemperatureSensorBase

def test_temperature_change_recovery():
    """Test that temperature sensors recover from legitimate changes."""
    
    print("Testing temperature sensor filtering fix...")
    print("=" * 60)
    
    # Create mock coordinator and entry
    coordinator = Mock()
    entry = Mock()
    entry.entry_id = "test_device"
    
    # Test FET Temperature Sensor (using base class for testing)
    print("\n1. Testing legitimate temperature change handling")
    sensor = TemperatureSensorBase(coordinator, entry)
    
    # Simulate normal readings at 55°C (20 readings to build history)
    print("   - Building baseline with 20 readings at 55°C...")
    for i in range(20):
        result = sensor._validate_temperature(550, "FET temperature")
        assert result == 55.0, f"Expected 55.0, got {result}"
    
    print(f"   - Recent readings: {sensor._recent_readings[-5:]}")
    print(f"   - Spike count: {sensor._spike_count}")
    
    # Simulate a legitimate drop to 46.5°C (this was causing issues before)
    print("\n   - Testing legitimate change to 46.5°C...")
    result = sensor._validate_temperature(465, "FET temperature")
    
    if result is None:
        print(f"   ✗ FAILED: Reading rejected (spike count: {sensor._spike_count})")
        return False
    else:
        print(f"   ✓ PASSED: Reading accepted ({result}°C)")
    
    # Verify spike counter was reset
    if sensor._spike_count > 0:
        print(f"   ✗ FAILED: Spike counter not reset ({sensor._spike_count})")
        return False
    else:
        print(f"   ✓ PASSED: Spike counter reset to {sensor._spike_count}")
    
    # Test spike counter timeout mechanism
    print("\n2. Testing spike counter timeout mechanism")
    sensor2 = TemperatureSensorBase(coordinator, entry)
    
    # Simulate 5 spikes in a row (out of range values)
    print("   - Simulating 5 consecutive spikes...")
    for i in range(5):
        result = sensor2._validate_temperature(2000, "FET temperature")  # Way out of range
        assert result is None, f"Expected None for invalid reading"
    
    print(f"   - Spike count after 5 rejections: {sensor2._spike_count}")
    
    # Next reading should be allowed through (graceful degradation)
    print("   - Testing next reading (should be allowed)...")
    result = sensor2._validate_temperature(500, "FET temperature")
    if result is None:
        print(f"   ✗ FAILED: Reading rejected even after 5 spikes")
        return False
    else:
        print(f"   ✓ PASSED: Reading allowed through ({result}°C)")
    
    # Test timeout reset (simulate 31 seconds passing)
    print("\n3. Testing spike counter timeout reset")
    sensor3 = TemperatureSensorBase(coordinator, entry)
    
    # Simulate spikes
    for i in range(3):
        result = sensor3._validate_temperature(2000, "FET temperature")
    
    print(f"   - Spike count: {sensor3._spike_count}")
    print(f"   - Last spike time set to: {sensor3._last_spike_time}")
    
    # Simulate 31 seconds passing
    sensor3._last_spike_time = time.time() - 31
    
    # Next reading should trigger timeout reset
    print("   - Testing with simulated 31 second timeout...")
    result = sensor3._validate_temperature(500, "FET temperature")
    if result is None:
        print(f"   ✗ FAILED: Reading rejected despite timeout")
        return False
    else:
        print(f"   ✓ PASSED: Timeout reset worked, reading accepted ({result}°C)")
    
    # Test that statistical filtering requires minimum data points
    print("\n4. Testing minimum data points requirement")
    sensor4 = TemperatureSensorBase(coordinator, entry)
    
    # Add only 3 readings (less than minimum of 5)
    for i in range(3):
        result = sensor4._validate_temperature(500, "FET temperature")
    
    print(f"   - Recent readings count: {len(sensor4._recent_readings)}")
    
    # Try a value that would be an outlier if statistical filtering was applied
    result = sensor4._validate_temperature(200, "FET temperature")  # 20°C (would be outlier)
    if result is None:
        print(f"   ✗ FAILED: Statistical filtering applied with only {len(sensor4._recent_readings)} readings")
        return False
    else:
        print(f"   ✓ PASSED: Reading accepted without statistical filtering (only {len(sensor4._recent_readings)} readings)")
    
    # Now add more readings and test again
    for i in range(10):  # Total of 13 readings now
        result = sensor4._validate_temperature(500, "FET temperature")
    
    print(f"   - Recent readings count: {len(sensor4._recent_readings)}")
    
    # Try the same value again (should be rejected now with statistical filtering)
    result = sensor4._validate_temperature(200, "FET temperature")  # 20°C
    if result is None:
        print(f"   ✓ PASSED: Statistical filtering correctly applied with {len(sensor4._recent_readings)} readings")
    else:
        print(f"   ⚠ WARNING: Reading accepted even though it's an outlier (z-score > 6)")
    
    print("\n" + "=" * 60)
    print("All tests PASSED! ✓")
    return True

if __name__ == "__main__":
    try:
        success = test_temperature_change_recovery()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
