"""Support for Midnite Solar sensor platform."""

from __future__ import annotations

import logging
from typing import Any, Optional

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
        """Return dynamic device info with serial number if available."""
        # Try to get serial number from coordinator data
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                serial_msb = device_info_data.get(REGISTER_MAP["SERIAL_NUMBER_MSB"])
                serial_lsb = device_info_data.get(REGISTER_MAP["SERIAL_NUMBER_LSB"])
                if serial_msb is not None and serial_lsb is not None:
                    serial_number = (serial_msb << 16) | serial_lsb
                    return {
                        "identifiers": {(DOMAIN, str(serial_number))},
                        "name": f"Midnite Solar ({serial_number})",
                        "manufacturer": "Midnite Solar",
                    }
        
        # Fallback to entry_id if serial number not available
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
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
        self._attr_options = list(CHARGE_STAGES.values())

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
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_options = list(INTERNAL_STATES.values())

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                raw_value = status_data.get(REGISTER_MAP["COMBO_CHARGE_STAGE"])
                if raw_value is not None:
                    # Extract LSB (low byte) for internal state
                    internal_state_value = raw_value & 0xFF
                    return INTERNAL_STATES.get(internal_state_value, f"Unknown ({internal_state_value})")
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

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            diagnostics_data = self.coordinator.data["data"].get("diagnostics")
            if diagnostics_data:
                value = diagnostics_data.get(REGISTER_MAP["REASON_FOR_RESTING"])
                if value is not None:
                    return REST_REASONS.get(value, f"Unknown ({value})")
        return None


class BatteryTemperatureSensor(MidniteSolarSensor):
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
                    temp_value = value / 10.0
                    # Check for negative temperature (two's complement)
                    if temp_value > 32767:
                        temp_value = temp_value - 65536
                    
                    # Validate temperature range (-50°C to 150°C is reasonable for batteries)
                    if value < -50 or value > 150:
                        _LOGGER.warning(f"Invalid battery temperature reading: {temp_value}°C. Ignoring.")
                        return None
                    
                    return temp_value
        return None


class FETTemperatureSensor(MidniteSolarSensor):
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
                    temp_value = value / 10.0
                    # Check for negative temperature (two's complement)
                    if temp_value > 32767:
                        temp_value = temp_value - 65536
                    
                    # Validate temperature range (-50°C to 150°C is reasonable)
                    if temp_value < -50 or temp_value > 150:
                        _LOGGER.warning(f"Invalid FET temperature reading: {temp_value}°C. Ignoring.")
                        return None
                    
                    return temp_value
        return None


class PCBTemperatureSensor(MidniteSolarSensor):
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
                    temp_value = value / 10.0
                    # Check for negative temperature (two's complement)
                    if temp_value > 32767:
                        temp_value = temp_value - 65536
                    
                    # Validate temperature range (-50°C to 150°C is reasonable)
                    if temp_value < -50 or temp_value > 150:
                        _LOGGER.warning(f"Invalid PCB temperature reading: {temp_value}°C. Ignoring.")
                        return None
                    
                    return temp_value
        return None


class DailyAmpHoursSensor(MidniteSolarSensor):
    """Representation of daily amp-hours sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Daily Amp-Hours"
        self._attr_unique_id = f"{entry.entry_id}_daily_ah"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            energy_data = self.coordinator.data["data"].get("energy")
            if energy_data:
                value = energy_data.get(REGISTER_MAP["AMP_HOURS_DAILY"])
                if value is not None:
                    # Convert Ah to kWh (1Ah = 0.001kWh for 12V system, but we'll keep as is)
                    return value / 1000.0
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
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

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
                    return value / 10.0
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
