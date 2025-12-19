# Connection Management Fix for Midnite Solar Integration

## Summary of Changes

This fix addresses the connection issues reported where the integration would take ~40 minutes to stabilize after a Home Assistant restart.

## Key Improvements

### 1. Exponential Backoff with Jitter
- **Before**: Fixed 2-second delay between retries
- **After**: Exponential backoff (2s, 4s, 8s, 16s, 32s, 64s max) with ±20% random jitter
- This prevents thundering herd problems and is more respectful to the device

### 2. Connection State Management
- Added explicit connection state tracking (CONNECTED, DISCONNECTED, RECONNECTING)
- Implemented async locks to prevent concurrent connection attempts
- Proper socket cleanup on errors

### 3. Improved Timeout Settings
- **Before**: 5-second timeout
- **After**: 10-second timeout (more appropriate for Modbus devices)

### 4. Connection Health Monitoring
- Added connection verification before operations
- Tracks retry count and connection state
- Better error handling and logging

### 5. Reduced Verbose Logging
- Changed many INFO logs to DEBUG level to reduce log spam
- Kept critical connection events at INFO level

## Technical Details

### New ConnectionManager Class
The `ConnectionManager` class encapsulates all connection logic:

```python
class ConnectionManager:
    def __init__(self, hass, host, port):
        self.client = ModbusTcpClient(host, port)
        self.connection_state = CONNECTION_STATE_DISCONNECTED
        self.retry_count = 0
        self.lock = asyncio.Lock()
        self.client.timeout = 10  # Increased timeout
        self.client.retries = 3
    
    async def connect(self) -> bool:
        """Connect with exponential backoff"""
        ...
    
    async def ensure_connected(self) -> bool:
        """Verify and ensure connection is healthy"""
        ...
    
    async def close(self):
        """Properly close connection"""
        ...
```

### Backoff Algorithm
```python
async def _calculate_backoff(self) -> float:
    if self.retry_count == 0: return 0
    elif self.retry_count == 1: base_delay = 2.0
    elif self.retry_count == 2: base_delay = 4.0
    elif self.retry_count == 3: base_delay = 8.0
    else: base_delay = min(64.0 * (2 ** (self.retry_count - 4)), 120.0)
    
    # Add jitter (±20%)
    jitter = random.uniform(0.8, 1.2)
    return base_delay * jitter
```

## Expected Benefits

1. **Faster stabilization**: Connections should stabilize within minutes instead of ~40 minutes
2. **Reduced error logs**: Better connection handling means fewer transient errors
3. **More respectful to device**: Exponential backoff prevents overwhelming the device
4. **Better resource management**: Proper socket cleanup prevents "bad file descriptor" errors
5. **Improved reliability**: Connection verification ensures we don't use stale connections

## Testing Recommendations

1. Restart Home Assistant and monitor connection logs
2. Verify that errors stop within a few minutes (not 40)
3. Check for proper exponential backoff in logs (2s, 4s, 8s delays)
4. Ensure no "bad file descriptor" errors appear
5. Verify all sensors still update correctly after connection issues
