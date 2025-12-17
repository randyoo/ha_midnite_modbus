# Quick Reference: DHCP Discovery and Connection Fixes

## Problem Summary
- DHCP auto-discovery not showing "Discovered" cards
- Connection errors: "Connection reset by peer", "Bad file descriptor", timeouts
- Initial connection failures due to short timeout

## Root Causes Identified
1. **Timeout configured AFTER connection attempt** (0.5s default vs needed 5s)
2. **No thread synchronization** - multiple entities accessing same Modbus client concurrently
3. **Poor connection validation** - stale connections not detected
4. **Inconsistent error recovery** - different retry logic in different methods

## Fixes Implemented

### 1. Connection Configuration Timing (CRITICAL)
**File**: `custom_components/midnite/__init__.py`

**Change**: Move timeout/retry BEFORE connect:
```python
# Configure FIRST
client.timeout = 5
client.retries = 3

# THEN connect
connected = await hass.async_add_executor_job(client.connect)
```

### 2. Thread-Safe Connection Management (CRITICAL)
**File**: `custom_components/midnite/__init__.py`

**Changes**:
- Added: `from threading import Lock`
- Added: `self._connection_lock = Lock()` in MidniteAPI.__init__()
- Wrapped all Modbus operations with lock to prevent concurrent access

### 3. Better Connection Validation
**File**: `custom_components/midnite/__init__.py`

**Added method**:
```python
def _is_connection_valid(self) -> bool:
    try:
        return (self.client.connected and 
                hasattr(self.client, 'socket') and 
                self.client.socket is not None)
    except Exception as e:
        _LOGGER.error(f"Error checking connection: {e}")
        return False
```

### 4. Standardized Error Recovery
**File**: `custom_components/midnite/__init__.py`

**Updated `_execute()` method**:
- Uses lock for thread safety
- Exponential backoff (1s, 2s, 3s)
- Force close stale connections
- Consistent retry logic across all operations

### 5. DHCP Discovery Error Handling
**File**: `custom_components/midnite/config_flow.py`

**Updated `async_step_dhcp()` method**:
```python
try:
    # ... existing code ...
    return await self.async_step_user()
except Exception as e:
    _LOGGER.error(f"Error in async_step_dhcp: {e}", exc_info=True)
    return self.async_abort(reason="discovery_failed")
```

## Testing Checklist

### Test DHCP Discovery
- [ ] Restart Home Assistant
- [ ] Connect Midnite Solar device to network
- [ ] Check Settings → Devices & Services for "Discovered" card
- [ ] Click "Configure" and verify setup completes
- [ ] Check logs for `async_step_dhcp` without errors

### Test Connection Reliability
- [ ] Monitor logs during initial connection
- [ ] Verify timeout set to 5s before connect
- [ ] Test multiple entities reading simultaneously
- [ ] Simulate network disruption, verify recovery

### Expected Log Messages (Good)
```
"Setting up Midnite Solar at X.X.X.X:502"
"Configure client timeout settings BEFORE connecting"
"Connection result: True"
"Reading holding registers: address=4100, count=1"
"Function executed successfully, result: ..."
```

### Expected Log Messages (Recovery)
```
"Connection invalid, reconnecting Modbus client..."
"Closing connection after error..."
"Waiting 1 seconds before retry..."
"Waiting 2 seconds before retry..."
"Function executed successfully on attempt 3"
```

## Key Configuration Values

- **Timeout**: 5 seconds (was 0.5s default)
- **Retries**: 3 attempts per operation
- **Backoff**: Exponential (1s, 2s, 3s between retries)
- **Locking**: Thread-safe access to Modbus client

## Files Modified

1. `custom_components/midnite/__init__.py`
   - Added imports: asyncio, Lock
   - Moved timeout/retry before connection
   - Added _connection_lock
   - Added _is_connection_valid() method
   - Updated read_holding_registers() and _execute()

2. `custom_components/midnite/config_flow.py`
   - Wrapped async_step_dhcp() in try-except

## Backward Compatibility

✅ All changes are backward compatible
✅ No API changes to public methods
✅ Existing configurations continue to work
✅ New connection management is transparent

## Expected Improvements

1. **DHCP Discovery**: "Discovered" cards appear reliably
2. **Initial Connection**: Succeeds with slow device response
3. **Concurrent Access**: No race conditions or resets
4. **Error Recovery**: Better reconnection logic
5. **Logging**: More detailed troubleshooting info

## Troubleshooting

### If DHCP Discovery Still Not Working
1. Check logs for `async_step_dhcp` being called
2. Verify MAC address starts with `60:1D:0F`
3. Ensure DHCP is enabled in Home Assistant settings
4. Check for exceptions in config flow

### If Connection Errors Persist
1. Verify timeout is set to 5 seconds before connect
2. Check for "Connection reset by peer" - indicates race condition (should be fixed)
3. Monitor retry attempts with exponential backoff
4. Verify all Modbus operations use the lock

### Common Log Patterns

**Good**:
```
"Configure client timeout settings BEFORE connecting"
"Connection result: True"
"Reading holding registers: address=..., count=..."
```

**Recovery (Expected)**:
```
"Exception during executor job (attempt 1/3): ..."
"Closing connection after error..."
"Waiting 1 seconds before retry..."
"Function executed successfully on attempt 2"
```

**Bad (Should Not Appear)**:
```
"Connection reset by peer"
"Bad file descriptor"
"Connection unexpectedly closed"
```

## Summary

These fixes address the core issues:
- **Timeout too short** → Configured before connection
- **Race conditions** → Thread-safe with Lock
- **Stale connections** → Better validation
- **Inconsistent retries** → Standardized error recovery
- **Discovery crashes** → Proper exception handling

Result: Reliable DHCP discovery and stable Modbus connections.
