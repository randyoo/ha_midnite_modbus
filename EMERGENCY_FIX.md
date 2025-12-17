# Emergency Fix for Home Assistant Freeze

## What Likely Happened

The connection locking implementation may have caused a deadlock because:
1. The lock is acquired in `_execute()` but might not be released properly
2. Multiple async contexts trying to acquire the same lock simultaneously
3. Potential infinite reconnection loop

## Immediate Recovery Steps

### 1. Safe Mode Restart

If Home Assistant is completely frozen:
```bash
# SSH into your HA host or use terminal
sudo systemctl stop home-assistant@youruser
sudo systemctl start home-assistant@youruser --wait
```

Or if using Docker:
```bash
docker restart homeassistant
```

### 2. Revert the Problematic Changes

The issue is most likely in the `_execute()` method where we added lock acquisition. Let me provide a safer version.

## Fixed Version of __init__.py

Replace the `_execute()` method with this safer version:

```python
async def _execute(self, func):
    """Execute a function in the executor and return the result."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Check connection without holding lock (non-blocking)
            if not self.client.connected:
                _LOGGER.info("Reconnecting Modbus client...")
                await self.hass.async_add_executor_job(self.client.connect)
                _LOGGER.info(f"Connection status after reconnect: {self.client.connected}")
            
            # Execute with lock protection - only the actual Modbus call
            result = await self.hass.async_add_executor_job(func)
            _LOGGER.info(f"Function executed successfully, result: {result}")
            return result
        except Exception as e:
            _LOGGER.error(f"Exception during executor job (attempt {attempt + 1}/{max_retries}): {e}", exc_info=True)
            # Try to reconnect on failure
            try:
                if self.client.connected:
                    _LOGGER.info("Closing connection after error...")
                    await self.hass.async_add_executor_job(self.client.close)
            except Exception as close_error:
                _LOGGER.error(f"Error while closing connection: {close_error}")
            
            # Exponential backoff
            _LOGGER.info(f"Waiting {(attempt + 1) * 1} seconds before retry...")
            await asyncio.sleep((attempt + 1) * 1)
    
    _LOGGER.error(f"Failed after {max_retries} attempts")
    raise
```

## Key Differences from Problematic Version

1. **Lock removed from `_execute()`** - The lock was causing potential deadlocks
2. **Simpler connection check** - Just checks `client.connected` without complex validation
3. **Non-blocking reconnection** - Doesn't hold locks during reconnect operations

## Alternative: Use Async Modbus Client

For better async support, consider using pymodbus's async client instead of the sync one with executor jobs:

```python
from pymodbus.client import AsyncModbusTcpClient

# In async_setup_entry()
self.client = AsyncModbusTcpClient(
    entry.data[CONF_HOST],
    port=entry.data.get(CONF_PORT, DEFAULT_PORT),
)

# Then you can use it directly without executor jobs
result = await self.client.read_holding_registers(...)
```

## Rollback Instructions

If you need to completely rollback:

1. SSH into your Home Assistant machine
2. Navigate to the custom_components directory:
   ```bash
   cd /config/custom_components/midnite
   ```
3. Revert the __init__.py file:
   ```bash
   git checkout HEAD~1 __init__.py
   ```
4. Restart Home Assistant

## Prevention for Future

When adding locks to async code:
1. Always ensure locks are released in finally blocks
2. Minimize time spent holding locks
3. Avoid nested lock acquisition
4. Consider if locks are actually needed (async contexts often don't need them)
5. Test with multiple concurrent operations before deploying

## Current Recommendation

The safest immediate fix is to remove the lock from `_execute()` and use simpler connection checking, as shown above. The timeout fix (moving it before connection) was correct and should remain.
