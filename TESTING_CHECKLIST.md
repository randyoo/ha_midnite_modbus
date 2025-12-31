# Testing Checklist

## ✓ Completed Tasks
- [x] Reverted to commit 66ca846 (last functional version)
- [x] Fixed indentation issues in config_flow.py
- [x] Added targeted debug logging for DHCP discovery
- [x] Added flow state logging for async_step_user
- [x] Verified file compiles without errors
- [x] Created comprehensive documentation

## Testing Tasks to Complete

### Basic Functionality Tests
- [ ] Verify config_flow.py compiles: `python -m py_compile custom_components/midnite/config_flow.py`
- [ ] Check for syntax errors in all Python files
- [ ] Verify imports work correctly

### Manual Configuration Test
- [ ] Go to Settings > Devices & Services
- [ ] Click "Add Integration"
- [ ] Search for "Midnite Solar"
- [ ] Fill out form with valid device IP and port
- [ ] Submit and verify config entry is created
- [ ] Check logs for: `✓ Called from MANUAL entry`
- [ ] Check logs for: `SHOWING MANUAL CONFIGURATION FORM`

### DHCP Discovery Test
- [ ] Ensure device is broadcasting DHCP packets
- [ ] Restart Home Assistant (or restart DHCP integration)
- [ ] Watch logs for: `DHCP DISCOVERY TRIGGERED!`
- [ ] Verify MAC address and IP are logged correctly
- [ ] Check for existing entries count in logs
- [ ] Verify confirmation form is shown to user
- [ ] Check logs for: `SHOWING DISCOVERY CONFIRMATION FORM`

### Duplicate Entry Test
- [ ] Attempt to add the same device twice (via DHCP)
- [ ] Verify second attempt is aborted as duplicate
- [ ] Check logs for `_abort_if_unique_id_configured` behavior
- [ ] Verify unique ID is based on formatted MAC address

### Connection Validation Test
- [ ] Enter invalid IP address in manual config
- [ ] Submit form and verify error is shown
- [ ] Check logs for: `cannot_connect` or `cannot_read`
- [ ] Test with valid device to ensure connection succeeds

### Error Handling Tests
- [ ] Verify no "reached end without returning" errors
- [ ] Check for proper exception handling in all code paths
- [ ] Ensure all functions return valid ConfigFlowResult objects
- [ ] Verify error messages are user-friendly

## Log Verification Checklist

### Expected Log Messages
- [ ] `DHCP DISCOVERY TRIGGERED!` when device is discovered
- [ ] Device IP and MAC address logged correctly
- [ ] Hostname (if available) logged
- [ ] Existing config entries count shown
- [ ] `async_step_user CALLED` when flow starts
- [ ] `user_input: None` on first call
- [ ] Context, Flow ID, and Handler logged
- [ ] Clear indication of discovery vs manual entry
- [ ] Form display messages (`SHOWING ... FORM`)

### Error Logs to Watch For
- [x] No indentation errors
- [x] No "reached end without returning" errors
- [ ] No KeyError exceptions
- [ ] No AttributeError exceptions
- [ ] No connection timeout errors (unless expected)
- [ ] No unhandled exceptions

## Debugging Information to Capture

If tests fail, capture:
1. **Complete log output** from the moment you trigger the config flow
2. **Exact error messages** with stack traces
3. **Which code path was taken** (discovery vs manual)
4. **User input values** (if any)
5. **Existing config entries** (from logs)
6. **Flow state information** (context, ID, handler)

## Success Criteria

The integration is working correctly when:
- ✓ Manual configuration works without errors
- ✓ DHCP discovery triggers and shows confirmation form
- ✓ Duplicate entries are properly handled
- ✓ Connection validation works correctly
- ✓ All code paths return valid results
- ✓ No unhandled exceptions occur
- ✓ Logs show clear progression through the config flow

## Troubleshooting Tips

### If DHCP Discovery Doesn't Work:
1. Verify device is on same network as Home Assistant
2. Check firewall settings (UDP ports 67/68)
3. Restart DHCP integration in Home Assistant
4. Reboot both the device and Home Assistant
5. Check if other devices are being discovered

### If Manual Configuration Fails:
1. Verify IP address is correct
2. Check port number (default: 502)
3. Test connection with modbus tools like `mbpoll`
4. Verify device is powered on and accessible
5. Check for network connectivity issues

### If Getting "Duplicate" Errors:
1. Check existing config entries in logs
2. Verify MAC address formatting
3. Remove old config entry if no longer needed
4. Restart Home Assistant after removing old entry
