# Quick Start: Running Diagnostic Tests

## How to Run the Tests

The diagnostic tests are now located in `custom_components/midnite/tests/` and can be run from **any directory**.

### Basic Diagnostic (No Home Assistant Dependencies)

```bash
python3 custom_components/midnite/tests/diagnose_basic.py
```

This will check:
- ✓ Python syntax in all component files
- ✓ PyModbus installation
- ✓ Manifest.json configuration
- ✓ DHCP settings

### Comprehensive Diagnostic (Requires Home Assistant Environment)

```bash
python3 custom_components/midnite/tests/diagnose_config_flow.py
```

This performs 10 comprehensive checks including:
- All imports and dependencies
- Config flow class structure
- Modbus API compatibility
- Connection logic testing
- DHCP discovery specific code paths

### Individual Test Suites

```bash
# General config flow validation
python3 custom_components/midnite/tests/test_config_flow_validation.py

# DHCP discovery specific tests
python3 custom_components/midnite/tests/test_dhcp_discovery_specific.py
```

## Where to Run the Tests

You can run these from **any directory** as long as:
1. You're in your Home Assistant config directory (where `custom_components` lives)
2. The Midnite Solar integration is installed in `custom_components/midnite/`

### Example from different directories:

```bash
# From HA config directory
cd /config
python3 custom_components/midnite/tests/diagnose_basic.py

# From anywhere (as long as paths are correct)
python3 /config/custom_components/midnite/tests/diagnose_basic.py

# From tests directory itself
cd custom_components/midnite/tests
python3 ./diagnose_basic.py
```

## What the Tests Check

### Basic Diagnostics (Always Works)
- Python syntax validation (catches indentation errors)
- PyModbus version compatibility
- Manifest.json structure and DHCP configuration
- File existence and readability

### Full Diagnostics (Requires HA Environment)
- All required imports work correctly
- Config flow class is properly defined
- DHCP discovery logic is sound
- Connection test logic functions properly
- Modbus API signature is correct
- Voluptuous schemas can be created

## Interpreting Results

### If Tests Pass ✅
The code structure is correct. The autodiscovery issue is likely:
- Network connectivity problems
- Device not responding on the network
- DHCP service not properly configured in Home Assistant
- Firewall settings blocking connections

### If Tests Fail ❌
The specific error message will tell you exactly what needs to be fixed:
- **Syntax errors:** Fix indentation in the file mentioned
- **Import errors:** Install missing dependencies
- **Class errors:** Add missing methods/attributes
- **Config errors:** Update manifest.json
- **Version issues:** Upgrade/downgrade PyModbus

## Troubleshooting

### "No such file or directory" Error
If you get path errors, make sure:
1. You're in your Home Assistant config directory
2. The Midnite Solar integration is installed at `custom_components/midnite/`
3. The test files are in `custom_components/midnite/tests/`

### Missing Dependencies
Install required packages:
```bash
pip install "pymodbus>=3.6.0,<4.0.0"
pip install voluptuous
```

## Next Steps After Running Tests

1. **If all tests pass:** Focus on network/device connectivity issues
2. **If tests fail:** Fix the specific issues identified by the error messages
3. **Check Home Assistant logs** for autodiscovery errors
4. **Test manual connection** to verify device responsiveness
