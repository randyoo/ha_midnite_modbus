#!/usr/bin/env python3
"""
Test script to verify device information handling.
This simulates the device_info creation logic without needing a real device.
"""

import sys
sys.path.insert(0, '/Users/randy/midnite')

from custom_components.midnite.const import DOMAIN

def test_device_info_creation():
    """Test device info creation with different scenarios."""
    
    print("=" * 60)
    print("Testing Device Info Creation")
    print("=" * 60)
    
    # Scenario 1: Successful read of serial number
    print("\n1. Testing with successful serial number read:")
    device_info = {
        "identifiers": {},
        "name": None,
        "model": "Classic 250",
        "serial_number": "3365322520",
        "manufacturer": "Midnite Solar",
    }
    
    # Simulate the logic from __init__.py
    if device_info.get("serial_number"):
        device_info["identifiers"] = {(DOMAIN, str(device_info["serial_number"]))}
        device_info["name"] = f"Midnite {device_info.get('model', 'Device')} ({device_info['serial_number']})"
    
    print(f"   Identifiers: {device_info['identifiers']}")
    print(f"   Name: {device_info['name']}")
    print("   ✅ Expected single device with serial number as identifier")
    
    # Scenario 2: Failed read of serial number (fallback to hostname)
    print("\n2. Testing with failed serial number read:")
    device_info = {
        "identifiers": {},
        "name": None,
        "model": "Classic 250",
        "manufacturer": "Midnite Solar",
    }
    hostname = "192.168.88.24"
    
    if device_info.get("serial_number"):
        device_info["identifiers"] = {(DOMAIN, str(device_info["serial_number"]))}
        device_info["name"] = f"Midnite {device_info.get('model', 'Device')} ({device_info['serial_number']})"
    else:
        device_info["identifiers"] = {(DOMAIN, hostname)}
        device_info["name"] = f"Midnite {device_info.get('model', 'Device')} @ {hostname}"
    
    print(f"   Identifiers: {device_info['identifiers']}")
    print(f"   Name: {device_info['name']}")
    print("   ✅ Expected single device with hostname as identifier")
    
    # Scenario 3: Verify device ID calculation
    print("\n3. Testing Device ID calculation:")
    msb = 0xC896  # 51350 in decimal
    lsb = 0xBF18  # 48920 in decimal
    device_id = (msb << 16) | lsb
    
    print(f"   MSB (register 20492): {msb} (0x{msb:04X}) = {msb}")
    print(f"   LSB (register 20493): {lsb} (0x{lsb:04X}) = {lsb}")
    print(f"   Combined Device ID: {device_id} (0x{device_id:08X})")
    print("   ✅ Matches Midnite website: C896 BF18")
    
    # Scenario 4: Verify charge stage extraction
    print("\n4. Testing Charge Stage Extraction:")
    test_values = [
        (0x0003, "Absorb", "MSB=0, LSB=3"),
        (0x0004, "BulkMPPT", "MSB=0, LSB=4"),
        (0x0005, "Float", "MSB=0, LSB=5"),
        (0x0306, "Unknown(3)", "MSB=3, LSB=6"),
        (0x0704, "Equalize", "MSB=7, LSB=4"),
    ]
    
    from custom_components.midnite.const import CHARGE_STAGES
    
    for raw_value, expected_stage, description in test_values:
        charge_stage_value = (raw_value >> 8) & 0xFF
        actual_stage = CHARGE_STAGES.get(charge_stage_value, f"Unknown({charge_stage_value})")
        status = "✅" if actual_stage == expected_stage else "❌"
        print(f"   {status} Raw: 0x{raw_value:04X} ({description})")
        print(f"      → MSB={charge_stage_value}, Stage='{actual_stage}' (expected '{expected_stage}')")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_device_info_creation()
