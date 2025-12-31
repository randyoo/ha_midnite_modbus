# Midnite Solar Config Flow Diagnostic Tests

This directory contains diagnostic tools to help identify issues with the Midnite Solar integration's config flow and autodiscovery functionality.

## Running the Diagnostics

### Option 1: Run the Comprehensive Diagnostic Script

```bash
python3 tests/diagnose_config_flow.py
```

This script performs 10 comprehensive checks:
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

### Option 2: Run Individual Test Files

```bash
# Run general config flow validation tests
python3 tests/test_config_flow_validation.py

# Run DHCP discovery specific tests
python3 tests/test_dhcp_discovery_specific.py
```

## What These Tests Check

The diagnostic tools verify:
- ✓ Python syntax is valid (no indentation errors)
- ✓ All required imports work correctly
- ✓ Config flow class is properly defined with all required methods
- ✓ Manifest.json has correct DHCP configuration
- ✓ PyModbus version is compatible (3.x)
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
