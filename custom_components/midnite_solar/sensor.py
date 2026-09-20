"""Support for Midnite Solar sensor platform."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from .base import MidniteBaseEntityDescription

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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHARGE_STAGES, DEVICE_TYPES, DOMAIN, INTERNAL_STATES, REGISTER_MAP, REST_REASONS
from .coordinator import MidniteSolarUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        DeviceTypeSensor(coordinator, entry),
        BatteryVoltageSensor(coordinator, entry),
        PVoltageSensor(coordinator, entry),
        BatteryCurrentSensor(coordinator, entry),
        PowerWattsSensor(coordinator, entry),
        ChargeStageSensor(coordinator, entry),
        InternalStateSensor(coordinator, entry),
        RestReasonSensor(coordinator, entry),
        BatteryTemperatureSensor(coordinator, entry),
        FETTemperatureSensor(coordinator, entry),
        PCBTemperatureSensor(coordinator, entry),
        DailyAmpHoursSensor(coordinator, entry),
        LifetimeEnergySensor(coordinator, entry),
        LifetimeAmpHoursSensor(coordinator, entry),
        PVInputCurrentSensor(coordinator, entry),
        VOCMeasuredSensor(coordinator, entry),
        FloatTimeTodaySensor(coordinator, entry),
        AbsorbTimeRemainingSensor(coordinator, entry),
        EqualizeTimeRemainingSensor(coordinator, entry),
        MACAddressSensor(coordinator, entry),
        ModbusPortSensor(coordinator, entry),
        IPAddressSensor(coordinator, entry),
        GatewayAddressSensor(coordinator, entry),
        SubnetMaskSensor(coordinator, entry),
        DNSSensor1(coordinator, entry),
        DNSSensor2(coordinator, entry),
        StatusRollSensor(coordinator, entry),
        DailyEnergySensor(coordinator, entry),
        HighestInputVoltageSensor(coordinator, entry),
        LoggingIntervalSensor(coordinator, entry),
        SlidingCurrentLimitSensor(coordinator, entry),
        RestartTimeSensor(coordinator, entry),
        MatchPointShadowSensor(coordinator, entry),
    ]
    
    async_add_entities(sensors)


class MidniteSolarSensor(CoordinatorEntity[MidniteSolarUpdateCoordinator], SensorEntity):
    """Base class for all Midnite Solar sensors."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        
        # Create device info - will be updated dynamically when data becomes available
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def device_info(self):
        """Return dynamic device info with device ID and model if available."""
        return MidniteBaseEntityDescription.get_device_info(
            self.coordinator, self._entry, DOMAIN
        )

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        return None


class RestartTimeSensor(MidniteSolarSensor):
    """Representation of restart time sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Restart Time"
        self._attr_unique_id = f"{entry.entry_id}_restart_time"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["RESTART_TIME_MS"])
                if value is not None:
                    return value
        return None

    @property
    def extra_state_attributes(self) -> Optional[dict]:
        """Return additional state attributes."""
        attrs = {}
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["RESTART_TIME_MS"])
                if value is not None:
                    attrs["seconds"] = value / 1000.0
        return attrs


class MatchPointShadowSensor(MidniteSolarSensor):
    """Representation of match point shadow sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Match Point Shadow"
        self._attr_unique_id = f"{entry.entry_id}_match_point_shadow"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # Match point shadow is a step index (1-16), not a standard measurement
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = None
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MATCH_POINT_SHADOW"])
                if value is not None:
                    return value
        return None


class StatusRollSensor(MidniteSolarSensor):
    """Representation of status roll sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Status Roll"
        self._attr_unique_id = f"{entry.entry_id}_status_roll"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # Status roll is a 12-bit status value, not a standard measurement
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = None
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["STATUSROLL"])
                if value is not None:
                    # STATUSROLL formula: ([4113]>>12)+([4113]&0x0FFF) - 12-bit status value
                    return (value >> 12) + (value & 0x0FFF)
        return None


class DailyEnergySensor(MidniteSolarSensor):
    """Representation of daily energy sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Daily Energy"
        self._attr_unique_id = f"{entry.entry_id}_daily_energy"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_suggested_display_precision = 1
        # Daily energy is useful for monitoring, enable by default
        self._attr_entity_registry_enabled_default = True

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["KW_HOURS"])
                if value is not None:
                    return value / 10.0
        return None


class HighestInputVoltageSensor(MidniteSolarSensor):
    """Representation of highest input voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Highest Input Voltage"
        self._attr_unique_id = f"{entry.entry_id}_highest_input_voltage"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["HIGHEST_VINPUT_LOG"])
                if value is not None:
                    return value / 10.0
        return None


class LoggingIntervalSensor(MidniteSolarSensor):
    """Representation of logging interval sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Logging Interval"
        self._attr_unique_id = f"{entry.entry_id}_logging_interval"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            settings_data = self.coordinator.data["data"].get("settings")
            if settings_data:
                value = settings_data.get(REGISTER_MAP["MINUTE_LOG_INTERVAL_SEC"])
                if value is not None:
                    return value
        return None

    @property
    def extra_state_attributes(self) -> Optional[dict]:
        """Return additional state attributes."""
        attrs = {}
        if self.coordinator.data and "data" in self.coordinator.data:
            settings_data = self.coordinator.data["data"].get("settings")
            if settings_data:
                value = settings_data.get(REGISTER_MAP["MINUTE_LOG_INTERVAL_SEC"])
                if value is not None:
                    attrs["minutes"] = value / 60.0
        return attrs


class SlidingCurrentLimitSensor(MidniteSolarSensor):
    """Representation of sliding current limit sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Sliding Current Limit"
        self._attr_unique_id = f"{entry.entry_id}_sliding_current_limit"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            settings_data = self.coordinator.data["data"].get("settings")
            if settings_data:
                value = settings_data.get(REGISTER_MAP["SLIDING_CURRENT_LIMIT"])
                if value is not None:
                    return value / 10.0
        return None


class BatteryVoltageSensor(MidniteSolarSensor):
    """Representation of a battery voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Battery Voltage"
        self._attr_unique_id = f"{entry.entry_id}_batt_voltage"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DISP_AVG_VBATT"])
                if value is not None:
                    return value / 10.0
        return None


class PVoltageSensor(MidniteSolarSensor):
    """Representation of a PV input voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PV Voltage"
        self._attr_unique_id = f"{entry.entry_id}_pv_voltage"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DISP_AVG_VPV"])
                if value is not None:
                    return value / 10.0
        return None


class BatteryCurrentSensor(MidniteSolarSensor):
    """Representation of a battery current sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Battery Current"
        self._attr_unique_id = f"{entry.entry_id}_batt_current"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["IBATT_DISPLAY_S"])
                if value is not None:
                    # Current can be negative (discharging)
                    current_value = value / 10.0
                    # Convert to signed value if needed
                    if current_value > 32767:  # Check for negative values in unsigned register
                        current_value = current_value - 65536
                    
                    # Validate current range (-200A to 200A is reasonable)
                    if abs(current_value) > 200:
                        _LOGGER.warning(f"Invalid battery current reading: {current_value}A. Ignoring.")
                        return None
                    
                    return current_value
        return None


class PowerWattsSensor(MidniteSolarSensor):
    """Representation of a power output sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Power Output"
        self._attr_unique_id = f"{entry.entry_id}_power_watts"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WATTS"])
                return value
        return None


class ChargeStageSensor(MidniteSolarSensor):
    """Representation of a charge stage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Charge Stage"
        self._attr_unique_id = f"{entry.entry_id}_charge_stage"
        self._attr_device_class = SensorDeviceClass.ENUM
        # Don't set options here - we'll handle unknown values dynamically
        # Options will be populated from CHARGE_STAGES when needed

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                raw_value = status_data.get(REGISTER_MAP["COMBO_CHARGE_STAGE"])
                if raw_value is not None:
                    # Extract MSB (high byte) for charge stage
                    charge_stage_value = (raw_value >> 8) & 0xFF
                    return CHARGE_STAGES.get(charge_stage_value, f"Unknown ({charge_stage_value})")
        return None


class InternalStateSensor(MidniteSolarSensor):
    """Representation of an internal state sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Internal State"
        self._attr_unique_id = f"{entry.entry_id}_internal_state"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # Track last seen invalid rest reason to avoid repeated logging
        self._last_invalid_rest_reason: Optional[int] = None

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            diagnostics_data = self.coordinator.data["data"].get("diagnostics")
            
            if status_data:
                raw_value = status_data.get(REGISTER_MAP["COMBO_CHARGE_STAGE"])
                if raw_value is not None:
                    # Extract LSB (low byte) for internal state
                    internal_state_value = raw_value & 0xFF
                    internal_state = INTERNAL_STATES.get(internal_state_value, f"Unknown ({internal_state_value})")
                    
                    # If device is resting and we have diagnostics data, append rest reason
                    if internal_state == "Resting" and diagnostics_data:
                        rest_reason_value = diagnostics_data.get(REGISTER_MAP["REASON_FOR_RESTING"])
                        if rest_reason_value is not None:
                            # Extract only the low byte (8 bits) since this register contains an 8-bit value
                            extracted_value = rest_reason_value & 0xFF
                            _LOGGER.debug(f"REASON_FOR_RESTING raw: {rest_reason_value}, extracted LSB: {extracted_value}")
                            
                            # Validate value is in documented range (1-35)
                            if 1 <= extracted_value <= 35:
                                rest_reason = REST_REASONS.get(extracted_value, "Reason Unknown")
                                return f"{internal_state}: {rest_reason}"
                            else:
                                # Only log warning if this is a new invalid value or first occurrence
                                if self._last_invalid_rest_reason != extracted_value:
                                    _LOGGER.warning(f"Invalid rest reason code: {extracted_value}. Expected 1-35. Using 'Reason Unknown'")
                                    self._last_invalid_rest_reason = extracted_value
                                return f"{internal_state}: Reason Unknown"
                    
                    return internal_state
        return None


class DeviceTypeSensor(MidniteSolarSensor):
    """Representation of the device type sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Device Type"
        self._attr_unique_id = f"{entry.entry_id}_device_type"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["UNIT_ID"])
                if value is not None:
                    # Register 4101: [4101]MSB → PCB Rev, [4101]LSB → Unit Type
                    device_value = value & 0xFF  # Get LSB (unit type)
                    return DEVICE_TYPES.get(device_value, f"Unknown ({device_value})")
        return None


class RestReasonSensor(MidniteSolarSensor):
    """Representation of the rest reason sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Rest Reason"
        self._attr_unique_id = f"{entry.entry_id}_rest_reason"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Hide by default - info is in Internal State sensor
        # Track last seen invalid rest reason to avoid repeated logging
        self._last_invalid_rest_reason: Optional[int] = None

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            diagnostics_data = self.coordinator.data["data"].get("diagnostics")
            
            if status_data and diagnostics_data:
                # Get internal state from COMBO_CHARGE_STAGE register
                raw_value = status_data.get(REGISTER_MAP["COMBO_CHARGE_STAGE"])
                if raw_value is not None:
                    # Extract LSB (low byte) for internal state
                    internal_state_value = raw_value & 0xFF
                    internal_state = INTERNAL_STATES.get(internal_state_value, f"Unknown ({internal_state_value})")
                    
                    # Only show rest reason if device is actually resting
                    if internal_state == "Resting":
                        value = diagnostics_data.get(REGISTER_MAP["REASON_FOR_RESTING"])
                        if value is not None:
                            # Extract only the low byte (8 bits) since this register contains an 8-bit value
                            extracted_value = value & 0xFF
                            _LOGGER.debug(f"RestReasonSensor REASON_FOR_RESTING raw: {value}, extracted LSB: {extracted_value}")
                            
                            # Validate value is in documented range (1-35)
                            if 1 <= extracted_value <= 35:
                                return str(extracted_value)
                            else:
                                # Only log warning if this is a new invalid value or first occurrence
                                if self._last_invalid_rest_reason != extracted_value:
                                    _LOGGER.warning(f"Invalid rest reason code: {extracted_value}. Expected 1-35. Showing raw value")
                                    self._last_invalid_rest_reason = extracted_value
                                return str(value)  # Show raw number for debugging
                    else:
                        # Device is not resting
                        return "Not resting"
        return None


class TemperatureSensorBase(MidniteSolarSensor):
    """Base class for temperature sensors with shared validation logic."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._last_temp: Optional[float] = None
        self._last_time: Optional[float] = None
        # Track recent valid readings for basic sanity checking
        self._recent_readings: list[float] = []
        self._max_recent_readings = 20  # Keep last 20 valid readings

    def _validate_temperature(self, value: int, sensor_name: str) -> Optional[float]:
        """
        Validate temperature reading with range and rate-of-change checks.
        Uses a more robust approach that doesn't rely on statistical outliers.
        
        Args:
            value: Raw register value (scaled by 10)
            sensor_name: Name of the sensor for logging
            
        Returns:
            Validated temperature in Celsius, or None if invalid
        """
        # Convert raw value to temperature
        temp_value = value / 10.0
        # Check for negative temperature (two's complement)
        if value > 32767:
            temp_value = (value - 65536) / 10.0
        
        current_time = time.time()
        
        # Validate temperature range (-50°C to 150°C is reasonable)
        if temp_value < -50 or temp_value > 150:
            _LOGGER.warning(f"Invalid {sensor_name} reading: {temp_value}°C. Ignoring.")
            return None
        
        # Check for sudden temperature changes
        # Use a more reasonable threshold: 2°C per second (120°C per minute)
        if self._last_temp is not None and self._last_time is not None:
            time_diff = current_time - self._last_time
            if time_diff > 0:  # Avoid division by zero
                temp_change_rate = abs(temp_value - self._last_temp) / time_diff
                # Allow up to 2°C per second (reasonable for real-world temperature changes)
                if temp_change_rate > 2.0:
                    _LOGGER.warning(
                        f"Sudden {sensor_name} change detected: {self._last_temp}°C -> {temp_value}°C "
                        f"({temp_change_rate:.2f}°C/s over {time_diff:.1f}s). Possible sensor error. Ignoring reading."
                    )
                    return None
        
        # Track recent readings for basic sanity checking
        self._recent_readings.append(temp_value)
        if len(self._recent_readings) > self._max_recent_readings:
            self._recent_readings.pop(0)
        
        # Update last values
        self._last_temp = temp_value
        self._last_time = current_time
        
        return temp_value


class BatteryTemperatureSensor(TemperatureSensorBase):
    """Representation of a battery temperature sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Battery Temperature"
        self._attr_unique_id = f"{entry.entry_id}_batt_temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            temps_data = self.coordinator.data["data"].get("temperatures")
            if temps_data:
                value = temps_data.get(REGISTER_MAP["BATT_TEMPERATURE"])
                if value is not None:
                    return self._validate_temperature(value, "battery temperature")
        return None


class FETTemperatureSensor(TemperatureSensorBase):
    """Representation of a FET temperature sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "FET Temperature"
        self._attr_unique_id = f"{entry.entry_id}_fet_temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            temps_data = self.coordinator.data["data"].get("temperatures")
            if temps_data:
                value = temps_data.get(REGISTER_MAP["FET_TEMPERATURE"])
                if value is not None:
                    return self._validate_temperature(value, "FET temperature")
        return None


class PCBTemperatureSensor(TemperatureSensorBase):
    """Representation of a PCB temperature sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PCB Temperature"
        self._attr_unique_id = f"{entry.entry_id}_pcb_temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            temps_data = self.coordinator.data["data"].get("temperatures")
            if temps_data:
                value = temps_data.get(REGISTER_MAP["PCB_TEMPERATURE"])
                if value is not None:
                    return self._validate_temperature(value, "PCB temperature")
        return None


class DailyAmpHoursSensor(MidniteSolarSensor):
    """Representation of daily amp-hours sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Daily Amp-Hours"
        self._attr_unique_id = f"{entry.entry_id}_daily_ah"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # Use no device class for amp-hours (not a standard HA device class)
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = "Ah"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_suggested_display_precision = 0
        # Daily amp-hours is less commonly used, disable by default
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            energy_data = self.coordinator.data["data"].get("energy")
            if energy_data:
                value = energy_data.get(REGISTER_MAP["AMP_HOURS_DAILY"])
                if value is not None:
                    # Value is already in amp-hours from the register
                    return float(value)
        return None


class LifetimeEnergySensor(MidniteSolarSensor):
    """Representation of lifetime energy sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Lifetime Energy"
        self._attr_unique_id = f"{entry.entry_id}_lifetime_energy"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_suggested_display_precision = 1
        # Lifetime energy is important for monitoring, enable by default
        self._attr_entity_registry_enabled_default = True

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            energy_data = self.coordinator.data["data"].get("energy")
            if energy_data:
                low_value = energy_data.get(REGISTER_MAP["LIFETIME_KW_HOURS_1"])
                high_value = energy_data.get(REGISTER_MAP["LIFETIME_KW_HOURS_1"] + 1)
                if low_value is not None and high_value is not None:
                    value = (high_value << 16) | low_value
                    return value / 10.0
        return None


class LifetimeAmpHoursSensor(MidniteSolarSensor):
    """Representation of lifetime amp-hours sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Lifetime Amp-Hours"
        self._attr_unique_id = f"{entry.entry_id}_lifetime_ah"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # Use no device class for amp-hours (not a standard HA device class)
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = "Ah"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_suggested_display_precision = 1
        # Lifetime amp-hours is less commonly used, disable by default
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            energy_data = self.coordinator.data["data"].get("energy")
            if energy_data:
                low_value = energy_data.get(REGISTER_MAP["LIFETIME_AMP_HOURS_1"])
                high_value = energy_data.get(REGISTER_MAP["LIFETIME_AMP_HOURS_1"] + 1)
                if low_value is not None and high_value is not None:
                    value = (high_value << 16) | low_value
                    # Value is in amp-hours from the register (divided by 10 for precision)
                    return float(value) / 10.0
        return None


class PVInputCurrentSensor(MidniteSolarSensor):
    """Representation of PV input current sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PV Input Current"
        self._attr_unique_id = f"{entry.entry_id}_pv_current"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["PV_INPUT_CURRENT"])
                if value is not None:
                    current_value = value / 10.0
                    # Check for negative values
                    if current_value > 32767:
                        current_value = current_value - 65536
                    
                    # Validate current range (-100A to 100A is reasonable)
                    if abs(current_value) > 100:
                        _LOGGER.warning(f"Invalid PV input current reading: {current_value}A. Ignoring.")
                        return None
                    
                    return current_value
        return None


class VOCMeasuredSensor(MidniteSolarSensor):
    """Representation of last measured VOC sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Last Measured VOC"
        self._attr_unique_id = f"{entry.entry_id}_voc_measured"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["VOC_LAST_MEASURED"])
                if value is not None:
                    return value / 10.0
        return None


class FloatTimeTodaySensor(MidniteSolarSensor):
    """Representation of float time today sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Float Time Today"
        self._attr_unique_id = f"{entry.entry_id}_float_time_today"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.DURATION
        # Display in minutes for better readability
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Time is in whole minutes, no decimal precision needed
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            time_data = self.coordinator.data["data"].get("time_settings")
            if time_data:
                seconds = time_data.get(REGISTER_MAP["FLOAT_TIME_TODAY_SEC"])
                if seconds is not None:
                    # Store value in minutes for display
                    return seconds / 60.0
        return None

    @property
    def extra_state_attributes(self) -> Optional[dict]:
        """Return additional state attributes."""
        attrs = {}
        if self.coordinator.data and "data" in self.coordinator.data:
            time_data = self.coordinator.data["data"].get("time_settings")
            if time_data:
                seconds = time_data.get(REGISTER_MAP["FLOAT_TIME_TODAY_SEC"])
                if seconds is not None:
                    attrs["seconds"] = seconds
                    attrs["hours"] = (seconds / 60.0) / 60.0
        return attrs


class AbsorbTimeRemainingSensor(MidniteSolarSensor):
    """Representation of absorb time remaining sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Absorb Time Remaining"
        self._attr_unique_id = f"{entry.entry_id}_absorb_time_remaining"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.DURATION
        # Display in minutes for better readability
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Time is in whole minutes, no decimal precision needed
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            time_data = self.coordinator.data["data"].get("time_settings")
            if time_data:
                seconds = time_data.get(REGISTER_MAP["ABSORB_TIME"])
                if seconds is not None:
                    # Store value in minutes for display
                    return seconds / 60.0
        return None

    @property
    def extra_state_attributes(self) -> Optional[dict]:
        """Return additional state attributes."""
        attrs = {}
        if self.coordinator.data and "data" in self.coordinator.data:
            time_data = self.coordinator.data["data"].get("time_settings")
            if time_data:
                seconds = time_data.get(REGISTER_MAP["ABSORB_TIME"])
                if seconds is not None:
                    attrs["seconds"] = seconds
                    attrs["hours"] = (seconds / 60.0) / 60.0
        return attrs


class EqualizeTimeRemainingSensor(MidniteSolarSensor):
    """Representation of equalize time remaining sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Equalize Time Remaining"
        self._attr_unique_id = f"{entry.entry_id}_equalize_time_remaining"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.DURATION
        # Display in minutes for better readability
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Time is in whole minutes, no decimal precision needed
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            time_data = self.coordinator.data["data"].get("time_settings")
            if time_data:
                seconds = time_data.get(REGISTER_MAP["EQUALIZE_TIME"])
                if seconds is not None:
                    # Store value in minutes for display
                    return seconds / 60.0
        return None

    @property
    def extra_state_attributes(self) -> Optional[dict]:
        """Return additional state attributes."""
        attrs = {}
        if self.coordinator.data and "data" in self.coordinator.data:
            time_data = self.coordinator.data["data"].get("time_settings")
            if time_data:
                seconds = time_data.get(REGISTER_MAP["EQUALIZE_TIME"])
                if seconds is not None:
                    attrs["seconds"] = seconds
                    attrs["hours"] = (seconds / 60.0) / 60.0
        return attrs


class MACAddressSensor(MidniteSolarSensor):
    """Representation of MAC address sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MAC Address"
        self._attr_unique_id = f"{entry.entry_id}_mac_address"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                part1 = device_info_data.get(REGISTER_MAP["MAC_ADDRESS_PART_1"])
                part2 = device_info_data.get(REGISTER_MAP["MAC_ADDRESS_PART_2"])
                part3 = device_info_data.get(REGISTER_MAP["MAC_ADDRESS_PART_3"])
                if part1 is not None and part2 is not None and part3 is not None:
                    # MAC address format: [4108]MSB:[4108]LSB:[4107]MSB:[4107]LSB:[4106]MSB:[4106]LSB
                    # Each register contains 2 bytes (16 bits)
                    mac_bytes = [
                        (part3 >> 8) & 0xFF,      # MSB of part3 (register 4108)
                        part3 & 0xFF,              # LSB of part3 (register 4108)
                        (part2 >> 8) & 0xFF,      # MSB of part2 (register 4107)
                        part2 & 0xFF,              # LSB of part2 (register 4107)
                        (part1 >> 8) & 0xFF,      # MSB of part1 (register 4106)
                        part1 & 0xFF,              # LSB of part1 (register 4106)
                    ]
                    return ":".join(f"{byte:02X}" for byte in mac_bytes)
        return None





class ModbusPortSensor(MidniteSolarSensor):
    """Representation of Modbus port sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Modbus Port"
        self._attr_unique_id = f"{entry.entry_id}_modbus_port"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            settings = self.coordinator.data["data"].get("settings")
            if settings:
                value = settings.get(REGISTER_MAP["MODBUS_PORT_REGISTER"])
                return value
        return None


class IPAddressSensor(MidniteSolarSensor):
    """Representation of IP address sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "IP Address"
        self._attr_unique_id = f"{entry.entry_id}_ip_address"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            network = self.coordinator.data["data"].get("network")
            if network:
                part1 = network.get(REGISTER_MAP["IP_ADDRESS_LSB_1"])
                part2 = network.get(REGISTER_MAP["IP_ADDRESS_LSB_2"])
                if part1 is not None and part2 is not None:
                    # IP address format: [20483]MSB:[20483]LSB:[20482]MSB:[20482]LSB
                    # Each register contains 2 bytes (16 bits)
                    octets = []
                    
                    def get_octets(reg_value):
                        """Extract two octets from a 16-bit register value."""
                        return [(reg_value >> 8) & 0xFF, reg_value & 0xFF]
                    
                    octets.extend(get_octets(part2))  # Register 20483 (LSB_1)
                    octets.extend(get_octets(part1))  # Register 20482 (LSB_2)
                    
                    # Reverse the octet order to get correct IP format
                    return ".".join(str(octet) for octet in reversed(octets[:4]))
        return None


class GatewayAddressSensor(MidniteSolarSensor):
    """Representation of gateway address sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Gateway Address"
        self._attr_unique_id = f"{entry.entry_id}_gateway_address"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            network = self.coordinator.data["data"].get("network")
            if network:
                part1 = network.get(REGISTER_MAP["GATEWAY_ADDRESS_LSB_1"])
                part2 = network.get(REGISTER_MAP["GATEWAY_ADDRESS_LSB_2"])
                if part1 is not None and part2 is not None:
                    # Gateway address format: [20485]MSB:[20485]LSB:[20484]MSB:[20484]LSB
                    octets = []
                    
                    def get_octets(reg_value):
                        """Extract two octets from a 16-bit register value."""
                        return [(reg_value >> 8) & 0xFF, reg_value & 0xFF]
                    
                    octets.extend(get_octets(part2))  # Register 20485 (LSB_1)
                    octets.extend(get_octets(part1))  # Register 20484 (LSB_2)
                    
                    # Reverse the octet order to get correct IP format
                    return ".".join(str(octet) for octet in reversed(octets[:4]))
        return None


class SubnetMaskSensor(MidniteSolarSensor):
    """Representation of subnet mask sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Subnet Mask"
        self._attr_unique_id = f"{entry.entry_id}_subnet_mask"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            network = self.coordinator.data["data"].get("network")
            if network:
                part1 = network.get(REGISTER_MAP["SUBNET_MASK_LSB_1"])
                part2 = network.get(REGISTER_MAP["SUBNET_MASK_LSB_2"])
                if part1 is not None and part2 is not None:
                    # Subnet mask format: [20487]MSB:[20487]LSB:[20486]MSB:[20486]LSB
                    octets = []
                    
                    def get_octets(reg_value):
                        """Extract two octets from a 16-bit register value."""
                        return [(reg_value >> 8) & 0xFF, reg_value & 0xFF]
                    
                    octets.extend(get_octets(part2))  # Register 20487 (LSB_1)
                    octets.extend(get_octets(part1))  # Register 20486 (LSB_2)
                    
                    # Reverse the octet order to get correct IP format
                    return ".".join(str(octet) for octet in reversed(octets[:4]))
        return None


class DNSSensor1(MidniteSolarSensor):
    """Representation of primary DNS server sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DNS Server 1"
        self._attr_unique_id = f"{entry.entry_id}_dns1"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            network = self.coordinator.data["data"].get("network")
            if network:
                part1 = network.get(REGISTER_MAP["DNS_1_LSB_1"])
                part2 = network.get(REGISTER_MAP["DNS_1_LSB_2"])
                if part1 is not None and part2 is not None:
                    # DNS 1 format: [20489]MSB:[20489]LSB:[20488]MSB:[20488]LSB
                    octets = []
                    
                    def get_octets(reg_value):
                        """Extract two octets from a 16-bit register value."""
                        return [(reg_value >> 8) & 0xFF, reg_value & 0xFF]
                    
                    octets.extend(get_octets(part2))  # Register 20489 (LSB_1)
                    octets.extend(get_octets(part1))  # Register 20488 (LSB_2)
                    
                    # Reverse the octet order to get correct IP format
                    return ".".join(str(octet) for octet in reversed(octets[:4]))
        return None


class DNSSensor2(MidniteSolarSensor):
    """Representation of secondary DNS server sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DNS Server 2"
        self._attr_unique_id = f"{entry.entry_id}_dns2"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            network = self.coordinator.data["data"].get("network")
            if network:
                part1 = network.get(REGISTER_MAP["DNS_2_LSB_1"])
                part2 = network.get(REGISTER_MAP["DNS_2_LSB_2"])
                if part1 is not None and part2 is not None:
                    # DNS 2 format: [20491]MSB:[20491]LSB:[20490]MSB:[20490]LSB
                    octets = []
                    
                    def get_octets(reg_value):
                        """Extract two octets from a 16-bit register value."""
                        return [(reg_value >> 8) & 0xFF, reg_value & 0xFF]
                    
                    octets.extend(get_octets(part2))  # Register 20491 (LSB_1)
                    octets.extend(get_octets(part1))  # Register 20490 (LSB_2)
                    
                    # Reverse the octet order to get correct IP format
                    return ".".join(str(octet) for octet in reversed(octets[:4]))
        return None
