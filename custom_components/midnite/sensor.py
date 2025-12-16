"""Support for Midnite Solar sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CHARGE_STAGES, DEVICE_TYPES, DOMAIN, INTERNAL_STATES, REGISTER_MAP, REST_REASONS
from . import MidniteAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar sensors."""
    api = entry.runtime_data
    
    sensors = [
        DeviceTypeSensor(api, entry),
        BatteryVoltageSensor(api, entry),
        PVoltageSensor(api, entry),
        BatteryCurrentSensor(api, entry),
        PowerWattsSensor(api, entry),
        ChargeStageSensor(api, entry),
        InternalStateSensor(api, entry),
        RestReasonSensor(api, entry),
        BatteryTemperatureSensor(api, entry),
        FETTemperatureSensor(api, entry),
        PCBTemperatureSensor(api, entry),
        DailyAmpHoursSensor(api, entry),
        LifetimeEnergySensor(api, entry),
        LifetimeAmpHoursSensor(api, entry),
        PVInputCurrentSensor(api, entry),
        VOCMeasuredSensor(api, entry),
        FloatTimeTodaySensor(api, entry),
        AbsorbTimeRemainingSensor(api, entry),
        EqualizeTimeRemainingSensor(api, entry),
    ]
    
    async_add_entities(sensors)


class MidniteSolarSensor(SensorEntity):
    """Base class for all Midnite Solar sensors."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        self._api = api
        self._entry = entry
        # Use device_info from API if available, otherwise create basic one
        if hasattr(api, 'device_info') and api.device_info.get('identifiers'):
            self._attr_device_info = api.device_info
        else:
            self._attr_device_info = {
                "identifiers": {(DOMAIN, entry.entry_id)},
                "name": entry.title,
                "manufacturer": "Midnite Solar",
            }

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        pass  # To be implemented by subclasses


class BatteryVoltageSensor(MidniteSolarSensor):
    """Representation of a battery voltage sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Battery Voltage"
        self._attr_unique_id = f"{entry.entry_id}_batt_voltage"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["DISP_AVG_VBATT"])
        if registers:
            self._attr_native_value = registers[0] / 10.0


class PVoltageSensor(MidniteSolarSensor):
    """Representation of a PV input voltage sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "PV Voltage"
        self._attr_unique_id = f"{entry.entry_id}_pv_voltage"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["DISP_AVG_VPV"])
        if registers:
            self._attr_native_value = registers[0] / 10.0


class BatteryCurrentSensor(MidniteSolarSensor):
    """Representation of a battery current sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Battery Current"
        self._attr_unique_id = f"{entry.entry_id}_batt_current"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["IBATT_DISPLAY_S"])
        if registers:
            # Current can be negative (discharging)
            value = registers[0] / 10.0
            # Convert to signed value if needed
            if value > 32767:  # Check for negative values in unsigned register
                value = value - 65536
            
            # Validate current range (-200A to 200A is reasonable)
            if abs(value) > 200:
                _LOGGER.warning(f"Invalid battery current reading: {value}A. Ignoring.")
                return
            
            self._attr_native_value = value


class PowerWattsSensor(MidniteSolarSensor):
    """Representation of a power output sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Power Output"
        self._attr_unique_id = f"{entry.entry_id}_power_watts"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["WATTS"])
        if registers:
            self._attr_native_value = registers[0]


class ChargeStageSensor(MidniteSolarSensor):
    """Representation of a charge stage sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Charge Stage"
        self._attr_unique_id = f"{entry.entry_id}_charge_stage"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(CHARGE_STAGES.values())

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["COMBO_CHARGE_STAGE"])
        if registers:
            raw_value = registers[0]
            _LOGGER.debug(f"Raw charge state value: {raw_value} (hex: 0x{raw_value:x})")
            
            # Extract MSB (high byte) for charge stage
            # According to the spec: [addr]MSB = (value >> 8) & 0xFF
            charge_stage_value = (raw_value >> 8) & 0xFF
            _LOGGER.debug(f"Charge stage value (MSB): {charge_stage_value}")
            
            # Look up the charge stage description
            self._attr_native_value = CHARGE_STAGES.get(charge_stage_value, f"Unknown ({charge_stage_value})")


class InternalStateSensor(MidniteSolarSensor):
    """Representation of an internal state sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Internal State"
        self._attr_unique_id = f"{entry.entry_id}_internal_state"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_options = list(INTERNAL_STATES.values())

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["COMBO_CHARGE_STAGE"])
        if registers:
            raw_value = registers[0]
            _LOGGER.debug(f"Raw charge state value: {raw_value} (hex: 0x{raw_value:x})")
            
            # Extract LSB (low byte) for internal state
            # According to the spec: [addr]LSB = value & 0xFF
            internal_state_value = raw_value & 0xFF
            _LOGGER.debug(f"Internal state value (LSB): {internal_state_value}")
            
            # Look up the internal state description
            self._attr_native_value = INTERNAL_STATES.get(internal_state_value, f"Unknown ({internal_state_value})")


class DeviceTypeSensor(MidniteSolarSensor):
    """Representation of the device type sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Device Type"
        self._attr_unique_id = f"{entry.entry_id}_device_type"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["UNIT_ID"])
        if registers:
            # Register 4101: [4101]MSB → PCB Rev, [4101]LSB → Unit Type
            device_value = registers[0] & 0xFF  # Get LSB (unit type)
            self._attr_native_value = DEVICE_TYPES.get(device_value, f"Unknown ({device_value})")


class RestReasonSensor(MidniteSolarSensor):
    """Representation of the rest reason sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Rest Reason"
        self._attr_unique_id = f"{entry.entry_id}_rest_reason"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["REASON_FOR_RESTING"])
        if registers:
            reason_value = registers[0]
            self._attr_native_value = REST_REASONS.get(reason_value, f"Unknown ({reason_value})")


class BatteryTemperatureSensor(MidniteSolarSensor):
    """Representation of a battery temperature sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Battery Temperature"
        self._attr_unique_id = f"{entry.entry_id}_batt_temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["BATT_TEMPERATURE"])
        if registers:
            value = registers[0] / 10.0
            # Check for negative temperature (two's complement)
            if value > 32767:
                value = value - 65536
            
            # Validate temperature range (-50°C to 150°C is reasonable for batteries)
            if value < -50 or value > 150:
                _LOGGER.warning(f"Invalid battery temperature reading: {value}°C. Ignoring.")
                return
            
            self._attr_native_value = value


class FETTemperatureSensor(MidniteSolarSensor):
    """Representation of a FET temperature sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "FET Temperature"
        self._attr_unique_id = f"{entry.entry_id}_fet_temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["FET_TEMPERATURE"])
        if registers:
            value = registers[0] / 10.0
            # Check for negative temperature (two's complement)
            if value > 32767:
                value = value - 65536
            
            # Validate temperature range (-50°C to 150°C is reasonable)
            if value < -50 or value > 150:
                _LOGGER.warning(f"Invalid FET temperature reading: {value}°C. Ignoring.")
                return
            
            self._attr_native_value = value


class PCBTemperatureSensor(MidniteSolarSensor):
    """Representation of a PCB temperature sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "PCB Temperature"
        self._attr_unique_id = f"{entry.entry_id}_pcb_temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["PCB_TEMPERATURE"])
        if registers:
            value = registers[0] / 10.0
            # Check for negative temperature (two's complement)
            if value > 32767:
                value = value - 65536
            
            # Validate temperature range (-50°C to 150°C is reasonable)
            if value < -50 or value > 150:
                _LOGGER.warning(f"Invalid PCB temperature reading: {value}°C. Ignoring.")
                return
            
            self._attr_native_value = value


class DailyAmpHoursSensor(MidniteSolarSensor):
    """Representation of daily amp-hours sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Daily Amp-Hours"
        self._attr_unique_id = f"{entry.entry_id}_daily_ah"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["AMP_HOURS_DAILY"])
        if registers:
            # Convert Ah to kWh (1Ah = 0.001kWh for 12V system, but we'll keep as is)
            self._attr_native_value = registers[0] / 1000.0


class LifetimeEnergySensor(MidniteSolarSensor):
    """Representation of lifetime energy sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Lifetime Energy"
        self._attr_unique_id = f"{entry.entry_id}_lifetime_energy"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["LIFETIME_KW_HOURS_1"])
        if registers:
            # Read 32-bit value
            high_word = await self._api.read_holding_registers(REGISTER_MAP["LIFETIME_KW_HOURS_1"] + 1)
            if high_word:
                value = (high_word[0] << 16) | registers[0]
                self._attr_native_value = value / 10.0


class LifetimeAmpHoursSensor(MidniteSolarSensor):
    """Representation of lifetime amp-hours sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Lifetime Amp-Hours"
        self._attr_unique_id = f"{entry.entry_id}_lifetime_ah"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["LIFETIME_AMP_HOURS_1"])
        if registers:
            # Read 32-bit value
            high_word = await self._api.read_holding_registers(REGISTER_MAP["LIFETIME_AMP_HOURS_1"] + 1)
            if high_word:
                value = (high_word[0] << 16) | registers[0]
                self._attr_native_value = value / 10.0


class PVInputCurrentSensor(MidniteSolarSensor):
    """Representation of PV input current sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "PV Input Current"
        self._attr_unique_id = f"{entry.entry_id}_pv_current"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["PV_INPUT_CURRENT"])
        if registers:
            value = registers[0] / 10.0
            # Check for negative values
            if value > 32767:
                value = value - 65536
            
            # Validate current range (-100A to 100A is reasonable)
            if abs(value) > 100:
                _LOGGER.warning(f"Invalid PV input current reading: {value}A. Ignoring.")
                return
            
            self._attr_native_value = value


class VOCMeasuredSensor(MidniteSolarSensor):
    """Representation of last measured VOC sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Last Measured VOC"
        self._attr_unique_id = f"{entry.entry_id}_voc_measured"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["VOC_LAST_MEASURED"])
        if registers:
            self._attr_native_value = registers[0] / 10.0


class FloatTimeTodaySensor(MidniteSolarSensor):
    """Representation of float time today sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Float Time Today"
        self._attr_unique_id = f"{entry.entry_id}_float_time_today"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.DURATION
        # Display in minutes for better readability
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Time is in whole minutes, no decimal precision needed
        self._attr_suggested_display_precision = 0

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["FLOAT_TIME_TODAY_SEC"])
        if registers:
            # Store value in minutes for display
            seconds = registers[0]
            minutes = seconds / 60.0
            
            # Set the state with proper unit conversion
            self._attr_native_value = minutes
            
            # Add attributes for additional context
            self._attr_extra_state_attributes = {
                "seconds": seconds,
                "hours": minutes / 60.0,
            }


class AbsorbTimeRemainingSensor(MidniteSolarSensor):
    """Representation of absorb time remaining sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Absorb Time Remaining"
        self._attr_unique_id = f"{entry.entry_id}_absorb_time_remaining"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.DURATION
        # Display in minutes for better readability
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Time is in whole minutes, no decimal precision needed
        self._attr_suggested_display_precision = 0

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["ABSORB_TIME"])
        if registers:
            # Store value in minutes for display
            seconds = registers[0]
            minutes = seconds / 60.0
            
            # Set the state with proper unit conversion
            self._attr_native_value = minutes
            
            # Add attributes for additional context
            self._attr_extra_state_attributes = {
                "seconds": seconds,
                "hours": minutes / 60.0,
            }


class EqualizeTimeRemainingSensor(MidniteSolarSensor):
    """Representation of equalize time remaining sensor."""

    def __init__(self, api: MidniteAPI, entry: Any):
        """Initialize the sensor."""
        super().__init__(api, entry)
        self._attr_name = "Equalize Time Remaining"
        self._attr_unique_id = f"{entry.entry_id}_equalize_time_remaining"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.DURATION
        # Display in minutes for better readability
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Time is in whole minutes, no decimal precision needed
        self._attr_suggested_display_precision = 0

    async def async_update(self) -> None:
        """Update sensor data from the device."""
        registers = await self._api.read_holding_registers(REGISTER_MAP["EQUALIZE_TIME"])
        if registers:
            # Store value in minutes for display
            seconds = registers[0]
            minutes = seconds / 60.0
            
            # Set the state with proper unit conversion
            self._attr_native_value = minutes
            
            # Add attributes for additional context
            self._attr_extra_state_attributes = {
                "seconds": seconds,
                "hours": minutes / 60.0,
            }
