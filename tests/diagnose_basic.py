#!/usr/bin/env python3
"""
Basic diagnostic script that doesn't require Home Assistant dependencies.
Tests the core structure and syntax of the config flow.
"""

import sys
import os
import json
from pathlib import Path

# Add custom_components to path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))

print("="*60)
print("BASIC CONFIG FLOW DIAGNOSTIC (No HA Dependencies)")
print("="*60)

# Test 1: Syntax validation
print("\n[1/5] Checking Python syntax...")
try:
    import py_compile
    config_flow_path = Path(__file__).parent.parent / "custom_components" / "midnite" / "config_flow.py"
    py_compile.compile(str(config_flow_path), doraise=True)
    print("✓ Python syntax is valid")
except SyntaxError as e:
    print(f"✗ SYNTAX ERROR at line {e.lineno}: {e.msg}")
    if e.text:
        print(f"  Code: {e.text.strip()}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Compilation failed: {e}")
    sys.exit(1)

# Test 2: Import pymodbus
print("\n[2/5] Checking PyModbus...")
try:
    import pymodbus
    version = pymodbus.__version__
    print(f"✓ PyModbus {version} installed")
except ImportError as e:
    print(f"✗ PyModbus not installed: {e}")
    sys.exit(1)

# Test 3: Check manifest.json
print("\n[3/5] Checking manifest.json...")
try:
    manifest_path = Path(__file__).parent.parent / "custom_components" / "midnite" / "manifest.json"
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    print(f"✓ Domain: {manifest.get('domain')}")
    print(f"✓ Version: {manifest.get('version')}")
    print(f"✓ Documentation: {manifest.get('documentation')}")
    
    if 'dhcp' in manifest and len(manifest['dhcp']) > 0:
        print("✓ DHCP configuration present")
        for config in manifest['dhcp']:
            if 'macaddress' in config:
                print(f"  MAC pattern: {config['macaddress']}")
    else:
        print("⚠ No DHCP configuration found")
except Exception as e:
    print(f"✗ Manifest check failed: {e}")
    sys.exit(1)

# Test 4: Check hub.py syntax
print("\n[4/5] Checking hub.py syntax...")
try:
    import py_compile
    hub_path = Path(__file__).parent.parent / "custom_components" / "midnite" / "hub.py"
    py_compile.compile(str(hub_path), doraise=True)
    print("✓ hub.py syntax is valid")
except SyntaxError as e:
    print(f"✗ SYNTAX ERROR in hub.py at line {e.lineno}: {e.msg}")
    sys.exit(1)
except Exception as e:
    print(f"✗ hub.py compilation failed: {e}")
    sys.exit(1)

# Test 5: Check __init__.py syntax
print("\n[5/5] Checking __init__.py syntax...")
try:
    import py_compile
    init_path = Path(__file__).parent.parent / "custom_components" / "midnite" / "__init__.py"
    py_compile.compile(str(init_path), doraise=True)
    print("✓ __init__.py syntax is valid")
except SyntaxError as e:
    print(f"✗ SYNTAX ERROR in __init__.py at line {e.lineno}: {e.msg}")
    sys.exit(1)
except Exception as e:
    print(f"✗ __init__.py compilation failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("BASIC DIAGNOSTICS PASSED!")
print("="*60)
print("\nNext steps:")
print("1. Run full diagnostics in Home Assistant environment")
print("2. Check Home Assistant logs for autodiscovery errors")
print("3. Test manual connection to the device")
sys.exit(0)
