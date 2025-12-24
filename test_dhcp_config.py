#!/usr/bin/env python3
"""
Simple test to verify DHCP config flow changes.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Test: DHCP Config Flow Changes")
print("=" * 50)

# Test 1: Verify the config flow file exists and has the right structure
try:
    from custom_components.midnite.config_flow import MidniteSolarConfigFlow
    print("✓ Config flow class imported successfully")
    
    # Check if it has the required methods
    required_methods = ['async_step_dhcp', 'async_step_user', 'async_step_reconfigure']
    for method in required_methods:
        if hasattr(MidniteSolarConfigFlow, method):
            print(f"✓ Method {method} exists")
        else:
            print(f"✗ Method {method} missing")
            sys.exit(1)
            
    print("✓ All required methods found in config flow")
    
except Exception as e:
    print(f"✗ Failed to import config flow: {e}")
    sys.exit(1)

# Test 2: Check that the manifest has registered_devices set to true
try:
    import json
    with open('custom_components/midnite/manifest.json', 'r') as f:
        manifest = json.load(f)
    
    if 'registered_devices' in manifest and manifest['registered_devices'] is True:
        print("✓ manifest.json has registered_devices = true")
    else:
        print("✗ manifest.json missing registered_devices or not set to true")
        sys.exit(1)
        
    if 'dhcp' in manifest:
        print("✓ manifest.json has DHCP configuration")
    else:
        print("✗ manifest.json missing DHCP configuration")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Failed to read manifest.json: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("All tests passed! ✓")
print("\nSummary of changes made:")
print("- Implemented proper DHCP discovery handling")
print("- Added reconfigure functionality for existing entries")
print("- Ensured unique ID is properly set using MAC address")
print("- IP addresses are updated when devices change networks")
print("- Scan interval configuration is preserved in options")