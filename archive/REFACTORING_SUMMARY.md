# Midnite Solar Architecture Overview

## Current Implementation

The Midnite Solar integration uses a hub/coordinator pattern following Home Assistant best practices:

### Key Components

#### `hub.py` - Connection Management
- Manages single Modbus TCP connection per device
- Thread-safe operations with threading.Lock
- Simple connect/disconnect methods
- Read/write operations for holding registers

#### `coordinator.py` - Data Update Coordination
- Uses Home Assistant's DataUpdateCoordinator
- Groups registers into logical categories
- Automatic reconnection and retry logic
- Configurable update interval (default: 15 seconds)

#### Entity Types
All entities extend `CoordinatorEntity[MidniteSolarUpdateCoordinator]`:
- **Sensors**: Battery voltage, PV voltage, temperatures, power, charge stage, etc.
- **Buttons**: Force float/bulk/equalize, reset faults, EEPROM update
- **Numbers**: Voltage setpoints, current limits, time settings

### Device Identification
The integration uses **DEVICE_ID registers (4111-4112)** as the unique identifier:
- Register 4111: DEVICE_ID_LSW (low word)
- Register 4112: DEVICE_ID_MSW (high word)
- Combined as: `(MSW << 16) | LSW`

**Note**: Registers 20492/20493 (SERIAL_NUMBER_MSB/LSB) have been removed due to consistent Modbus protocol errors.

## Key Design Decisions

### Thread-Safe Connection Management
All Modbus operations are protected by a threading.Lock to prevent concurrent access, which was causing "Unable to decode request" errors in the original implementation.

### Single Connection Pattern
The integration maintains one persistent Modbus TCP connection that stays open. This is more reliable than opening/closing connections for each operation.

### Device ID vs Serial Number
- **DEVICE_ID (4111-4112)**: Reliable, always accessible, used as primary identifier
- **SERIAL_NUMBER (20492-20493)**: Removed - caused Modbus protocol errors on all devices

## Files Structure
```
custom_components/midnite/
├── __init__.py          # Component setup and teardown
├── hub.py              # Modbus connection management
├── coordinator.py       # Data update coordination
├── base.py             # Base entity classes
├── sensor.py           # All sensor entities
├── button.py           # Button entities (actions)
├── number.py           # Number entities (configurable parameters)
└── const.py            # Constants and register map
```
