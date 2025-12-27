#!/usr/bin/env python3
"""Verify the generated files."""

import re

def verify_const_py():
    """Verify const.py was generated correctly."""
    with open('custom_components/midnite/const.py', 'r') as f:
        content = f.read()
    
    # Check if REGISTER_MAP and REGISTER_CATEGORIES are present
    assert 'REGISTER_MAP' in content, "Missing REGISTER_MAP"
    assert 'REGISTER_CATEGORIES' in content, "Missing REGISTER_CATEGORIES"
    
    # Count entries
    map_count = len(re.findall(r'"[^"]+": \d+', content))
    cat_count = len(re.findall(r'"[^"]+": "[A-Z]"', content))
    
    print(f"✓ const.py contains REGISTER_MAP and REGISTER_CATEGORIES")
    print(f"  - REGISTER_MAP has {map_count} entries")
    print(f"  - REGISTER_CATEGORIES has {cat_count} entries")


def verify_sensor_py():
    """Verify sensor.py was generated correctly."""
    with open('custom_components/midnite/sensor.py', 'r') as f:
        content = f.read()
    
    # Check for base class
    assert 'class MidniteSolarSensor' in content, "Missing MidniteSolarSensor base class"
    
    # Count sensor classes (excluding base class)
    sensor_classes = re.findall(r'class (\w+)Sensor\(MidniteSolarSensor\)', content)
    print(f"✓ sensor.py generated with {len(sensor_classes)} sensor classes")
    
    # Check for async_setup_entry
    assert 'async def async_setup_entry' in content, "Missing async_setup_entry"
    print("  - Contains async_setup_entry function")


def verify_number_py():
    """Verify number.py was generated correctly."""
    with open('custom_components/midnite/number.py', 'r') as f:
        content = f.read()
    
    # Check for base class
    assert 'class MidniteSolarNumber' in content, "Missing MidniteSolarNumber base class"
    
    # Count number classes (excluding base class)
    number_classes = re.findall(r'class (\w+)Number\(MidniteSolarNumber\)', content)
    print(f"✓ number.py generated with {len(number_classes)} number classes")
    
    # Check for async_setup_entry
    assert 'async def async_setup_entry' in content, "Missing async_setup_entry"
    print("  - Contains async_setup_entry function")


def verify_select_py():
    """Verify select.py was generated correctly."""
    with open('custom_components/midnite/select.py', 'r') as f:
        content = f.read()
    
    # Check for base class
    assert 'class MidniteSolarSelect' in content, "Missing MidniteSolarSelect base class"
    
    # Count select classes (excluding base class)
    select_classes = re.findall(r'class (\w+)Select\(MidniteSolarSelect\)', content)
    print(f"✓ select.py generated with {len(select_classes)} select classes")
    
    # Check for async_setup_entry
    assert 'async def async_setup_entry' in content, "Missing async_setup_entry"
    print("  - Contains async_setup_entry function")


if __name__ == "__main__":
    print("Verifying generated files...\n")
    
    try:
        verify_const_py()
        print()
        verify_sensor_py()
        print()
        verify_number_py()
        print()
        verify_select_py()
        print("\n✓ All verifications passed!")
    except AssertionError as e:
        print(f"\n✗ Verification failed: {e}")
        exit(1)
