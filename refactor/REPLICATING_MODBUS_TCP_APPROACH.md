# Replicating the Victron Modbus TCP Approach

## Step-by-Step Guide for Implementing Modbus TCP in Home Assistant

This guide provides a practical, step-by-step approach to implementing Modbus TCP in your Home Assistant integration, based on the proven Victron implementation.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Step 1: Create the Hub Class](#step-1-create-the-hub-class)
3. [Step 2: Implement Connection Management](#step-2-implement-connection-management)
4. [Step 3: Set Up the Coordinator](#step-3-set-up-the-coordinator)
5. [Step 4: Configure Config Flow](#step-4-configure-config-flow)
6. [Step 5: Handle Data Updates](#step-5-handle-data-updates)
7. [Step 6: Implement Error Handling](#step-6-implement-error-handling)
8. [Step 7: Manage Lifecycle](#step-7-manage-lifecycle)
9. [Complete Example](#complete-example)
10. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)

## Architecture Overview

```
┌───────────────────────────────────────────────────────┐
│                    Home Assistant                     │
├───────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌───────────────────────────────┐  │
│  │ Config Entry │───▶│ DataUpdateCoordinator (your   │  │
│  └─────────────┘    │     coordinator)               │  │
│                     └───────────────────────────────┘  │
│                              ▲                        │
│                              │                        │
│                     ┌───────────────────┐            │
│                     │   YourHubClass    │            │
│                     │ (wraps ModbusTcp- │            │
│                     │  Client)          │            │
│                     └───────────────────┘            │
│                              ▲                        │
│                              │                        │
└──────────────────────────────┼────────────────────────────┘
                               │
                         ┌──────┴──────┐
                         │  Modbus    │
                         │  TCP       │
                         │  Device    │
                         └──────┬──────┘
                               │
                           Multiple
                           Unit IDs
```

## Step 1: Create the Hub Class

**Purpose**: Wrap pymodbus client and manage connection lifecycle.

```python
# hub.py
import logging
from pymodbus.client import ModbusTcpClient

_LOGGER = logging.getLogger(__name__)

class YourHub:
    """Your Modbus TCP hub that manages the connection."""
    
    def __init__(self, host: str, port: int) -> None:
        """Initialize the hub with connection parameters."""
        self.host = host
        self.port = port
        self._client = ModbusTcpClient(host=self.host, port=self.port)
    
    def connect(self):
        """Establish connection to Modbus TCP server."""
        return self._client.connect()
    
    def disconnect(self):
        """Close the connection if it's open."""
        if self._client.is_socket_open():
            return self._client.close()
        return None
    
    def is_connected(self):
        """Check if connection is active."""
        return self._client.is_socket_open()
```

**Key Points:**
- Create ONE `ModbusTcpClient` instance per hub
- Store it as `self._client`
- Implement basic connection management methods

## Step 2: Implement Connection Management

Add read/write operations that use the single connection:

```python
# Add to hub.py
    def read_holding_registers(self, unit_id: int, address: int, count: int):
        """Read holding registers from a specific unit."""
        _LOGGER.debug("Reading unit %s address %s count %s", unit_id, address, count)
        return self._client.read_holding_registers(
            address=address,
            count=count,
            device_id=unit_id  # Key: access different units through same connection
        )
    
    def write_register(self, unit_id: int, address: int, value: int):
        """Write to a register on a specific unit."""
        return self._client.write_register(
            address=address,
            value=value,
            device_id=unit_id
        )
```

**Key Points:**
- Use `device_id` parameter to access different Modbus units
- Keep operations simple - just pass through to pymodbus
- Add logging for debugging

## Step 3: Set Up the Coordinator

**Purpose**: Manage periodic updates and coordinate async/sync operations.

```python
# coordinator.py
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .hub import YourHub

class YourDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinate data updates from your Modbus device."""
    
    def __init__(self, hass: HomeAssistant, host: str, port: int, interval: int):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="your_integration",
            update_interval=timedelta(seconds=interval)
        )
        self.api = YourHub(host, port)  # Create ONE hub
        self.api.connect()  # Establish connection
    
    async def _async_update_data(self):
        """Fetch data from the Modbus device."""
        try:
            # Schedule blocking operation in executor
            data = await self.hass.async_add_executor_job(
                self._fetch_data_sync
            )
            return data
        except Exception as e:
            raise UpdateFailed(f"Error fetching data: {e}") from e
    
    def _fetch_data_sync(self):
        """Synchronous data fetch (runs in executor)."""
        # This method can be blocking - it's OK here
        return self.api.read_holding_registers(unit_id=1, address=0, count=10)
```

**Key Points:**
- Extend `DataUpdateCoordinator`
- Create ONE hub instance in `__init__`
- Connect immediately after creation
- Use `async_add_executor_job()` for blocking Modbus operations
- Keep sync and async concerns separate

## Step 4: Configure Config Flow

**Purpose**: Handle user setup and validate connection.

```python
# config_flow.py
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .hub import YourHub

class YourConfigFlow(config_entries.ConfigFlow, domain="your_integration"):
    """Handle configuration flow."""
    
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            try:
                # Validate connection
                hub = YourHub(user_input["host"], user_input["port"])
                if not hub.connect():
                    raise ConnectionError("Failed to connect")
                
                # Discover devices (optional)
                devices = await self._async_discover_devices(hub)
                
                # Close temporary connection
                hub.disconnect()
                
                return self.async_create_entry(
                    title=f"Device at {user_input['host']}",
                    data={"devices": devices}
                )
            except Exception as e:
                errors["base"] = "cannot_connect"
                _LOGGER.error("Connection failed: %s", e)
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
                vol.Required("port", default=502): int,
            }),
            errors=errors
        )
    
    async def _async_discover_devices(self, hub: YourHub):
        """Discover available devices/units."""
        # Implement device discovery logic here
        return [1, 2, 3]  # Example unit IDs
```

**Key Points:**
- Create temporary hub for validation
- Close it after validation completes
- Keep the temporary connection short-lived
- Don't reuse this hub - let the coordinator create the persistent one

## Step 5: Handle Data Updates

Enhance your coordinator to handle multiple units and parse data:

```python
# Add to coordinator.py
    async def _async_update_data(self):
        """Fetch all device data."""
        parsed_data = {}
        unavailable_entities = {}
        
        # Define what registers to read for each unit
        units_to_read = {
            1: {"address": 0, "count": 10},
            2: {"address": 100, "count": 5},
        }
        
        if self.data is None:
            self.data = {"data": {}, "availability": {}}
        
        for unit_id, read_params in units_to_read.items():
            try:
                # Read registers for this unit
                result = await self.hass.async_add_executor_job(
                    self.api.read_holding_registers,
                    unit_id,
                    read_params["address"],
                    read_params["count"]
                )
                
                if result.isError():
                    _LOGGER.warning("Error reading from unit %s", unit_id)
                    for i in range(read_params["count"]):
                        unavailable_entities[f"{unit_id}.register_{i}"] = False
                else:
                    # Parse successful data
                    parsed_data.update(self._parse_registers(unit_id, result.registers))
                    for i in range(read_params["count"]):
                        unavailable_entities[f"{unit_id}.register_{i}"] = True
            
            except Exception as e:
                _LOGGER.error("Failed to read from unit %s: %s", unit_id, e)
        
        return {
            "data": parsed_data,
            "availability": unavailable_entities,
        }
    
    def _parse_registers(self, unit_id: int, registers: list):
        """Parse raw register values."""
        # Implement your parsing logic here
        return {f"{unit_id}.voltage": registers[0] / 10.0}
```

**Key Points:**
- Read from multiple units in a single update cycle
- Handle errors per-unit to enable partial updates
- Track availability of individual entities
- Parse data after successful reads

## Step 6: Implement Error Handling

Add robust error handling:

```python
# Add to hub.py
    def read_holding_registers(self, unit_id: int, address: int, count: int):
        """Read holding registers with error handling."""
        try:
            # Check connection before reading
            if not self.is_connected():
                if not self.connect():
                    raise ConnectionError("Failed to reconnect")
            
            result = self._client.read_holding_registers(
                address=address,
                count=count,
                device_id=unit_id
            )
            
            # Check for Modbus errors
            if result.isError():
                error_code = result.function_code
                _LOGGER.error("Modbus error %s reading unit %s", error_code, unit_id)
            
            return result
        except Exception as e:
            _LOGGER.error("Read failed: %s", e)
            raise
```

**Key Points:**
- Check connection state before operations
- Handle Modbus-specific errors
- Log meaningful error messages
- Let exceptions propagate (coordinator will handle them)

## Step 7: Manage Lifecycle

Properly handle startup and shutdown:

```python
# __init__.py
async def async_setup_entry(hass, config_entry):
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = YourDataUpdateCoordinator(
        hass,
        config_entry.options["host"],
        config_entry.options["port"],
        config_entry.options.get("interval", 30)
    )
    
    # Initial refresh
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator
    hass.data[DOMAIN][config_entry.entry_id] = coordinator
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass, config_entry):
    """Unload the integration."""
    unloaded = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    
    # Remove coordinator (and its connection) from hass.data
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        del hass.data[DOMAIN][config_entry.entry_id]
    
    return unloaded
```

**Key Points:**
- Create coordinator during setup
- Store it in `hass.data` with config entry ID as key
- Remove it during unload (connection will be closed by garbage collection)
- Let Home Assistant manage the lifecycle

## Complete Example

Here's a complete, minimal implementation:

```python
# hub.py
from pymodbus.client import ModbusTcpClient
import logging

_LOGGER = logging.getLogger(__name__)

class MyHub:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._client = ModbusTcpClient(host, port)
    
    def connect(self):
        return self._client.connect()
    
    def disconnect(self):
        if self._client.is_socket_open():
            return self._client.close()
    
    def read_holding_registers(self, unit_id: int, address: int, count: int):
        _LOGGER.debug("Reading unit %s addr %s count %s", unit_id, address, count)
        if not self._client.is_socket_open() and not self.connect():
            raise ConnectionError("Failed to connect")
        return self._client.read_holding_registers(address, count, device_id=unit_id)
```

```python
# coordinator.py
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .hub import MyHub

class MyCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, host: str, port: int, interval: int = 30):
        super().__init__(hass, _LOGGER, name="my_integration", update_interval=timedelta(seconds=interval))
        self.api = MyHub(host, port)
        self.api.connect()
    
    async def _async_update_data(self):
        try:
            data = await self.hass.async_add_executor_job(
                self._read_data
            )
            return {"value": data.registers[0] if not data.isError() else None}
        except Exception as e:
            raise UpdateFailed(f"Update failed: {e}") from e
    
    def _read_data(self):
        return self.api.read_holding_registers(unit_id=1, address=0, count=1)
```

## Common Pitfalls and Solutions

### ❌ Pitfall 1: Creating multiple connections per device
**Problem**: Creating a new `ModbusTcpClient` for each unit or operation.

```python
# WRONG - Multiple connections
for unit_id in [1, 2, 3]:
    client = ModbusTcpClient(host, port)  # New connection each time!
    result = client.read_holding_registers(..., device_id=unit_id)
```

**Solution**: Create ONE client and reuse it.

```python
# RIGHT - Single connection
client = ModbusTcpClient(host, port)
for unit_id in [1, 2, 3]:
    result = client.read_holding_registers(..., device_id=unit_id)  # Same connection
```

### ❌ Pitfall 2: Not using async_add_executor_job
**Problem**: Blocking Modbus operations in the event loop.

```python
# WRONG - Blocks event loop
async def _async_update_data(self):
    result = self.api.read_holding_registers(...)  # This is blocking!
```

**Solution**: Schedule blocking operations in executor.

```python
# RIGHT - Non-blocking
async def _async_update_data(self):
    result = await self.hass.async_add_executor_job(
        self.api.read_holding_registers, ...
    )
```

### ❌ Pitfall 3: Not handling connection state
**Problem**: Assuming connection stays open forever.

```python
# WRONG - No connection check
result = self._client.read_holding_registers(...)
```

**Solution**: Check and reconnect if needed.

```python
# RIGHT - Connection-aware
if not self._client.is_socket_open():
    if not self._client.connect():
        raise ConnectionError("Failed to connect")
result = self._client.read_holding_registers(...)
```

### ❌ Pitfall 4: Not handling partial failures
**Problem**: Failing entire update when one unit fails.

```python
# WRONG - All-or-nothing
for unit_id in units:
    data = read_from_unit(unit_id)  # If one fails, all fail
```

**Solution**: Continue on errors and track availability.

```python
# RIGHT - Graceful degradation
parsed_data = {}
availability = {}
for unit_id in units:
    try:
        data = read_from_unit(unit_id)
        if not data.isError():
            parsed_data[unit_id] = parse(data)
            availability[unit_id] = True
        else:
            availability[unit_id] = False
    except Exception:
        availability[unit_id] = False
```

### ❌ Pitfall 5: Not letting Home Assistant manage lifecycle
**Problem**: Manually managing connection cleanup.

```python
# WRONG - Manual cleanup
def async_unload_entry(hass, config_entry):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    coordinator.api.disconnect()  # Manual disconnect
    del hass.data[DOMAIN][config_entry.entry_id]
```

**Solution**: Let garbage collection handle it.

```python
# RIGHT - Automatic cleanup
def async_unload_entry(hass, config_entry):
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        del hass.data[DOMAIN][config_entry.entry_id]  # Connection closed on GC
```

## Final Checklist

Before deploying your Modbus TCP integration, verify:

- [ ] ✅ One `ModbusTcpClient` instance per physical device
- [ ] ✅ Using `device_id` parameter for multiple units
- [ ] ✅ Connection established once during initialization
- [ ] ✅ Using `async_add_executor_job()` for blocking operations
- [ ] ✅ Proper error handling with partial failure recovery
- [ ] ✅ Connection state checking before operations
- [ ] ✅ Lifecycle managed through Home Assistant config entry
- [ ] ✅ Temporary connections closed after validation
- [ ] ✅ Logging for debugging and monitoring
- [ ] ✅ Availability tracking for entities

By following this guide, you'll implement a robust Modbus TCP integration that follows the proven patterns used in the Victron integration.
