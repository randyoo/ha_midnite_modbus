# DHCP Discovery and Connection Issues Analysis

## Current State

Based on the code review, I've identified several issues that are preventing proper DHCP discovery and causing connection problems.

## Issue 1: DHCP Discovery Not Working

### Root Cause
The DHCP discovery implementation is mostly correct, but there's a critical issue in how the connection is being established during setup.

### Evidence from Code Review

Looking at `custom_components/midnite/__init__.py` lines 40-52:
```python
# Connect to the device
_LOGGER.info("Attempting to connect to Midnite Solar device...")
connected = await hass.async_add_executor_job(client.connect)
_LOGGER.info(f"Connection result: {connected}")
if not connected:
    raise ConfigEntryNotReady("Could not connect to Midnite Solar device")

# Configure client timeout settings
client.timeout = 5
client.retries = 3
```

**Problem**: The timeout and retry settings are configured AFTER the initial connection attempt. This means:
1. The first connection attempt uses default timeout (0.5 seconds)
2. If the device is slow to respond, it fails immediately
3. Even if we set `client.timeout = 5` after the failed connection, it doesn't help the initial attempt
4. The retry count is also set too late

### Solution
Move the timeout and retry configuration BEFORE the initial connection attempt:
```python
# Configure client timeout settings FIRST
client.timeout = 5
client.retries = 3

# THEN connect to the device
_LOGGER.info("Attempting to connect to Midnite Solar device...")
connected = await hass.async_add_executor_job(client.connect)
```

## Issue 2: Connection Management in MidniteAPI

Looking at `custom_components/midnite/__init__.py` lines 105-115:
```python
async def read_holding_registers(self, address: int, count: int = 1):
    """Read holding registers from the device."""
    _LOGGER.info(f"Reading holding registers: address={address}, count={count}")
    try:
        # Ensure connection is active
        if not self.client.connected:
            _LOGGER.info("Reconnecting Modbus client before read...")
            await self.hass.async_add_executor_job(self.client.connect)
```

**Problem**: The reconnection logic has several issues:
1. It only checks `client.connected` but doesn't verify the connection is actually working
2. If the connection was closed abruptly, it might report as "connected" when it's not
3. There's no retry logic with backoff in this method (only in `_execute`)
4. The connection state can be stale after errors

### Solution
Add more robust connection verification:
```python
def _is_connection_valid(self):
    """Check if the Modbus connection is truly valid."""
    try:
        return self.client.connected and self.client.socket is not None
    except Exception:
        return False

async def read_holding_registers(self, address: int, count: int = 1):
    """Read holding registers from the device."""
    _LOGGER.info(f"Reading holding registers: address={address}, count={count}")
    try:
        # Ensure connection is active
        if not self._is_connection_valid():
            _LOGGER.info("Connection invalid, reconnecting Modbus client...")
            await self.hass.async_add_executor_job(self.client.close)
            await self.hass.async_add_executor_job(self.client.connect)
```

## Issue 3: Connection Contention / Race Conditions

The error messages show:
- "Connection unexpectedly closed"
- "Connection reset by peer"
- "Bad file descriptor"

These suggest that multiple threads/processes are trying to access the same Modbus client simultaneously, or the connection is being closed while still in use.

### Root Cause Analysis

Looking at the code flow:
1. `async_setup_entry` creates a single ModbusTcpClient and stores it in `entry.runtime_data`
2. Multiple entities (sensors, buttons, numbers) all access this same client
3. Each entity may try to read/write registers independently
4. The connection can be closed by one operation while another is in progress

### Solution
Implement proper connection locking and ensure atomic operations:
```python
import asyncio
from threading import Lock

class MidniteAPI:
    def __init__(self, hass: HomeAssistant, client: ModbusTcpClient):
        self.hass = hass
        self.client = client
        self._connection_lock = Lock()  # Protect concurrent access
        self.device_info = {...}

    async def _execute(self, func):
        """Execute a function in the executor with connection protection."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Acquire lock to prevent concurrent access
                with self._connection_lock:
                    if not self._is_connection_valid():
                        _LOGGER.info("Reconnecting Modbus client...")
                        await self.hass.async_add_executor_job(self.client.connect)
                    
                    result = await self.hass.async_add_executor_job(func)
                    return result
            except Exception as e:
                # Release lock before retry delay
                _LOGGER.error(f"Exception during executor job (attempt {attempt + 1}/{max_retries}): {e}")
                # Close connection on error to force reconnect
                try:
                    with self._connection_lock:
                        if self.client.connected:
                            await self.hass.async_add_executor_job(self.client.close)
                except Exception as close_error:
                    _LOGGER.error(f"Error while closing connection: {close_error}")
                
                # Exponential backoff
                await asyncio.sleep((attempt + 1) * 1)
        
        raise Exception(f"Failed after {max_retries} attempts")
```

## Issue 4: DHCP Discovery Debugging

The logs show that DHCP discovery is being triggered, but the "Discovered" card isn't appearing. This could be because:

1. The unique ID isn't being set correctly (but we fixed this with `ConfigEntries.format_mac`)
2. An exception during `async_step_dhcp` is preventing the flow from completing
3. The return value from `async_step_user()` isn't proper for discovery

### Solution
Add more defensive error handling in `async_step_dhcp`:
```python
async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
    """Handle DHCP discovery."""
    try:
        _LOGGER.info(f"DHCP discovery triggered for device at {discovery_info.ip}")
        
        # 1. SET UNIQUE ID (Crucial step)
        from homeassistant.config_entries import ConfigEntries
        formatted_mac = ConfigEntries.format_mac(discovery_info.macaddress)
        _LOGGER.info(f"Setting unique ID: {formatted_mac}")
        await self.async_set_unique_id(formatted_mac, raise_on_progress=False)
        
        # 2. ABORT IF ALREADY CONFIGURED
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: discovery_info.ip}
        )
        
        # 3. STORE DISCOVERY INFO
        self.discovery_info = discovery_info
        self.context["title_placeholders"] = {"ip": discovery_info.ip}
        
        # 4. TRIGGER USER FLOW
        return await self.async_step_user()
    except Exception as e:
        _LOGGER.error(f"Error in async_step_dhcp: {e}", exc_info=True)
        return self.async_abort(reason="discovery_failed")
```

## Issue 5: Connection Timeout Too Short

The default pymodbus timeout is 0.5 seconds, which may not be enough for:
- Network latency
- Device bootup time
- Modbus protocol overhead

### Solution
Increase the timeout and add retry logic earlier in the setup process.

## Recommended Fixes

### Priority 1: Connection Configuration Timing (Critical)
Move timeout/retry configuration before initial connection:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Midnite Solar from a config entry."""
    _LOGGER.info(f"Setting up Midnite Solar at {entry.data[CONF_HOST]}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}")
    client = ModbusTcpClient(
        entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
    )

    # Configure timeout and retries BEFORE connecting
    client.timeout = 5
    client.retries = 3
    
    # Connect to the device
    _LOGGER.info("Attempting to connect to Midnite Solar device...")
    connected = await hass.async_add_executor_job(client.connect)
    _LOGGER.info(f"Connection result: {connected}")
    if not connected:
        raise ConfigEntryNotReady("Could not connect to Midnite Solar device")
```

### Priority 2: Connection Locking (Critical for stability)
Add thread-safe connection management:
```python
class MidniteAPI:
    def __init__(self, hass: HomeAssistant, client: ModbusTcpClient):
        self.hass = hass
        self.client = client
        self._connection_lock = Lock()  # NEW: Thread lock for connection safety
        self.device_info = {...}
```

### Priority 3: Improved Connection Validation
Add better connection state checking:
```python
    def _is_connection_valid(self):
        """Check if the Modbus connection is truly valid."""
        try:
            return self.client.connected and hasattr(self.client, 'socket') and self.client.socket is not None
        except Exception:
            return False
```

### Priority 4: Enhanced Error Recovery
Improve the `_execute` method to handle connection drops better:
```python
    async def _execute(self, func):
        """Execute a function in the executor and return the result."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use lock to prevent concurrent access
                with self._connection_lock:
                    if not self._is_connection_valid():
                        _LOGGER.info("Connection invalid, reconnecting...")
                        await self.hass.async_add_executor_job(self.client.connect)
                    
                    result = await self.hass.async_add_executor_job(func)
                    return result
            except Exception as e:
                _LOGGER.error(f"Exception during executor job (attempt {attempt + 1}/{max_retries}): {e}")
                # Force close connection on error to avoid stale state
                try:
                    with self._connection_lock:
                        if hasattr(self.client, 'connected') and self.client.connected:
                            await self.hass.async_add_executor_job(self.client.close)
                except Exception as close_error:
                    _LOGGER.error(f"Error while closing connection: {close_error}")
                
                # Exponential backoff
                await asyncio.sleep((attempt + 1) * 1)
        
        raise Exception(f"Failed after {max_retries} attempts")
```

## Testing Strategy

After implementing these fixes:

1. **Test DHCP Discovery**:
   - Restart Home Assistant
   - Connect a Midnite Solar device to the network
   - Verify "Discovered" card appears in Settings → Devices & Services
   - Check logs for `async_step_dhcp` being called

2. **Test Connection Reliability**:
   - Monitor logs during initial connection
   - Verify no "connection reset by peer" errors
   - Test with multiple entities reading simultaneously
   - Verify retry logic works (check for exponential backoff in logs)

3. **Test Recovery from Errors**:
   - Simulate network disruption
   - Verify automatic reconnection
   - Check that entities recover gracefully

4. **Performance Testing**:
   - Measure connection time with 5-second timeout
   - Verify no race conditions with concurrent access
