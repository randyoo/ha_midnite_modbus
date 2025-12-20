#!/usr/bin/env python3
"""
Validation script to check the code structure changes for scan_interval configuration.
This doesn't require Home Assistant to be installed.
"""

import os
import re

def read_file(path):
    """Read file content."""
    with open(path, 'r') as f:
        return f.read()

def check_constants():
    """Check that constants are defined correctly."""
    print("Checking constants.py...")
    const_content = read_file('custom_components/midnite/const.py')
    
    checks = [
        ('CONF_SCAN_INTERVAL', 'scan_interval'),
        ('DEFAULT_SCAN_INTERVAL', '15'),
    ]
    
    for var_name, expected_value in checks:
        pattern = rf'{var_name}\s*=\s*["\']?{expected_value}["\']?'
        if re.search(pattern, const_content):
            print(f"  ✓ {var_name} = {expected_value}")
        else:
            print(f"  ✗ {var_name} not found or incorrect value")
            return False
    
    return True

def check_config_flow():
    """Check that config_flow.py has the necessary changes."""
    print("\nChecking config_flow.py...")
    config_content = read_file('custom_components/midnite/config_flow.py')
    
    checks = [
        (r'from \.const import.*DEFAULT_SCAN_INTERVAL.*CONF_SCAN_INTERVAL', 'Imports constants'),
        (r'vol\.Optional\(CONF_SCAN_INTERVAL', 'Has scan_interval in form'),
        (r'async def async_step_options', 'Has options flow method'),
        (r'entry_options\[CONF_SCAN_INTERVAL\]', 'Stores scan_interval in options'),
    ]
    
    for pattern, description in checks:
        if re.search(pattern, config_content):
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            return False
    
    return True

def check_init():
    """Check that __init__.py has the necessary changes."""
    print("\nChecking __init__.py...")
    init_content = read_file('custom_components/midnite/__init__.py')
    
    checks = [
        (r'entry\.options\.get\("scan_interval"', 'Reads scan_interval from options'),
        (r'entry\.add_update_listener\(update_listener\)', 'Registers update listener'),
        (r'async def update_listener', 'Has update_listener function'),
    ]
    
    for pattern, description in checks:
        if re.search(pattern, init_content):
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            return False
    
    return True

def main():
    """Run all validation checks."""
    print("=" * 70)
    print("VALIDATING SCAN_INTERVAL CONFIGURATION CHANGES")
    print("=" * 70)
    
    results = []
    results.append(("Constants", check_constants()))
    results.append(("Config Flow", check_config_flow()))
    results.append(("Init File", check_init()))
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n✓ ALL VALIDATION CHECKS PASSED!")
        print("\nChanges implemented:")
        print("1. Added CONF_SCAN_INTERVAL and DEFAULT_SCAN_INTERVAL to const.py")
        print("2. Updated config_flow.py to include scan_interval in configuration forms")
        print("3. Added async_step_options method for updating options after setup")
        print("4. Modified __init__.py to read scan_interval from entry.options")
        print("5. Added update_listener to reload integration when options change")
        return 0
    else:
        print("\n✗ SOME VALIDATION CHECKS FAILED!")
        return 1

if __name__ == "__main__":
    exit(main())
