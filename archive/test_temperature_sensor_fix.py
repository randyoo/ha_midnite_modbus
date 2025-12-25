#!/usr/bin/env python3
"""
Test script to verify the temperature sensor filtering fix.
This simulates the scenario where legitimate temperature changes occur.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from unittest.mock import Mock
from midnite.sensor import FETTemperatureSensor, PCBTemperatureSensor
import time

def test_temperature_change_recovery():
    """Test that temperature sensors recover from legitimate changes."""
    
    print("Testing temperature sensor filtering fix...")
    print("=" * 60)
    
    # Create mock coordinator and entry
    coordinator = Mock()
    entry = Mock()
    entry.entry_id = "test_device"
    
    # Test FET Temperature Sensor
    print("\n1. Testing FET Temperature Sensor")
    fet_sensor = FETTemperatureSensor(coordinator, entry)
    
    # Simulate normal readings at 55°C (20 readings to build history)
    print("   - Building baseline with 20 readings at 55°C...")
    for i in range(20):
        result = fet_sensor._validate_temperature(550, "FET temperature")
        assert result == 55.0, f"Expected 55.0, got {result}"
    
    # Simulate a legitimate drop to 46.5°C (this was causing issues before)
    print("   - Testing legitimate change to 46.5°C...")
    result = fet_sensor._validate_temperature(465, "FET temperature")
    if result is None:
        print(f"   ✗ FAILED: Reading rejected (spike count: {fet_sensor._spike_count})")
        return False
    else:
        print(f"   ✓ PASSED: Reading accepted ({result}°C)")
    
    # Verify spike counter was reset
    if fet_sensor._spike_count > 0:
        print(f"   ✗ FAILED: Spike counter not reset ({fet_sensor._spike_count})")
        return False
    else:
        print(f"   ✓ PASSED: Spike counter reset to {fet_sensor._spike_count}")
    
    # Test PCB Temperature Sensor
    print("\n2. Testing PCB Temperature Sensor")
    pcb_sensor = PCBTemperatureSensor(coordinator, entry)
    
    # Simulate normal readings at 53°C (20 readings to build history)
    print("   - Building baseline with 20 readings at 53°C...")
    for i in range(20):
        result = pcb_sensor._validate_temperature(530, "PCB temperature")
        assert result == 53.0, f"Expected 53.0, got {result}"
    
    # Simulate a legitimate drop to 49°C
    print("   - Testing legitimate change to 49°C...")
    result = pcb_sensor._validate_temperature(490, "PCB temperature")
    if result is None:
        print(f"   ✗ FAILED: Reading rejected (spike count: {pcb_sensor._spike_count})")
        return False
    else:
        print(f"   ✓ PASSED: Reading accepted ({result}°C)")
    
    # Verify spike counter was reset
    if pcb_sensor._spike_count > 0:
        print(f"   ✗ FAILED: Spike counter not reset ({pcb_sensor._spike_count})")
        return False
    else:
        print(f"   ✓ PASSED: Spike counter reset to {pcb_sensor._spike_count}")
    
    # Test spike counter timeout mechanism
    print("\n3. Testing spike counter timeout mechanism")
    test_sensor = FETTemperatureSensor(coordinator, entry)
    
    # Simulate 5 spikes in a row
    print("   - Simulating 5 consecutive spikes...")
    for i in range(5):
        result = test_sensor._validate_temperature(2000, "FET temperature")  # Way out of range
        assert result is None, f"Expected None for invalid reading"
    
    print(f"   - Spike count after 5 rejections: {test_sensor._spike_count}")
    
    # Next reading should be allowed through (graceful degradation)
    print("   - Testing next reading (should be allowed)...")
    result = test_sensor._validate_temperature(500, "FET temperature")
    if result is None:
        print(f"   ✗ FAILED: Reading rejected even after 5 spikes")
        return False
    else:
        print(f"   ✓ PASSED: Reading allowed through ({result}°C)")
    
    # Test timeout reset (simulate 31 seconds passing)
    print("\n4. Testing spike counter timeout reset")
    test_sensor2 = FETTemperatureSensor(coordinator, entry)
    
    # Simulate spikes
    for i in range(3):
        result = test_sensor2._validate_temperature(2000, "FET temperature")
    
    print(f"   - Spike count: {test_sensor2._spike_count}")
    print(f"   - Last spike time set to: {test_sensor2._last_spike_time}")
    
    # Simulate 31 seconds passing
    test_sensor2._last_spike_time = time.time() - 31
    
    # Next reading should trigger timeout reset
    print("   - Testing with simulated 31 second timeout...")
    result = test_sensor2._validate_temperature(500, "FET temperature")
    if result is None:
        print(f"   ✗ FAILED: Reading rejected despite timeout")
        return False
    else:
        print(f"   ✓ PASSED: Timeout reset worked, reading accepted ({result}°C)")
    
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
