#!/usr/bin/env python3
"""
Standalone test for DHCP discovery configuration.
Tests the manifest and code structure without requiring Home Assistant.
"""

import json
import sys

def test_manifest():
    """Test that manifest.json has registered_devices set to true."""
    print("=" * 60)
    print("TEST 1: Manifest Configuration")
    print("=" * 60)
    
    try:
        with open('custom_components/midnite/manifest.json', 'r') as f:
            manifest = json.load(f)
        
        # Check registered_devices
        if 'registered_devices' not in manifest:
            print("✗ FAIL: registered_devices not found in manifest")
            return False
        
        if manifest['registered_devices'] != True:
            print(f"✗ FAIL: registered_devices is {manifest['registered_devices']}, should be true")
            return False
        
        print("✓ PASS: registered_devices = true")
        
        # Check DHCP configuration
        if 'dhcp' not in manifest:
            print("✗ FAIL: DHCP configuration not found")
            return False
        
        dhcp_config = manifest['dhcp'][0]
        if 'macaddress' not in dhcp_config:
            print("✗ FAIL: MAC address pattern not configured")
            return False
        
        print(f"✓ PASS: DHCP discovery configured with MAC pattern: {dhcp_config['macaddress']}")
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Error reading manifest: {e}")
        return False

def test_translations():
    """Test that translations include required error messages."""
    print("\n" + "=" * 60)
    print("TEST 2: Translation Messages")
    print("=" * 60)
    
    try:
        with open('custom_components/midnite/translations/en.json', 'r') as f:
            translations = json.load(f)
        
        errors = translations.get('config', {}).get('error', {})
        aborts = translations.get('config', {}).get('abort', {})
        
        required_errors = ['cannot_set_unique_id']
        for error in required_errors:
            if error not in errors:
                print(f"✗ FAIL: Error message '{error}' not found")
                return False
            print(f"✓ PASS: Error message '{error}' present")
        
        required_aborts = ['discovery_failed', 'cannot_set_unique_id']
        for abort in required_aborts:
            if abort not in aborts:
                print(f"✗ FAIL: Abort reason '{abort}' not found")
                return False
            print(f"✓ PASS: Abort reason '{abort}' present")
        
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Error reading translations: {e}")
        return False

def test_config_flow():
    """Test that config_flow.py has the DHCP method."""
    print("\n" + "=" * 60)
    print("TEST 3: Config Flow DHCP Method")
    print("=" * 60)
    
    try:
        with open('custom_components/midnite/config_flow.py', 'r') as f:
            content = f.read()
        
        # Check for async_step_dhcp method
        if 'async def async_step_dhcp' not in content:
            print("✗ FAIL: async_step_dhcp method not found")
            return False
        print("✓ PASS: async_step_dhcp method exists")
        
        # Check for unique ID setting with MAC address
        if 'format_mac' not in content:
            print("✗ FAIL: MAC address formatting not found")
            return False
        print("✓ PASS: MAC address formatting present")
        
        # Check for IP update logic
        if '_abort_if_unique_id_configured' not in content:
            print("✗ FAIL: Unique ID configuration check not found")
            return False
        print("✓ PASS: Unique ID configuration check present")
        
        # Check for proper abort handling
        if 'updates={CONF_HOST:' not in content:
            print("✗ FAIL: IP address update logic not found")
            return False
        print("✓ PASS: IP address update logic present")
        
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Error reading config_flow.py: {e}")
        return False

def test_hostname_write_fix():
    """Test that hostname write logic uses little-endian."""
    print("\n" + "=" * 60)
    print("TEST 4: Hostname Write Fix (Little-Endian)")
    print("=" * 60)
    
    try:
        with open('custom_components/midnite/text.py', 'r') as f:
            content = f.read()
        
        # Check for correct little-endian logic
        if "ord(char1) | (ord(char2) << 8)" not in content:
            print("✗ FAIL: Correct little-endian write logic not found")
            return False
        print("✓ PASS: Little-endian write logic present")
        
        # Check that old big-endian logic is gone (or at least not in the write method)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'register_value' in line and '(ord(char1) << 8)' in line:
                # Check if this is in a comment
                prev_lines = '\n'.join(lines[max(0, i-5):i])
                if '"' not in prev_lines and "#" not in prev_lines or '#' in prev_lines[-10:]:
                    print(f"✗ FAIL: Old big-endian logic still present at line {i+1}")
                    return False
        
        print("✓ PASS: No old big-endian logic found")
        
        # Check for documentation comment
        if "little-endian" not in content.lower():
            print("⚠ WARNING: No documentation about endianness found")
        else:
            print("✓ PASS: Documentation about little-endian present")
        
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Error reading text.py: {e}")
        return False

def main():
    """Run all tests."""
    print("\nMidnite Solar Integration - Standalone Tests")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Manifest", test_manifest()))
    results.append(("Translations", test_translations()))
    results.append(("Config Flow", test_config_flow()))
    results.append(("Hostname Fix", test_hostname_write_fix()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
