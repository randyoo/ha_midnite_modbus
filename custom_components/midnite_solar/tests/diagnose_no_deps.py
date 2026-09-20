#!/usr/bin/env python3
"""
Zero-dependency diagnostic script.
Tests the core structure without requiring any external packages.
This will work from CLI even without pymodbus installed.
"""

import sys
from pathlib import Path

# Find the component directory relative to this script
script_dir = Path(__file__).parent  # tests directory
component_dir = script_dir.parent  # midnite directory

print("="*60)
print("ZERO-DEPENDENCY CONFIG FLOW DIAGNOSTIC")
print("="*60)

# Test 1: File existence
print("\n[1/4] Checking file existence...")
required_files = [
    "config_flow.py",
    "hub.py", 
    "__init__.py",
    "manifest.json"
]

all_exist = True
for filename in required_files:
    filepath = component_dir / filename
    if filepath.exists():
        print(f"✓ {filename} exists")
    else:
        print(f"✗ {filename} MISSING")
        all_exist = False

if not all_exist:
    sys.exit(1)

# Test 2: Python syntax validation
print("\n[2/4] Checking Python syntax...")
try:
    import py_compile
    for filename in ["config_flow.py", "hub.py", "__init__.py"]:
        filepath = component_dir / filename
        try:
            py_compile.compile(str(filepath), doraise=True)
            print(f"✓ {filename} syntax is valid")
        except SyntaxError as e:
            print(f"✗ SYNTAX ERROR in {filename} at line {e.lineno}: {e.msg}")
            if e.text:
                print(f"  Code: {e.text.strip()}")
            sys.exit(1)
except ImportError:
    print("⚠ py_compile not available, skipping syntax check")

# Test 3: Manifest.json structure
print("\n[3/4] Checking manifest.json...")
try:
    import json
    manifest_path = component_dir / "manifest.json"
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    required_fields = ['domain', 'name', 'version']
    for field in required_fields:
        if field in manifest:
            print(f"✓ {field}: {manifest[field]}")
        else:
            print(f"✗ Missing required field: {field}")
            sys.exit(1)
    
    if 'dhcp' in manifest and len(manifest['dhcp']) > 0:
        print("✓ DHCP configuration present")
        for i, config in enumerate(manifest['dhcp']):
            if 'macaddress' in config:
                print(f"  MAC pattern {i+1}: {config['macaddress']}")
    else:
        print("⚠ No DHCP configuration found")
        
except json.JSONDecodeError as e:
    print(f"✗ Invalid JSON in manifest.json: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Manifest check failed: {e}")
    sys.exit(1)

# Test 4: Basic Python imports (no external dependencies)
print("\n[4/4] Checking basic Python imports...")
basic_imports = [
    ('os', 'OS module'),
    ('sys', 'System module'),
    ('json', 'JSON module'),
    ('logging', 'Logging module'),
]

for import_name, description in basic_imports:
    try:
        __import__(import_name)
        print(f"✓ {description}")
    except ImportError as e:
        print(f"✗ Missing: {description} - {e}")
        sys.exit(1)

print("\n" + "="*60)
print("ZERO-DEPENDENCY DIAGNOSTICS PASSED!")
print("="*60)
print("\nNext steps:")
print("1. If you need to test with pymodbus, run from Home Assistant's Python environment")
print("2. Check Home Assistant logs for autodiscovery errors")
print("3. Test manual connection to verify device responsiveness")
sys.exit(0)
