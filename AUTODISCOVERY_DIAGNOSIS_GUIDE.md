# Autodiscovery Issue Diagnosis Guide

## Current Situation Summary

**Working Commit:** 66ca846 (Add auxiliary function selectors and wind power curve numbers)
- Autodiscovery badge appears but fails to complete successfully
- After autodiscovery failure, manual device addition also fails
- Previous attempts to fix introduced indentation problems in `config_flow.py`

**Root Cause Hypothesis:** The issue is likely NOT an indentation problem in the current code (commit 66ca846), but rather:
1. A logic error in the config flow
2. A connection/test timing issue
3. A device response handling problem
4. A network/device availability issue at runtime

## Diagnostic Tools Created

We have created comprehensive diagnostic tools that **do not modify** `config_flow.py` and can help identify the exact issue:

### 1. Quick Diagnostic Script
```bash
python3 tests/diagnose_config_flow.py
```

Performs 10 validation checks covering:
- Python syntax (catches indentation errors)
- All imports and dependencies
- Config flow class structure
- DHCP configuration in manifest.json
- PyModbus version compatibility
- Modbus API correctness
- Connection logic
- DHCP discovery specific code paths

### 2. Detailed Test Suites
```bash
# General config flow validation
python3 tests/test_config_flow_validation.py

# DHCP discovery specific tests
python3 tests/test_dhcp_discovery_specific.py
```

## Recommended Diagnostic Process

### Step 1: Verify Current Code State
```bash
cd /Users/randy/midnite
git log --oneline -5
git status
python3 -m py_compile custom_components/midnite/config_flow.py
```

**Expected:** Syntax compilation should succeed (no errors)

### Step 2: Run Comprehensive Diagnostic
```bash
python3 tests/diagnose_config_flow.py
```

**Interpret Results:**
- ✅ **All checks pass:** Code structure is correct. Issue is runtime/network related.
- ❌ **Any check fails:** Specific error will indicate what needs fixing.

### Step 3: Check Home Assistant Logs

Look for specific error messages during autodiscovery:
```bash
# In Home Assistant logs, search for:
- "DHCP DISCOVERY TRIGGERED!"
- "async_step_user CALLED"
- "cannot_connect"
- "cannot_read"
- "unknown"
- Exception stack traces
```

### Step 4: Test Manual Connection

Try connecting manually to verify device responsiveness:
```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('DEVICE_IP', port=502)
connected = client.connect()
print(f"Connected: {connected}")

if connected:
    result = client.read_holding_registers(address=4100, count=1)
    print(f"Read successful: {not result.isError()}")
    if not result.isError():
        print(f"Register value: {result.registers}")

client.close()
```

## Common Autodiscovery Failure Points

### 1. Connection Test Logic (Line ~120 in config_flow.py)
```python
# Test connection
client = ModbusTcpClient(user_input[CONF_HOST], port=user_input[CONF_PORT])
try:
    connected = await self.hass.async_add_executor_job(client.connect)
    if not connected:
        errors["base"] = "cannot_connect"
    else:
        # Try to read a register to verify communication
        result = await self.hass.async_add_executor_job(
            lambda: client.read_holding_registers(address=4100, count=1)
        )
        if result.isError():
            errors["base"] = "cannot_read"
    
    client.close()
except Exception as ex:
    _LOGGER.exception("Unexpected exception during connection test")
    errors["base"] = "unknown"
```

**Potential Issues:**
- Device not responding to connection attempts
- Register 4100 not readable or returns error
- Connection times out
- Exception during read operation

### 2. DHCP Discovery Flow (Line ~35 in config_flow.py)
```python
async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
    """Handle DHCP discovery."""
    # ... logging and MAC formatting ...
    
    await self.async_set_unique_id(formatted_mac, raise_on_progress=False)
    
    self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.ip})
    
    self.discovery_info = discovery_info
    self.context["title_placeholders"] = {"ip": discovery_info.ip}
    
    return self.async_show_form(
        step_id="user",
        description_placeholders={"ip": discovery_info.ip},
    )
```

**Potential Issues:**
- MAC address formatting incorrect
- Device already configured with different IP
- Form not displaying properly in UI

### 3. User Step with Discovery Context (Line ~65 in config_flow.py)
```python
async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
    """Handle the initial step (manual or DHCP discovery)."""
    # ... logging ...
    
    discovered = hasattr(self, 'discovery_info') and self.discovery_info is not None
    if discovered:
        # For DHCP discovery, pre-fill the host from discovery info
        if CONF_HOST not in user_input:
            user_input[CONF_HOST] = self.discovery_info.ip
```

**Potential Issues:**
- `user_input` is None when it shouldn't be
- Host not being pre-filled correctly from discovery
- Form validation failing silently

## Next Steps Based on Findings

### If Diagnostic Tests Pass ✅

The code is structurally sound. Focus on:
1. **Network connectivity** - Can you ping the device?
2. **Modbus responsiveness** - Does the device respond to manual connection tests?
3. **Home Assistant DHCP service** - Is it properly configured and running?
4. **Firewall settings** - Are ports being blocked?
5. **Device state** - Is the Modbus TCP server running on the device?

### If Diagnostic Tests Fail ❌

The specific failure will indicate:
- **Syntax errors:** Fix indentation in `config_flow.py`
- **Import errors:** Install missing dependencies
- **Class errors:** Add missing methods/attributes
- **Config errors:** Update manifest.json
- **Version issues:** Upgrade/downgrade PyModbus

### If Connection Tests Fail

Check:
1. Device IP address is correct
2. Port 502 (or custom port) is open
3. Register 4100 is readable on the device
4. No network firewalls blocking the connection
5. Device firmware supports Modbus TCP

## Prevention of Future Issues

1. **Always run diagnostics before making changes**
2. **Test with mocks first** to avoid runtime issues
3. **Verify syntax** after any edits: `python3 -m py_compile custom_components/midnite/config_flow.py`
4. **Use version control** and commit frequently with clear messages
5. **Review logs carefully** for specific error messages

## Files Created for Diagnosis

```
tests/
├── diagnose_config_flow.py          # Comprehensive diagnostic script
├── test_config_flow_validation.py   # General config flow tests
├── test_dhcp_discovery_specific.py  # DHCP-specific tests
└── README.md                        # How to use the tests

DIAGNOSTIC_TOOLS_SUMMARY.md         # Overview of diagnostic tools
AUTODISCOVERY_DIAGNOSIS_GUIDE.md    # This guide
```

## Running the Diagnostics Now

```bash
cd /Users/randy/midnite
python3 tests/diagnose_config_flow.py
```

This will provide immediate feedback on whether the code structure is sound or if there are specific issues to address.
