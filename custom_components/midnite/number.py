"""Support for Midnite Solar number platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfElectricCurrent, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPES, DOMAIN, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar numbers."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    numbers = [
        MINUTE_LOG_INTERVAL_SECNumber(coordinator, entry),
        MODBUS_PORT_REGISTERNumber(coordinator, entry),
        BATTERY_OUTPUT_CURRENT_LIMITNumber(coordinator, entry),
        ABSORB_SETPOINT_VOLTAGENumber(coordinator, entry),
        FLOAT_VOLTAGE_SETPOINTNumber(coordinator, entry),
        EQUALIZE_VOLTAGE_SETPOINTNumber(coordinator, entry),
        ABSORB_TIME_EEPROMNumber(coordinator, entry),
        MAX_BATTERY_TEMP_COMP_VOLTAGENumber(coordinator, entry),
        MIN_BATTERY_TEMP_COMP_VOLTAGENumber(coordinator, entry),
        BATTERY_TEMP_COMP_VALUENumber(coordinator, entry),
        EQUALIZE_TIME_EEPROMNumber(coordinator, entry),
        EQUALIZE_INTERVAL_DAYS_EEPROMNumber(coordinator, entry),
        AUX1_VOLTS_LO_ABSNumber(coordinator, entry),
        AUX1_DELAY_T_MSNumber(coordinator, entry),
        AUX1_HOLD_T_MSNumber(coordinator, entry),
        AUX2_PWM_VWIDTHNumber(coordinator, entry),
        AUX1_VOLTS_HI_ABSNumber(coordinator, entry),
        AUX2_VOLTS_HI_ABSNumber(coordinator, entry),
        VBATT_OFFSETNumber(coordinator, entry),
        VPV_OFFSETNumber(coordinator, entry),
        FACTORY_VBATT_OFFSET_EEPANumber(coordinator, entry),
    ]
    
    async_add_entities(numbers)


class MidniteSolarNumber(CoordinatorEntity[MidniteSolarUpdateCoordinator], NumberEntity):
    """Base class for all Midnite Solar numbers."""

    _attr_native_min_value: float | None = None
    _attr_native_max_value: float | None = None
    _attr_native_step: float | None = None

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator)
        self._entry = entry
        
        # Create device info - use serial number if available, otherwise use entry_id
        # We'll update this dynamically when data becomes available via property override
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def device_info(self):
        """Return dynamic device info with device ID and model if available."""
        # Try to get device ID from coordinator data (registers 4111-4112)
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                device_id_lsw = device_info_data.get(REGISTER_MAP["DEVICE_ID_LSW"])
                device_id_msw = device_info_data.get(REGISTER_MAP["DEVICE_ID_MSW"])
                if device_id_lsw is not None and device_id_msw is not None:
                    device_id = (device_id_msw << 16) | device_id_lsw
                    # Try to get device model from UNIT_ID register
                    unit_id_value = device_info_data.get(REGISTER_MAP["UNIT_ID"])
                    if unit_id_value is not None:
                        device_type = unit_id_value & 0xFF  # Get LSB (unit type)
                        model = DEVICE_TYPES.get(device_type, f"Unknown ({device_type})")
                    else:
                        model = "Midnite Solar Device"
                    
                    return {
                        "identifiers": {(DOMAIN, str(device_id))},
                        "name": f"{model} ({device_id})",
                        "manufacturer": "Midnite Solar",
                        "model": model,
                    }
        
        # Fallback to entry_id if serial number not available
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return None


class MINUTE_LOG_INTERVAL_SECNumber(MidniteSolarNumber):
    """Representation of a data logging interval (min 60 s) number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Minute Log Interval Sec"
        self._attr_unique_id = f"{entry.entry_id}_minute_log_interval_sec_number"
        self.register_address = 4136
        self._attr_device_class = "duration"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:clock"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 86400
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value
        return None


class MODBUS_PORT_REGISTERNumber(MidniteSolarNumber):
    """Representation of a modbus tcp port (default 502) number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Modbus Port Register"
        self._attr_unique_id = f"{entry.entry_id}_modbus_port_register_number"
        self.register_address = 4137
        self._attr_icon = "mdi:lan"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 65535
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value
        return None


class BATTERY_OUTPUT_CURRENT_LIMITNumber(MidniteSolarNumber):
    """Representation of a battery current limit (e.g., 23.4 a = 234) number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Battery Output Current Limit"
        self._attr_unique_id = f"{entry.entry_id}_battery_output_current_limit_number"
        self.register_address = 4148
        self._attr_device_class = "current"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_icon = "mdi:current-dc"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 1000
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class ABSORB_SETPOINT_VOLTAGENumber(MidniteSolarNumber):
    """Representation of a battery absorb stage set point voltage number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Absorb Setpoint Voltage"
        self._attr_unique_id = f"{entry.entry_id}_absorb_setpoint_voltage_number"
        self.register_address = 4149
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:tune"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class FLOAT_VOLTAGE_SETPOINTNumber(MidniteSolarNumber):
    """Representation of a battery float stage set point voltage number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Float Voltage Setpoint"
        self._attr_unique_id = f"{entry.entry_id}_float_voltage_setpoint_number"
        self.register_address = 4150
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:tune"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class EQUALIZE_VOLTAGE_SETPOINTNumber(MidniteSolarNumber):
    """Representation of a battery equalize stage set point voltage number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Equalize Voltage Setpoint"
        self._attr_unique_id = f"{entry.entry_id}_equalize_voltage_setpoint_number"
        self.register_address = 4151
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:tune"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class ABSORB_TIME_EEPROMNumber(MidniteSolarNumber):
    """Representation of a absorb setpoint time for batteries number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Absorb Time Eeprom"
        self._attr_unique_id = f"{entry.entry_id}_absorb_time_eeprom_number"
        self.register_address = 4154
        self._attr_device_class = "duration"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:clock-edit"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 86400
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value
        return None


class MAX_BATTERY_TEMP_COMP_VOLTAGENumber(MidniteSolarNumber):
    """Representation of a highest charge voltage limited when using temp sensor number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Max Battery Temp Comp Voltage"
        self._attr_unique_id = f"{entry.entry_id}_max_battery_temp_comp_voltage_number"
        self.register_address = 4155
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:thermometer-plus"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class MIN_BATTERY_TEMP_COMP_VOLTAGENumber(MidniteSolarNumber):
    """Representation of a lowest charge voltage limited when using temp sensor number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Min Battery Temp Comp Voltage"
        self._attr_unique_id = f"{entry.entry_id}_min_battery_temp_comp_voltage_number"
        self.register_address = 4156
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:thermometer-minus"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class BATTERY_TEMP_COMP_VALUENumber(MidniteSolarNumber):
    """Representation of a temperature compensation value per 2 v cell number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Battery Temp Comp Value"
        self._attr_unique_id = f"{entry.entry_id}_battery_temp_comp_value_number"
        self.register_address = 4157
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:snowflake-thermometer"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class EQUALIZE_TIME_EEPROMNumber(MidniteSolarNumber):
    """Representation of a initialize equalize stage duration number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Equalize Time Eeprom"
        self._attr_unique_id = f"{entry.entry_id}_equalize_time_eeprom_number"
        self.register_address = 4162
        self._attr_device_class = "duration"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:clock-edit"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 86400
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value
        return None


class EQUALIZE_INTERVAL_DAYS_EEPROMNumber(MidniteSolarNumber):
    """Representation of a days between equalize stages (auto eq) number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Equalize Interval Days Eeprom"
        self._attr_unique_id = f"{entry.entry_id}_equalize_interval_days_eeprom_number"
        self.register_address = 4163
        self._attr_native_unit_of_measurement = "days"
        self._attr_icon = "mdi:calendar-range"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 365
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value
        return None


class AUX1_VOLTS_LO_ABSNumber(MidniteSolarNumber):
    """Representation of a aux 1 low absolute threshold voltage number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Au 1 Volts Lo Abs"
        self._attr_unique_id = f"{entry.entry_id}_aux1_volts_lo_abs_number"
        self.register_address = 4166
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:gauge-low"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class AUX1_DELAY_T_MSNumber(MidniteSolarNumber):
    """Representation of a aux 1 delay before asserting number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Au 1 Delay T Ms"
        self._attr_unique_id = f"{entry.entry_id}_aux1_delay_t_ms_number"
        self.register_address = 4167
        self._attr_device_class = "duration"
        self._attr_native_unit_of_measurement = "ms"
        self._attr_icon = "mdi:timer-sand"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 65535
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value
        return None


class AUX1_HOLD_T_MSNumber(MidniteSolarNumber):
    """Representation of a aux 1 hold before de-asserting number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Au 1 Hold T Ms"
        self._attr_unique_id = f"{entry.entry_id}_aux1_hold_t_ms_number"
        self.register_address = 4168
        self._attr_device_class = "duration"
        self._attr_native_unit_of_measurement = "ms"
        self._attr_icon = "mdi:timer-sand"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 65535
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value
        return None


class AUX2_PWM_VWIDTHNumber(MidniteSolarNumber):
    """Representation of a voltage range for aux 2 pwm (0-5 v) number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Au 2 Pwm Vwidth"
        self._attr_unique_id = f"{entry.entry_id}_aux2_pwm_vwidth_number"
        self.register_address = 4169
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:sine-wave"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class AUX1_VOLTS_HI_ABSNumber(MidniteSolarNumber):
    """Representation of a aux 1 high absolute threshold voltage number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Au 1 Volts Hi Abs"
        self._attr_unique_id = f"{entry.entry_id}_aux1_volts_hi_abs_number"
        self.register_address = 4172
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:gauge-high"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class AUX2_VOLTS_HI_ABSNumber(MidniteSolarNumber):
    """Representation of a aux 2 high absolute threshold voltage number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Au 2 Volts Hi Abs"
        self._attr_unique_id = f"{entry.entry_id}_aux2_volts_hi_abs_number"
        self.register_address = 4173
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:gauge-high"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class VBATT_OFFSETNumber(MidniteSolarNumber):
    """Representation of a battery voltage offset tweak (signed) number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Vbatt Offset"
        self._attr_unique_id = f"{entry.entry_id}_vbatt_offset_number"
        self.register_address = 4189
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:tune-vertical"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class VPV_OFFSETNumber(MidniteSolarNumber):
    """Representation of a pv input voltage offset tweak (signed) number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Vpv Offset"
        self._attr_unique_id = f"{entry.entry_id}_vpv_offset_number"
        self.register_address = 4190
        self._attr_device_class = "voltage"
        self._attr_native_unit_of_measurement = "V"
        self._attr_icon = "mdi:tune-vertical"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 200
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value / 10.0
        return None


class FACTORY_VBATT_OFFSET_EEPANumber(MidniteSolarNumber):
    """Representation of a factory v battery offset calibration number."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "Factory Vbatt Offset Eepa"
        self._attr_unique_id = f"{entry.entry_id}_factory_vbatt_offset_eepa_number"
        self.register_address = 4300
        self._attr_icon = "mdi:tune"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 65535
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
            return value
        return None
