#!/usr/bin/env python3
"""
Test to verify the config flow changes for scan_interval configuration.
"""

import sys
sys.path.insert(0, '/Users/randy/midnite')

from custom_components.midnite.const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from custom_components.midnite.config_flow import MidniteSolarConfigFlow

print("Test: Config Flow Scan Interval Configuration")
print("=" * 60)

# Test 1: Verify constants are properly imported
print("\nTest 1: Constants Import")
print(f"✓ CONF_SCAN_INTERVAL = '{CONF_SCAN_INTERVAL}'")
print(f"✓ DEFAULT_SCAN_INTERVAL = {DEFAULT_SCAN_INTERVAL}")

# Test 2: Verify config flow imports constants
print("\nTest 2: Config Flow Imports")
try:
    from custom_components.midnite.config_flow import (
        CONF_SCAN_INTERVAL as CF_CONF_SCAN_INTERVAL,
        DEFAULT_SCAN_INTERVAL as CF_DEFAULT_SCAN_INTERVAL
    )
    print(f"✓ Config flow has CONF_SCAN_INTERVAL = '{CF_CONF_SCAN_INTERVAL}'")
    print(f"✓ Config flow has DEFAULT_SCAN_INTERVAL = {CF_DEFAULT_SCAN_INTERVAL}")
    assert CF_CONF_SCAN_INTERVAL == "scan_interval"
    assert CF_DEFAULT_SCAN_INTERVAL == 15
    print("✓ Constants match expected values")
except ImportError as e:
    print(f"✗ Failed to import constants from config_flow: {e}")
    sys.exit(1)

# Test 3: Verify the async_step_options method exists
print("\nTest 3: Options Flow Method")
try:
    assert hasattr(MidniteSolarConfigFlow, 'async_step_options')
    print("✓ async_step_options method exists in MidniteSolarConfigFlow")
except AssertionError:
    print("✗ async_step_options method not found")
    sys.exit(1)

# Test 4: Verify __init__.py has update_listener
print("\nTest 4: Update Listener Function")
try:
    from custom_components.midnite import update_listener
    print("✓ update_listener function exists in __init__.py")
except ImportError as e:
    print(f"✗ Failed to import update_listener: {e}")
    sys.exit(1)

# Test 5: Verify async_setup_entry registers the listener
print("\nTest 5: Setup Entry Registration")
try:
    from custom_components.midnite import async_setup_entry
    import inspect
    source = inspect.getsource(async_setup_entry)
    if "add_update_listener" in source and "update_listener" in source:
        print("✓ async_setup_entry registers update_listener")
    else:
        print("✗ async_setup_entry doesn't register update_listener")
        sys.exit(1)
except Exception as e:
    print(f"✗ Error checking async_setup_entry: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("All tests passed! ✓")
print("\nSummary of changes:")
print("- Added scan_interval configuration option to config flow")
print("- Scan interval stored in config entry options")
print("- Options can be updated after initial setup via UI")
print("- Integration reloads when options are changed")
