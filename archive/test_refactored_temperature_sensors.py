#!/usr/bin/env python3
"""
Test to verify that the refactored temperature sensors maintain identical behavior.
This test simulates various scenarios to ensure all three temperature sensors work correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from midnite.sensor import BatteryTemperatureSensor, FETTemperatureSensor, PCBTemperatureSensor
from midnite.coordinator import MidniteSolarUpdateCoordinator
from unittest.mock import Mock, MagicMock
import time


def create_mock_coordinator(data):
    """Create a mock coordinator with the given data."""
    coordinator = Mock(spec=MidniteSolarUpdateCoordinator)
    coordinator.data = {"data": data}
    return coordinator


def create_mock_entry():
    """Create a mock config entry."""
    entry = Mock()
    entry.entry_id = "test_device"
    return entry


def test_valid_temperature_readings():
    """Test that all three sensors handle valid temperature readings correctly."""
    print("\n" + "="*70)
    print("TEST 1: Valid Temperature Readings")
    print("="*70)
    
    test_cases = [
        (423, 42.3),   # Typical FET temp
        (408, 40.8),   # Typical PCB temp
        (250, 25.0),   # Default battery temp
        (1500, 150.0), # Max valid temp
        (-500, -50.0), # Min valid temp
    ]
    
    all_passed = True
    
    for raw_value, expected_temp in test_cases:
        print(f"\n  Testing with raw value: {raw_value} (expected: {expected_temp}°C)")
        
        # Test BatteryTemperatureSensor
        data = {"temperatures": {"BATT_TEMPERATURE": raw_value}}
        coordinator = create_mock_coordinator(data)
        entry = create_mock_entry()
        batt_sensor = BatteryTemperatureSensor(coordinator, entry)
        result = batt_sensor.native_value
        
        # Test FETTemperatureSensor
        data = {"temperatures": {"FET_TEMPERATURE": raw_value}}
        coordinator = create_mock_coordinator(data)
        fet_sensor = FETTemperatureSensor(coordinator, entry)
        result_fet = fet_sensor.native_value
        
        # Test PCBTemperatureSensor
        data = {"temperatures": {"PCB_TEMPERATURE": raw_value}}
        coordinator = create_mock_coordinator(data)
        pcb_sensor = PCBTemperatureSensor(coordinator, entry)
        result_pcb = pcb_sensor.native_value
        
        # All should return the same value
        if result == expected_temp and result_fet == expected_temp and result_pcb == expected_temp:
            print(f"    ✓ PASS: All sensors returned {result}°C")
        else:
            print(f"    ✗ FAIL: Battery={result}, FET={result_fet}, PCB={result_pcb}")
            all_passed = False
    
    return all_passed


def test_invalid_temperature_range():
    """Test that sensors reject temperatures outside valid range."""
    print("\n" + "="*70)
    print("TEST 2: Invalid Temperature Range (should be rejected)")
    print("="*70)
    
    test_cases = [
        (1510, 151.0), # Too high
        (-510, -51.0), # Too low
        (65051, 6505.1), # Absurd temperature
    ]
    
    all_passed = True
    
    for raw_value, temp_value in test_cases:
        print(f"\n  Testing with raw value: {raw_value} (temp: {temp_value}°C)")
        
        # Test BatteryTemperatureSensor
        data = {"temperatures": {"BATT_TEMPERATURE": raw_value}}
        coordinator = create_mock_coordinator(data)
        entry = create_mock_entry()
        batt_sensor = BatteryTemperatureSensor(coordinator, entry)
        result = batt_sensor.native_value
        
        # Test FETTemperatureSensor
        data = {"temperatures": {"FET_TEMPERATURE": raw_value}}
        coordinator = create_mock_coordinator(data)
        fet_sensor = FETTemperatureSensor(coordinator, entry)
        result_fet = fet_sensor.native_value
        
        # Test PCBTemperatureSensor
        data = {"temperatures": {"PCB_TEMPERATURE": raw_value}}
        coordinator = create_mock_coordinator(data)
        pcb_sensor = PCBTemperatureSensor(coordinator, entry)
        result_pcb = pcb_sensor.native_value
        
        # All should return None (rejected)
        if result is None and result_fet is None and result_pcb is None:
            print(f"    ✓ PASS: All sensors correctly rejected the reading")
        else:
            print(f"    ✗ FAIL: Battery={result}, FET={result_fet}, PCB={result_pcb}")
            all_passed = False
    
    return all_passed


def test_negative_temperature_conversion():
    """Test that negative temperatures are correctly converted from two's complement."""
    print("\n" + "="*70)
    print("TEST 3: Negative Temperature Conversion (two's complement)")
    print("="*70)
    
    # Simulate negative temperatures using two's complement
    test_cases = [
        (-100, 64536),   # -10.0°C
        (-250, 64786),   # -25.0°C
        (-500, 64936),   # -50.0°C (minimum valid)
    ]
    
    all_passed = True
    
    for expected_temp, raw_value in test_cases:
        print(f"\n  Testing with raw value: {raw_value} (expected: {expected_temp}°C)")
        
        # Test BatteryTemperatureSensor
        data = {"temperatures": {"BATT_TEMPERATURE": raw_value}}
        coordinator = create_mock_coordinator(data)
        entry = create_mock_entry()
        batt_sensor = BatteryTemperatureSensor(coordinator, entry)
        result = batt_sensor.native_value
        
        # Test FETTemperatureSensor
        data = {"temperatures": {"FET_TEMPERATURE": raw_value}}
        coordinator = create_mock_coordinator(data)
        fet_sensor = FETTemperatureSensor(coordinator, entry)
        result_fet = fet_sensor.native_value
        
        # Test PCBTemperatureSensor
        data = {"temperatures": {"PCB_TEMPERATURE": raw_value}}
        coordinator = create_mock_coordinator(data)
        pcb_sensor = PCBTemperatureSensor(coordinator, entry)
        result_pcb = pcb_sensor.native_value
        
        # All should return the same value
        if abs(result - expected_temp) < 0.1 and abs(result_fet - expected_temp) < 0.1 and abs(result_pcb - expected_temp) < 0.1:
            print(f"    ✓ PASS: All sensors returned {result}°C (expected {expected_temp}°C)")
        else:
            print(f"    ✗ FAIL: Battery={result}, FET={result_fet}, PCB={result_pcb}")
            all_passed = False
    
    return all_passed


def test_state_preservation():
    """Test that sensor state is preserved between readings."""
    print("\n" + "="*70)
    print("TEST 4: State Preservation (last_temp, last_time, recent_readings)")
    print("="*70)
    
    all_passed = True
    
    # Test BatteryTemperatureSensor
    print("\n  Testing BatteryTemperatureSensor state preservation:")
    data1 = {"temperatures": {"BATT_TEMPERATURE": 250}}
    coordinator = create_mock_coordinator(data1)
    entry = create_mock_entry()
    batt_sensor = BatteryTemperatureSensor(coordinator, entry)
    
    # First reading
    result1 = batt_sensor.native_value
    print(f"    First reading: {result1}°C")
    
    # Check that state was updated
    if hasattr(batt_sensor, '_last_temp') and batt_sensor._last_temp == 25.0:
        print(f"    ✓ PASS: _last_temp correctly set to {batt_sensor._last_temp}°C")
    else:
        print(f"    ✗ FAIL: _last_temp = {getattr(batt_sensor, '_last_temp', 'NOT SET')}")
        all_passed = False
    
    if hasattr(batt_sensor, '_recent_readings') and len(batt_sensor._recent_readings) == 1:
        print(f"    ✓ PASS: _recent_readings correctly updated (length={len(batt_sensor._recent_readings)})")
    else:
        print(f"    ✗ FAIL: _recent_readings length = {getattr(batt_sensor, '_recent_readings', [])}")
        all_passed = False
    
    # Test FETTemperatureSensor
    print("\n  Testing FETTemperatureSensor state preservation:")
    data2 = {"temperatures": {"FET_TEMPERATURE": 450}}
    coordinator = create_mock_coordinator(data2)
    fet_sensor = FETTemperatureSensor(coordinator, entry)
    
    result2 = fet_sensor.native_value
    print(f"    First reading: {result2}°C")
    
    if hasattr(fet_sensor, '_last_temp') and fet_sensor._last_temp == 45.0:
        print(f"    ✓ PASS: _last_temp correctly set to {fet_sensor._last_temp}°C")
    else:
        print(f"    ✗ FAIL: _last_temp = {getattr(fet_sensor, '_last_temp', 'NOT SET')}")
        all_passed = False
    
    # Test PCBTemperatureSensor
    print("\n  Testing PCBTemperatureSensor state preservation:")
    data3 = {"temperatures": {"PCB_TEMPERATURE": 400}}
    coordinator = create_mock_coordinator(data3)
    pcb_sensor = PCBTemperatureSensor(coordinator, entry)
    
    result3 = pcb_sensor.native_value
    print(f"    First reading: {result3}°C")
    
    if hasattr(pcb_sensor, '_last_temp') and pcb_sensor._last_temp == 40.0:
        print(f"    ✓ PASS: _last_temp correctly set to {pcb_sensor._last_temp}°C")
    else:
        print(f"    ✗ FAIL: _last_temp = {getattr(pcb_sensor, '_last_temp', 'NOT SET')}")
        all_passed = False
    
    return all_passed


def test_spike_detection():
    """Test that consecutive spikes are detected and handled correctly."""
    print("\n" + "="*70)
    print("TEST 5: Spike Detection (consecutive invalid readings)")
    print("="*70)
    
    all_passed = True
    
    # Test BatteryTemperatureSensor with multiple spikes
    print("\n  Testing BatteryTemperatureSensor spike detection:")
    entry = create_mock_entry()
    batt_sensor = BatteryTemperatureSensor(None, entry)  # No coordinator needed for this test
    
    # Simulate 3 consecutive spikes (should be rejected)
    for i in range(3):
        result = batt_sensor._validate_temperature(1510, "battery temperature")  # Invalid temp
        if result is None:
            print(f"    Spike {i+1}: Correctly rejected (spike_count={batt_sensor._spike_count})")
        else:
            print(f"    ✗ FAIL: Spike {i+1} was not rejected")
            all_passed = False
    
    # Fourth spike should also be rejected due to consecutive spikes
    result = batt_sensor._validate_temperature(500, "battery temperature")  # Valid temp but should be rejected
    if result is None:
        print(f"    ✓ PASS: Fourth reading correctly rejected due to consecutive spikes")
    else:
        print(f"    ✗ FAIL: Fourth reading was not rejected (value={result})")
        all_passed = False
    
    # After a valid reading, spike counter should reset
    batt_sensor._spike_count = 0  # Reset for next test
    result = batt_sensor._validate_temperature(500, "battery temperature")
    if result == 50.0:
        print(f"    ✓ PASS: Valid reading accepted after reset (value={result}°C)")
    else:
        print(f"    ✗ FAIL: Valid reading was rejected (value={result})")
        all_passed = False
    
    return all_passed


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("REFACTORED TEMPERATURE SENSOR TEST SUITE")
    print("="*70)
    
    results = []
    
    # Run all tests
    results.append(("Valid Temperature Readings", test_valid_temperature_readings()))
    results.append(("Invalid Temperature Range", test_invalid_temperature_range()))
    results.append(("Negative Temperature Conversion", test_negative_temperature_conversion()))
    results.append(("State Preservation", test_state_preservation()))
    results.append(("Spike Detection", test_spike_detection()))
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("="*70)
    
    if all_passed:
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    exit(main())
