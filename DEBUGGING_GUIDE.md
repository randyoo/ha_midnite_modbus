# Debugging Guide for Autodiscovery Issues

## Overview
This guide provides step-by-step instructions for debugging autodiscovery issues in the Midnite Solar integration.

## Current State
- Reverted to commit `66ca846` - Last known functional version
- Added enhanced logging to track DHCP discovery and config flow execution
- Clean, properly indented code without "reached end without returning" errors

## Debugging Steps

### 1. Enable Debug Logging
Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.midnite: debug
    homeassistant.components.dhcp: debug
```

Then restart Home Assistant.

### 2. Verify DHCP Discovery is Working
Check the logs for these key messages:

**Expected DHCP Discovery Logs:**
```
========================================
DHCP DISCOVERY TRIGGERED!
Device IP: X.X.X.X
MAC Address: XX:XX:XX:XX:XX:XX
Hostname: (if available)
========================================
Existing config entries count: N
  - Entry ID: ..., Data: {...}
```

**If you don't see these logs:**
- DHCP discovery is not being triggered
- Check your network settings
- Verify the device is broadcasting DHCP packets
- Ensure Home Assistant's DHCP integration is enabled

### 3. Verify Config Flow Execution
After DHCP discovery, look for:

**Expected async_step_user Logs:**
```
========================================
async_step_user CALLED
user_input: None
Context: {...}
Flow ID: ...
Handler: ...
✓ Called from DHCP DISCOVERY
  MAC: XX:XX:XX:XX:XX:XX
  IP: X.X.X.X
========================================
```

**Then look for form display:**
```
SHOWING DISCOVERY CONFIRMATION FORM
Device IP: X.X.X.X
User should see a 'Discovered' card in UI
```

### 4. Check for Errors
Look for any ERROR or EXCEPTION messages in the logs, especially:
- `KeyError` exceptions
- `AttributeError` exceptions  
- "reached end without returning" errors
- Connection timeout errors

### 5. Test Manual Configuration
If autodiscovery isn't working, try manual configuration:
1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Midnite Solar"
4. Enter the device IP and port manually

Check logs for:
```
✓ Called from MANUAL entry
SHOWING MANUAL CONFIGURATION FORM
```

## Common Issues and Solutions

### Issue 1: DHCP Discovery Not Triggered
**Symptoms:** No "DHCP DISCOVERY TRIGGERED!" logs

**Solutions:**
- Verify device is on the same network as Home Assistant
- Check firewall settings - ensure UDP port 67/68 are open
- Restart the DHCP integration in Home Assistant
- Try rebooting both the device and Home Assistant

### Issue 2: Config Flow Returns None
**Symptoms:** Integration doesn't appear, no error shown

**Solutions:**
- Check for indentation errors (already fixed in this version)
- Ensure all code paths return a valid result
- Look for "CRITICAL ERROR" messages in logs

### Issue 3: Duplicate Entry Issues
**Symptoms:** Can't add device, gets aborted as duplicate

**Solutions:**
- Check the unique ID logic (MAC address formatting)
- Verify `_abort_if_unique_id_configured` is working correctly
- Look for logs about existing entries

## Logging Reference

### Key Log Messages

| Message | Meaning |
|---------|---------|
| `DHCP DISCOVERY TRIGGERED!` | DHCP packet received |
| `async_step_user CALLED` | Config flow initiated |
| `Called from DHCP DISCOVERY` | Flow triggered by discovery |
| `Called from MANUAL entry` | Flow triggered manually |
| `SHOWING DISCOVERY CONFIRMATION FORM` | User should see confirmation dialog |
| `SHOWING MANUAL CONFIGURATION FORM` | User should see full config form |

### Debug Information Logged

1. **Discovery Info:**
   - Device IP
   - MAC address (formatted)
   - Hostname (if available)

2. **Flow State:**
   - Context dictionary
   - Flow ID
   - Handler name

3. **Existing Entries:**
   - Count of existing config entries
   - Entry IDs and data for each

## Next Steps

If you identify an issue:
1. Document the exact log output
2. Note any error messages
3. Check which code path is being taken
4. Report findings with specific log excerpts

This will help pinpoint exactly where the autodiscovery process is failing.
