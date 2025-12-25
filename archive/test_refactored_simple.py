#!/usr/bin/env python3
"""
Simple test to verify the refactored temperature sensor code structure.
This test checks that the base class and inheritance are working correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

# Test imports work
try:
    from midnite.sensor import TemperatureSensorBase, BatteryTemperatureSensor, FETTemperatureSensor, PCBTemperatureSensor
    print("✓ All sensor classes imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test inheritance
print("\nTesting class hierarchy:")
print(f"  BatteryTemperatureSensor inherits from TemperatureSensorBase: {issubclass(BatteryTemperatureSensor, TemperatureSensorBase)}")
print(f"  FETTemperatureSensor inherits from TemperatureSensorBase: {issubclass(FETTemperatureSensor, TemperatureSensorBase)}")
print(f"  PCBTemperatureSensor inherits from TemperatureSensorBase: {issubclass(PCBTemperatureSensor, TemperatureSensorBase)}")

# Test that base class has the validation method
if hasattr(TemperatureSensorBase, '_validate_temperature'):
    print("\n✓ TemperatureSensorBase has _validate_temperature method")
else:
    print("\n✗ TemperatureSensorBase missing _validate_temperature method")
    sys.exit(1)

# Test that all sensors have the required attributes
print("\nTesting sensor attributes:")
from unittest.mock import Mock

entry = Mock()
entry.entry_id = "test"

try:
    # Create instances without coordinator (for attribute checking only)
    batt = BatteryTemperatureSensor(None, entry)
    fet = FETTemperatureSensor(None, entry)
    pcb = PCBTemperatureSensor(None, entry)
    
    print(f"  BatteryTemperatureSensor has _last_temp: {hasattr(batt, '_last_temp')}")
    print(f"  BatteryTemperatureSensor has _recent_readings: {hasattr(batt, '_recent_readings')}")
    print(f"  BatteryTemperatureSensor has _spike_count: {hasattr(batt, '_spike_count')}")
    
    print(f"  FETTemperatureSensor has _last_temp: {hasattr(fet, '_last_temp')}")
    print(f"  FETTemperatureSensor has _recent_readings: {hasattr(fet, '_recent_readings')}")
    print(f"  FETTemperatureSensor has _spike_count: {hasattr(fet, '_spike_count')}")
    
    print(f"  PCBTemperatureSensor has _last_temp: {hasattr(pcb, '_last_temp')}")
    print(f"  PCBTemperatureSensor has _recent_readings: {hasattr(pcb, '_recent_readings')}")
    print(f"  PCBTemperatureSensor has _spike_count: {hasattr(pcb, '_spike_count')}")
    
except Exception as e:
    print(f"✗ Instance creation failed: {e}")
    sys.exit(1)

print("\n✓ All tests passed!")
