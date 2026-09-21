"""Support for Midnite Solar sensor platform."""

from __future__ import annotations

import logging
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

from .const import (
    CHARGE_STAGES,
    FIRMWARE_REVISION_SENSORS,
    FIRMWARE_VERSION_SENSORS,
    CLASSIC_STATUS_SENSORS,
    DEVICE_TYPES,
    DOMAIN,
    INTERNAL_STATES,
    REGISTER_MAP,
    REST_REASONS,
)
from .coordinator import MidniteSolarUpdateCoordinator
from .register_values import (
    TemperatureFilter,
    combine32,
    format_ipv4,
    format_mac_from_registers,
    scaled_value,
    version_from_register,
)

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
        # The Classic's own firmware, which is what support asks for.
        *(
            FirmwareVersionSensor(coordinator, entry, key, label, describes)
            for key, label, describes in FIRMWARE_VERSION_SENSORS
        ),
        *(
            FirmwareRevisionSensor(coordinator, entry, low_key, high_key, label)
            for low_key, high_key, label in FIRMWARE_REVISION_SENSORS
        ),
        # What the Classic itself is regulating to, and why it reset.
        *(
            ClassicStatusSensor(coordinator, entry, setting)
            for setting in CLASSIC_STATUS_SENSORS
        ),
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

    def _group(self, name: str) -> dict:
        """Return one register group from the last update, or an empty dict."""
        if not self.coordinator.data or "data" not in self.coordinator.data:
            return {}
        return self.coordinator.data["data"].get(name) or {}

    @staticmethod
    def _register(group: dict, key: str) -> Optional[int]:
        """Return one register by its const name, or None if it was not read."""
        from .const import REGISTER_MAP

        return group.get(REGISTER_MAP[key])

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
    """The 12-bit status value of register 4113, and its 4-bit roll counter.

    "4113 | R | StatusRoll | ([4113]>>12)Count + ([4113]& 0x0fff) Value | Various
    12 bit values changes once per second. Hi 4 bits = count". The "+" in that
    formula is the map putting two fields in one line, not an instruction to add
    them: the high 4 bits are how many times the value has rolled and the low 12
    bits are the value. Adding them produced a third number that is neither, so a
    value of 1 with a count of 3 read as 4.
    """

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Status Roll"
        self._attr_unique_id = f"{entry.entry_id}_status_roll"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # A status value that changes once per second is a code, not a quantity:
        # no device class and no statistics.
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = None
        self._attr_state_class = None
        self._attr_entity_registry_enabled_default = False  # Disable by default

    def _raw(self):
        """Return register 4113, or None if it has not been read."""
        return self._register(self._group("status"), "STATUSROLL")

    @property
    def native_value(self) -> Optional[int]:
        """Return the 12-bit value the register carries."""
        value = self._raw()
        if value is None:
            return None
        return value & 0x0FFF

    @property
    def extra_state_attributes(self) -> Optional[dict]:
        """Return the roll counter, which is the other half of the register."""
        value = self._raw()
        if value is None:
            return None
        return {"count": value >> 12, "raw": value}


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
                    # The map gives "[4152] Amps" with no divisor.
                    return float(value)
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
                    # The Classic reports current as tenths in a two's-complement
                    # 16-bit register, so it has to be read as signed BEFORE it is
                    # divided: a raw register divided by 10 is at most 6553.5, so a
                    # "> 32767" test placed after the divide can never fire and a
                    # discharge reading (e.g. -20.0 A = register 65336) would be
                    # thrown away as "invalid" every interval.
                    #
                    # No range check: the map gives "[4117] /10 Amps" with no range,
                    # and an invented ceiling silently drops readings a Classic 250
                    # can legitimately produce (the map's own rest reason 31 speaks
                    # of battery current past 90 A, and 200.0 A is a ordinary
                    # operating point). A discarded real value is worse than a
                    # displayed absurd one; the display is the Classic's own truth.
                    return scaled_value(value)
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
    """The Classic's own state: Table 4120-2, the low byte of register 4120.

    "4120 | R | ComboChargeStage | Charge Stage = [4120] MSB State = [4120] LSB".
    It used to append the rest reason while the Classic was resting, which put one
    quantity in two entities and made this sensor's history a function of something
    else: the reported state changed whenever the reason changed, so a graph of the
    Classic's states was really a graph of its reasons. The reason has had its own
    sensor since; the high byte of the same register is the charge stage sensor.
    """

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Internal State"
        self._attr_unique_id = f"{entry.entry_id}_internal_state"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Optional[str]:
        """Return the state named in Table 4120-2."""
        raw_value = self._register(self._group("status"), "COMBO_CHARGE_STAGE")
        if raw_value is None:
            return None
        state = raw_value & 0xFF
        return INTERNAL_STATES.get(state, f"Unknown ({state})")


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
    """Why the Classic went to rest: register 4275, decoded by Table 4275-1.

    "4275 | R | ReasonForResting | [4275] Reason number | Reason Classic went to
    Rest (See Table 4275-1)". The register keeps the last reason even after the
    Classic wakes up, so a reason shown while the Classic is running is history and
    not an explanation of what it is doing now; that is said instead of shown as if
    it were current. It used to be a hidden duplicate of the text the internal state
    sensor was appending, which left the reason with no entity of its own.
    """

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Rest Reason"
        self._attr_unique_id = f"{entry.entry_id}_rest_reason"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Optional[str]:
        """Return the reason from Table 4275-1, or say it is not resting."""
        reason = self._register(self._group("diagnostics"), "REASON_FOR_RESTING")
        if reason is None:
            return None
        state = self._register(self._group("status"), "COMBO_CHARGE_STAGE")
        if state is not None and (state & 0xFF) != 0:
            return "Not resting"
        return REST_REASONS.get(reason, f"Unknown reason ({reason})")


class TemperatureSensorBase(MidniteSolarSensor):
    """Base class for the temperature sensors, with noise filtering.

    A Classic reports nonsense when the battery temperature probe is unplugged
    or a read is torn, and that garbage lands in the history. Readings outside
    the plausible range, and readings far from the median of the recent ones,
    are dropped. The filter gives up after a handful of rejections and starts a
    new baseline, so a genuine change - or a filter that has it wrong - can
    never lock a sensor out of reporting.
    """

    _address_key: str = ""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._filter = TemperatureFilter()

    @property
    def native_value(self) -> Optional[float]:
        """Return the temperature, or None while a reading is rejected."""
        if not self.coordinator.data or "data" not in self.coordinator.data:
            return None
        temps_data = self.coordinator.data["data"].get("temperatures")
        if not temps_data:
            return None
        raw = temps_data.get(REGISTER_MAP[self._address_key])
        if raw is None:
            return None
        # The map gives "([4132] /10)" with negatives as two's complement.
        temperature = self._filter.apply(scaled_value(raw))
        if temperature is None:
            _LOGGER.warning(
                "%s: rejecting implausible reading %.1f °C", self.name, scaled_value(raw)
            )
        return temperature

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """Return how many readings in this run have been rejected."""
        return {"rejected_readings": self._filter.rejected}


class BatteryTemperatureSensor(TemperatureSensorBase):
    """Representation of a battery temperature sensor."""

    _address_key = "BATT_TEMPERATURE"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Battery Temperature"
        self._attr_unique_id = f"{entry.entry_id}_batt_temp"


class FETTemperatureSensor(TemperatureSensorBase):
    """Representation of a FET temperature sensor."""

    _address_key = "FET_TEMPERATURE"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "FET Temperature"
        self._attr_unique_id = f"{entry.entry_id}_fet_temp"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class PCBTemperatureSensor(TemperatureSensorBase):
    """Representation of a PCB temperature sensor."""

    _address_key = "PCB_TEMPERATURE"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PCB Temperature"
        self._attr_unique_id = f"{entry.entry_id}_pcb_temp"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


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
                    # The map's formula is "(([4127] << 16) + [4126]) kWh" with no
                    # divisor, but the Classic's own display shows one decimal place
                    # (bench: register 109917 reads as 10991.7 kWh). The register
                    # holds tenths of a kWh; divide by ten, as the daily total does.
                    return combine32(low_value, high_value) / 10.0
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
                    # The map gives "(([4129] << 16) + [4128]) Amp Hours" with no divisor.
                    return float(combine32(low_value, high_value))
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
                    # Same two's-complement tenths as the battery current, and
                    # same no-invented-range rule: the map gives "([4121] /10)"
                    # with no limits, so nothing is discarded here. A reading is
                    # shown as the Classic reports it.
                    return scaled_value(value)
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
                    # One decode path for the MAC (register_values), shared with
                    # the config flow so a displayed MAC and a unique id can
                    # never drift apart. Canonical form is lower case.
                    return format_mac_from_registers(part1, part2, part3)
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


class NetworkAddressSensor(MidniteSolarSensor):
    """A network address held in two registers.

    The map composes every one of these as
    "[20483]MSB . [20483]LSB . [20482]MSB . [20482]LSB", but a real Classic stores
    it reversed (bench-confirmed): the lower register (the _LOW_WORD key) carries
    the first two octets and each register reads low byte first. In const.py each
    pair is `..._LOW_WORD` (the lower register, first two octets) and
    `..._HIGH_WORD` (the higher register, last two). format_ipv4 does the reversal.
    """

    _low_key: str = ""
    _high_key: str = ""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def native_value(self) -> Optional[str]:
        """Return the dotted quad address."""
        if not self.coordinator.data or "data" not in self.coordinator.data:
            return None
        network = self.coordinator.data["data"].get("network")
        if not network:
            return None
        low = network.get(REGISTER_MAP[self._low_key])
        high = network.get(REGISTER_MAP[self._high_key])
        if low is None or high is None:
            return None
        return format_ipv4(low, high)


class IPAddressSensor(NetworkAddressSensor):
    """Representation of IP address sensor."""

    _low_key = "IP_ADDRESS_LOW_WORD"
    _high_key = "IP_ADDRESS_HIGH_WORD"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "IP Address"
        self._attr_unique_id = f"{entry.entry_id}_ip_address"


class GatewayAddressSensor(NetworkAddressSensor):
    """Representation of gateway address sensor."""

    _low_key = "GATEWAY_ADDRESS_LOW_WORD"
    _high_key = "GATEWAY_ADDRESS_HIGH_WORD"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Gateway Address"
        self._attr_unique_id = f"{entry.entry_id}_gateway_address"


class SubnetMaskSensor(NetworkAddressSensor):
    """Representation of subnet mask sensor."""

    _low_key = "SUBNET_MASK_LOW_WORD"
    _high_key = "SUBNET_MASK_HIGH_WORD"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Subnet Mask"
        self._attr_unique_id = f"{entry.entry_id}_subnet_mask"


class DNSSensor1(NetworkAddressSensor):
    """Representation of primary DNS server sensor."""

    _low_key = "DNS_1_LOW_WORD"
    _high_key = "DNS_1_HIGH_WORD"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DNS Server 1"
        self._attr_unique_id = f"{entry.entry_id}_dns1"


class DNSSensor2(NetworkAddressSensor):
    """Representation of secondary DNS server sensor."""

    _low_key = "DNS_2_LOW_WORD"
    _high_key = "DNS_2_HIGH_WORD"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DNS Server 2"
        self._attr_unique_id = f"{entry.entry_id}_dns2"


class ClassicStatusSensor(MidniteSolarSensor):
    """One of the Classic's own status values that no other entity reports.

    The scale comes from the register map's formula for that register: tenths for
    the "([4nnn] /10)" rows, and the plain register for a code or a counter. (The
    nominal bank voltage 4245 is the NominalBatteryVoltageSelect now, not a sensor,
    so there is no twelve-times case left here.)
    """

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any, setting):
        """Initialize the sensor for one status register."""
        super().__init__(coordinator, entry)
        key, group, name, units, kind, diagnostic, enabled = setting
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key.lower()}"
        self._attr_entity_registry_enabled_default = enabled
        # DIAGNOSTIC for all of them: real Home Assistant REFUSES a read-only
        # sensor carrying the CONFIG category ("cannot be added as the entity
        # category is set to config" - it is reserved for entities the user can
        # act on). The first dev-HA boot dropped Battery Regulation Target
        # entirely over this (2026-09-20); the test double had no such rule.
        # The map's diagnostic flag now only annotates, it cannot demote.
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_unit_of_measurement = units
        self._attr_state_class = SensorStateClass.MEASUREMENT if units else None
        self._attr_suggested_display_precision = 1 if kind == "tenths" else 0
        self.register_address = REGISTER_MAP[key]
        self.status_group = group
        self.kind = kind

    @property
    def native_value(self) -> Optional[float]:
        """Return the value the register map's formula describes."""
        group = self.coordinator.data.get("data", {}).get(self.status_group) if self.coordinator.data else None
        if not group:
            return None
        raw = group.get(self.register_address)
        if raw is None:
            return None
        if self.kind == "tenths":
            return scaled_value(raw)
        return float(raw)


class FirmwareVersionSensor(MidniteSolarSensor):
    """The application or communications firmware version, 16385 and 16386.

    Three four-bit fields: "Major: [16385](15…12) Minor: [16385](11…8)
    Release: [16385](8..4)". See VERSION_FIELDS for the one ambiguity in how the
    map prints that.
    """

    def __init__(
        self,
        coordinator: MidniteSolarUpdateCoordinator,
        entry: Any,
        key: str,
        label: str,
        describes: str,
    ):
        """Initialize the sensor for one version register."""
        super().__init__(coordinator, entry)
        self._attr_name = label
        self._attr_unique_id = f"{entry.entry_id}_{key.lower()}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self.version_address = REGISTER_MAP[key]
        self.describes = describes

    @property
    def native_value(self) -> Optional[str]:
        """Return the version as major.minor.release."""
        raw = self._group("firmware").get(self.version_address)
        if raw is None:
            return None
        return version_from_register(raw)

    @property
    def extra_state_attributes(self) -> Optional[dict]:
        """Say which code this version belongs to."""
        return {"describes": self.describes}


class FirmwareRevisionSensor(MidniteSolarSensor):
    """The 32-bit build revision of the application or the comms stack.

    "([16388] << 16) + [16387]" - the second register of the pair is the high
    word.
    """

    def __init__(
        self,
        coordinator: MidniteSolarUpdateCoordinator,
        entry: Any,
        low_key: str,
        high_key: str,
        label: str,
    ):
        """Initialize the sensor for one revision pair."""
        super().__init__(coordinator, entry)
        self._attr_name = label
        self._attr_unique_id = f"{entry.entry_id}_{low_key.lower()}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_unit_of_measurement = None
        self.low_address = REGISTER_MAP[low_key]
        self.high_address = REGISTER_MAP[high_key]

    @property
    def native_value(self) -> Optional[int]:
        """Return the build revision as one 32-bit number."""
        group = self._group("firmware")
        low = group.get(self.low_address)
        high = group.get(self.high_address)
        if low is None or high is None:
            return None
        return combine32(low, high)
