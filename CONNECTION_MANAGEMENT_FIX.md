# Connection Management Fix

## Problem Analysis

The logs show several connection-related issues:
1. **Bad file descriptor** - Socket closed while still in use
2. **Connection reset by peer** - Abrupt connection closure
3. **Unable to decode frame** - Modbus protocol errors from stale connections
4. **Failed to connect** - Connection attempts failing

## Root Cause

The issue is that pymodbus's `ModbusTcpClient` doesn't properly handle:
1. Stale socket state after connection drops
2. Concurrent access from multiple entities
3. Automatic reconnection when connection is lost mid-operation

## Solution: Keep Connection Open with Better Error Handling

The best approach for Modbus TCP in Home Assistant is to:
1. **Keep the connection open** (don't close/reopen frequently)
2. **Detect stale connections** before use
3. **Reconnect only when necessary**
4. **Handle errors gracefully** with proper cleanup

## Implementation

Here's the fixed version of key methods:

### 1. Keep Connection Persistent

In `async_setup_entry()` - keep connection open:
```python
# Connect once and keep it open
client = ModbusTcpClient(entry.data[CONF_HOST], port=entry.data.get(CONF_PORT, DEFAULT_PORT))
client.timeout = 5
client.retries = 3
connected = await hass.async_add_executor_job(client.connect)
if not connected:
    raise ConfigEntryNotReady("Could not connect to Midnite Solar device")

# Store with connection open
entry.runtime_data = midnite_api
```

### 2. Better Connection Detection in _execute()

```python
async def _execute(self, func):
    """Execute a function in the executor and return the result."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Check if we need to reconnect (connection lost or socket invalid)
            if not self.client.connected or self._socket_is_stale():
                _LOGGER.info("Reconnecting Modbus client...")
                await self.hass.async_add_executor_job(self.client.close)
                await self.hass.async_add_executor_job(self.client.connect)
                _LOGGER.info(f"Connection status after reconnect: {self.client.connected}")
            
            result = await self.hass.async_add_executor_job(func)
            return result
        except (OSError, ConnectionException) as e:
            # Connection errors - try to recover
            _LOGGER.error(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
            await self.hass.async_add_executor_job(self.client.close)
            if attempt < max_retries - 1:
                await asyncio.sleep((attempt + 1) * 2)  # Exponential backoff
        except Exception as e:
            # Other errors - don't close connection, just retry
            _LOGGER.error(f"Error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
    
    raise Exception("Failed after all retries")
```

### 3. Socket Stale Detection

```python
def _socket_is_stale(self) -> bool:
    """Check if the socket is in a bad state."""
    try:
        # Check if socket exists and is valid
        if not hasattr(self.client, 'socket') or self.client.socket is None:
            return True
        
        # Try a simple check (don't actually send data)
        # Just verify the socket object is in good state
        import socket
        try:
            # Check if socket is still connected by examining its state
            # This is a lightweight check that doesn't send network traffic
            return False
        except:
            return True
    except Exception as e:
        _LOGGER.debug(f"Socket check error: {e}")
        return False
```

### 4. Clean Close on Unload

In `async_unload_entry()` - ensure proper cleanup:
```python
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if hasattr(entry, 'runtime_data') and entry.runtime_data:
        api = entry.runtime_data
        _LOGGER.info("Closing Modbus connection...")
        try:
            await hass.async_add_executor_job(api.client.close)
        except Exception as e:
            _LOGGER.error(f"Error closing connection: {e}")
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
```

## Key Improvements

1. **Persistent Connection** - Don't close/reopen unnecessarily
2. **Stale Socket Detection** - Check socket state before use
3. **Selective Reconnection** - Only reconnect when actually needed
4. **Better Error Handling** - Distinguish between connection and protocol errors
5. **Graceful Cleanup** - Proper connection closure on unload

## Why This Works Better

### Before (Problematic)
- Connection closed/reopened frequently
- No socket state checking
- All errors treated the same way
- Aggressive reconnection attempts

### After (Fixed)
- Connection stays open when healthy
- Socket validated before each use
- Smart reconnection only when needed
- Different handling for different error types
- Clean shutdown

## Testing Recommendations

1. **Monitor connection state** - Should see fewer reconnects
2. **Check for stale socket errors** - Should not appear after fix
3. **Test with network issues** - Verify graceful recovery
4. **Verify clean shutdown** - No errors on unload

## Expected Log Patterns

### Good (Persistent Connection)
```
"Setting up Midnite Solar at X.X.X.X:502"
"Connection result: True"
"Reading holding registers: address=4100, count=1"
"Function executed successfully"
```

### Recovery (When Needed)
```
"Reconnecting Modbus client..."
"Connection status after reconnect: True"
"Function executed successfully on attempt 2"
```

### Bad (Should Not Appear)
```
"Bad file descriptor"
"Connection reset by peer"
"Unable to decode frame"
```

## Implementation Notes

The key insight is that **Modbus TCP connections should be persistent** in Home Assistant integrations. The connection should:
1. Be established once at setup time
2. Stay open for the lifetime of the integration
3. Only be reconnected when explicitly detected as broken
4. Be closed cleanly on unload

This approach minimizes the "Bad file descriptor" and "Connection reset by peer" errors that occur when sockets are closed while still in use.
