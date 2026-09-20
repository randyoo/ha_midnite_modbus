# Midnite Solar Config Flow Diagnostic Tests

This directory contains diagnostic tools to help identify issues with the Midnite Solar integration's config flow and autodiscovery functionality.

## Running the Diagnostics

### Option 1: Zero-Dependency Diagnostic (Recommended for CLI)

```bash
python3 custom_components/midnite/tests/diagnose_no_deps.py
```

**This is the best option if you're running from command line (CLI)** because it doesn't require any external packages. It checks:
- File existence and structure
- Python syntax (catches indentation errors)
- Manifest.json configuration
- Basic Python imports

### Option 2: Basic Diagnostic Script

```bash
python3 custom_components/midnite/tests/diagnose_basic.py
```

This script performs basic checks that only require PyModbus:
1. Python syntax validation
2. PyModbus version check
3. Manifest configuration validation
4. Hub and __init__.py syntax validation

### Option 3: Comprehensive Diagnostic Script

```bash
python3 custom_components/midnite/tests/diagnose_config_flow.py
```

This script performs 10 comprehensive checks (requires Home Assistant environment):
1. Python syntax validation
2. Import validation
3. Config flow class validation
4. Manifest configuration validation
5. PyModbus version validation
6. Modbus API validation
7. Hub connection logic validation
8. DHCP discovery logic validation
9. Connection test logic validation
10. Voluptuous schema validation

### Option 4: Run Individual Test Files

```bash
# Run general config flow validation tests
python3 custom_components/midnite/tests/test_config_flow_validation.py

# Run DHCP discovery specific tests
python3 custom_components/midnite/tests/test_dhcp_discovery_specific.py
```

## What These Tests Check

### Zero-Dependency Tests (Option 1)
- ✓ File existence and structure
- ✓ Python syntax validation (catches indentation errors)
- ✓ Manifest.json configuration including DHCP settings
- ✓ Basic Python imports (os, sys, json, logging)

### Basic Diagnostic Tests (Option 2)
- ✓ All of the above plus:
- ✓ PyModbus installation and version compatibility

### Comprehensive Diagnostic Tests (Options 3 & 4)
- ✓ All of the above plus:
- ✓ Config flow class is properly defined with all required methods
- ✓ Modbus API signature is correct
- ✓ Hub connection logic works
- ✓ DHCP discovery logic is sound
- ✓ Connection test logic functions properly
- ✓ Voluptuous schemas can be created and validated

## If All Tests Pass

If all diagnostic tests pass but autodiscovery still fails, the issue is likely:
- **Network connectivity** - The device may not be reachable on the network
- **Device not responding** - The Modbus TCP server may not be running or responding
- **DHCP service configuration** - Home Assistant's DHCP discovery may need to be enabled/configured
- **Firewall settings** - Network firewalls may be blocking the connection

## If Tests Fail

If any tests fail, they will indicate:
- Syntax errors (indentation issues)
- Missing imports or dependencies
- Incorrect class definitions
- Configuration problems in manifest.json
- Version compatibility issues

These failures can help pinpoint exactly where the problem lies without modifying the actual config_flow.py file.
