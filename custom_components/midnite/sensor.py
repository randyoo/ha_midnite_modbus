"""Support for Midnite Solar sensor platform."""

from __future__ import annotations

import logging
import time
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
        UNIT_IDSensor(coordinator, entry),
        UNIT_SW_DATE_ROSensor(coordinator, entry),
        UNIT_SW_DATE_MONTH_DAYSensor(coordinator, entry),
        INFO_FLAGS_BITS3Sensor(coordinator, entry),
        RESERVED_4105Sensor(coordinator, entry),
        MAC_ADDRESS_PART_1Sensor(coordinator, entry),
        MAC_ADDRESS_PART_2Sensor(coordinator, entry),
        MAC_ADDRESS_PART_3Sensor(coordinator, entry),
        JrAmpHourNETSensor(coordinator, entry),
        DEVICE_ID_LSWSensor(coordinator, entry),
        DEVICE_ID_MSWSensor(coordinator, entry),
        STATUSROLLSensor(coordinator, entry),
        RESTART_TIME_MSSensor(coordinator, entry),
        DISP_AVG_VBATTSensor(coordinator, entry),
        DISP_AVG_VPVSensor(coordinator, entry),
        IBATT_DISPLAY_SSensor(coordinator, entry),
        KW_HOURSSensor(coordinator, entry),
        WATTSSensor(coordinator, entry),
        PV_INPUT_CURRENTSensor(coordinator, entry),
        VOC_LAST_MEASUREDSensor(coordinator, entry),
        HIGHEST_VINPUT_LOGSensor(coordinator, entry),
        MATCH_POINT_SHADOWSensor(coordinator, entry),
        AMP_HOURS_DAILYSensor(coordinator, entry),
        LIFETIME_KW_HOURS_1Sensor(coordinator, entry),
        LIFETIME_KW_HOURS_1_HIGHSensor(coordinator, entry),
        LIFETIME_AMP_HOURS_1Sensor(coordinator, entry),
        LIFETIME_AMP_HOURS_1_HIGHSensor(coordinator, entry),
        BATT_TEMPERATURESensor(coordinator, entry),
        FET_TEMPERATURESensor(coordinator, entry),
        PCB_TEMPERATURESensor(coordinator, entry),
        NITE_MINUTES_NO_PWRSensor(coordinator, entry),
        FLOAT_TIME_TODAY_SECSensor(coordinator, entry),
        ABSORB_TIMESensor(coordinator, entry),
        PWM_READONLYSensor(coordinator, entry),
        REASON_FOR_RESETSensor(coordinator, entry),
        EQUALIZE_TIMESensor(coordinator, entry),
        MPP_W_LASTSensor(coordinator, entry),
        NO_DOUBLE_CLICK_TIMERSensor(coordinator, entry),
        SLIDING_CURRENT_LIMITSensor(coordinator, entry),
        MIN_ABSORB_TIMESensor(coordinator, entry),
        GENERAL_PURPOSE_WORDSensor(coordinator, entry),
        EQUALIZE_RETRY_DAYSSensor(coordinator, entry),
        FORCE_FLAG_BITSSensor(coordinator, entry),
        AUX1_VOLTS_LO_RELSensor(coordinator, entry),
        AUX1_VOLTS_HI_RELSensor(coordinator, entry),
        AUX2_VOLTS_LO_RELSensor(coordinator, entry),
        AUX2_VOLTS_HI_RELSensor(coordinator, entry),
        AUX1_VOLTS_LO_PV_ABSSensor(coordinator, entry),
        AUX1_VOLTS_HI_PV_ABSSensor(coordinator, entry),
        VARIMAXSensor(coordinator, entry),
        AUX2_VOLTS_HI_PV_ABSSensor(coordinator, entry),
        ENABLE_FLAGS3Sensor(coordinator, entry),
        ARC_FAULT_SENSITIVITYSensor(coordinator, entry),
        VPV_TARGET_RDSensor(coordinator, entry),
        VPV_TARGET_WRSensor(coordinator, entry),
        SWEEP_INTERVAL_SECS_EEPROMSensor(coordinator, entry),
        MIN_SWP_VOLTAGE_EEPROMSensor(coordinator, entry),
        MAX_INPUT_CURRENT_EEPROMSensor(coordinator, entry),
        SWEEP_DEPTHSensor(coordinator, entry),
        NEGATIVE_CURRENT_ADJSensor(coordinator, entry),
        CLIPPER_CMD_VOLTSSensor(coordinator, entry),
        WIND_NUMBER_OF_POLES_EEPROMSensor(coordinator, entry),
        MPP_PERCENT_VOC_EEPROMSensor(coordinator, entry),
        WIND_TABLE_TO_USE_EEPROMSensor(coordinator, entry),
        UNIT_NAME_0Sensor(coordinator, entry),
        UNIT_NAME_1Sensor(coordinator, entry),
        UNIT_NAME_2Sensor(coordinator, entry),
        UNIT_NAME_3Sensor(coordinator, entry),
        CTI_ME0Sensor(coordinator, entry),
        CTI_ME0_HIGHSensor(coordinator, entry),
        CTI_ME1Sensor(coordinator, entry),
        CTI_ME1_HIGHSensor(coordinator, entry),
        CTI_ME2Sensor(coordinator, entry),
        REMOTE_BUTTONSSensor(coordinator, entry),
        PREVOCSensor(coordinator, entry),
        AUX2_A2D_D2ASensor(coordinator, entry),
        VOC_RDSensor(coordinator, entry),
        ABSORB_TIME_DUPLICATESensor(coordinator, entry),
        SIESTA_TIME_SECSensor(coordinator, entry),
        SIESTA_ABORT_VOC_ADJSensor(coordinator, entry),
        VBATT_REG_SET_P_TEMP_COMPSensor(coordinator, entry),
        VBATT_NOMINAL_EEPROMSensor(coordinator, entry),
        ENDING_AMPES_EEPROMSensor(coordinator, entry),
        ENDING_SOC_EEPROMSensor(coordinator, entry),
        REBUCK_VOLTS_EEPROMSensor(coordinator, entry),
        DAYS_BTW_BULK_ABS_EEPROMSensor(coordinator, entry),
        DAY_LOG_COMB_CAT_INDEXSensor(coordinator, entry),
        MIN_LOG_COMB_CAT_INDEXSensor(coordinator, entry),
        REBUCK_TIMER_SEC_EEPROMSensor(coordinator, entry),
        VOC_QUALIFY_TIMER_MS_EEPROM_LOWSensor(coordinator, entry),
        VOC_QUALIFY_TIMER_MS_EEPROMSensor(coordinator, entry),
        IPV_MINUS_RAWSensor(coordinator, entry),
        RESTART_TIME_MS2Sensor(coordinator, entry),
        IBATT_RAW_ASensor(coordinator, entry),
        OUTPUT_VBATT_RAWSensor(coordinator, entry),
        INPUT_VPV_RAWSensor(coordinator, entry),
        PK_HOLD_VPV_STAMPSensor(coordinator, entry),
        VPV_TARGET_RD_TMPSensor(coordinator, entry),
        SWP_DEEP_TIMEOUT_SECSensor(coordinator, entry),
        LOW_WATTS_EEPASensor(coordinator, entry),
        WIND_LOW_WATTS_EEPASensor(coordinator, entry),
        WIND_WINDOW_WATTS_REF_EEPASensor(coordinator, entry),
        WINDOW_WATTS_RO_DELTA_EEPASensor(coordinator, entry),
        WIND_TIMEOUT_REF_EEPASensor(coordinator, entry),
        WIND_TIMEOUT2_REF_EEPASensor(coordinator, entry),
        WIND_TIMEOUT_SECONDSSensor(coordinator, entry),
        WIND_TIMEOUT2_SECONDSSensor(coordinator, entry),
        MIN_VPV_TURN_ONSensor(coordinator, entry),
        VPV_B4_TURN_OFFSensor(coordinator, entry),
        H2O_SWEEP_AMPS_10TIME6_EEPASensor(coordinator, entry),
        ENDING_AMPS_TIMER_SECSensor(coordinator, entry),
        PK_AMPS_OVER_LIMIT_HI_EEPASensor(coordinator, entry),
        PK_AMPS_OVER_LIMIT_LO_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_V_0_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_V_1_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_V_2_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_V_3_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_V_4_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_V_5_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_V_6_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_V_7_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_I_0_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_I_1_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_I_2_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_I_3_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_I_4_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_I_5_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_I_6_EEPASensor(coordinator, entry),
        WIND_POWER_TABLE_I_7_EEPASensor(coordinator, entry),
        PK_AMPS_OVER_TRIP_EEPROMSensor(coordinator, entry),
        MNGP_REVISIONSensor(coordinator, entry),
        MNLP_REVISIONSensor(coordinator, entry),
        CLASSIC_MODBUS_ADDR_EEPROMSensor(coordinator, entry),
        BATTERY_TEMP_PASSED_EEPROMSensor(coordinator, entry),
        MODBUS_CONTROL_EEPROMSensor(coordinator, entry),
        CLASSIC_FME_PASSED_BITS_EEPROMSensor(coordinator, entry),
        WIND_SYNCH_A_EEPROMSensor(coordinator, entry),
        WIND_SYNCH_V_EEPROMSensor(coordinator, entry),
        FOLLOW_ME_PASS_REF_EEPROMSensor(coordinator, entry),
        DABT_U32_DEBUG_01Sensor(coordinator, entry),
        DABT_U32_DEBUG_02Sensor(coordinator, entry),
        DABT_U32_DEBUG_03Sensor(coordinator, entry),
        DABT_U32_DEBUG_04Sensor(coordinator, entry),
        CLEAR_LOGS_CATSensor(coordinator, entry),
        CLEAR_LOGS_COUNTER_10MSSensor(coordinator, entry),
        USER_VARIABLE_02Sensor(coordinator, entry),
        WIZBANG_RX_BUFFER_TEMP_SH1Sensor(coordinator, entry),
        WIZBANG_RX_BUFFER_TEMP_SH2Sensor(coordinator, entry),
        WIZBANG_RX_BUFFER_TEMP_SH3Sensor(coordinator, entry),
        WIZBANG_RX_BUFFER_TEMP_SH4Sensor(coordinator, entry),
        WJRB_CMD_S_EEPROMSensor(coordinator, entry),
        WJRB_RAW_CURRENTSensor(coordinator, entry),
        WJRB_NUMERATOR_SS_EEPROMSensor(coordinator, entry),
        WJRB_AMP_HOUR_POSITIVESensor(coordinator, entry),
        WJRB_AMP_HOUR_POSITIVE_HIGHSensor(coordinator, entry),
        WJRB_AMP_HOUR_NEGATIVESensor(coordinator, entry),
        WJRB_AMP_HOUR_NEGATIVE_HIGHSensor(coordinator, entry),
        WJRB_AMP_HOUR_NETSensor(coordinator, entry),
        WJRB_AMP_HOUR_NET_HIGHSensor(coordinator, entry),
        WJRB_CURRENT_32_SIGNED_EEPROMSensor(coordinator, entry),
        WJRB_RAW_CRC_AND_TEMPSensor(coordinator, entry),
        IP_ADDRESS_LSB_1Sensor(coordinator, entry),
        IP_ADDRESS_LSB_2Sensor(coordinator, entry),
        GATEWAY_ADDRESS_LSB_1Sensor(coordinator, entry),
        GATEWAY_ADDRESS_LSB_2Sensor(coordinator, entry),
        SUBNET_MASK_LSB_1Sensor(coordinator, entry),
        SUBNET_MASK_LSB_2Sensor(coordinator, entry),
        DNS_1_LSB_1Sensor(coordinator, entry),
        DNS_1_LSB_2Sensor(coordinator, entry),
        DNS_2_LSB_1Sensor(coordinator, entry),
        DNS_2_LSB_2Sensor(coordinator, entry),

        ChargeStageSensor(coordinator, entry),
        InternalStateSensor(coordinator, entry),
        DeviceTypeSensor(coordinator, entry),
        RestReasonSensor(coordinator, entry),
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

class UNIT_IDSensor(MidniteSolarSensor):
    """Representation of a hardware revision & voltage category (pcb rev, unit type) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "UNIT_ID"
        self._attr_unique_id = f"{entry.entry_id}_unit_id"
        self._attr_icon = "mdi:identifier"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["UNIT_ID"])
                if value is not None:
                    return value
                return None


class UNIT_SW_DATE_ROSensor(MidniteSolarSensor):
    """Representation of a software build date sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "UNIT_SW_DATE_RO"
        self._attr_unique_id = f"{entry.entry_id}_unit_sw_date_ro"
        self._attr_icon = "mdi:calendar"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["UNIT_SW_DATE_RO"])
                if value is not None:
                    return value
                return None


class UNIT_SW_DATE_MONTH_DAYSensor(MidniteSolarSensor):
    """Representation of a software build month/day sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "UNIT_SW_DATE_MONTH_DAY"
        self._attr_unique_id = f"{entry.entry_id}_unit_sw_date_month_day"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["UNIT_SW_DATE_MONTH_DAY"])
                if value is not None:
                    return value
                return None


class INFO_FLAGS_BITS3Sensor(MidniteSolarSensor):
    """Representation of a classic system status flags (bitfield) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "INFO_FLAGS_BITS3"
        self._attr_unique_id = f"{entry.entry_id}_info_flags_bits3"
        self._attr_icon = "mdi:flag"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["INFO_FLAGS_BITS3"])
                if value is not None:
                    return value
                return None


class RESERVED_4105Sensor(MidniteSolarSensor):
    """Representation of a unimplemented - avoid writing sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RESERVED_4105"
        self._attr_unique_id = f"{entry.entry_id}_reserved_4105"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["RESERVED_4105"])
                if value is not None:
                    return value
                return None


class MAC_ADDRESS_PART_1Sensor(MidniteSolarSensor):
    """Representation of a mac address part 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MAC_ADDRESS_PART_1"
        self._attr_unique_id = f"{entry.entry_id}_mac_address_part_1"
        self._attr_icon = "mdi:wifi"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["MAC_ADDRESS_PART_1"])
                if value is not None:
                    return value
                return None


class MAC_ADDRESS_PART_2Sensor(MidniteSolarSensor):
    """Representation of a mac address part 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MAC_ADDRESS_PART_2"
        self._attr_unique_id = f"{entry.entry_id}_mac_address_part_2"
        self._attr_icon = "mdi:wifi"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["MAC_ADDRESS_PART_2"])
                if value is not None:
                    return value
                return None


class MAC_ADDRESS_PART_3Sensor(MidniteSolarSensor):
    """Representation of a mac address part 3 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MAC_ADDRESS_PART_3"
        self._attr_unique_id = f"{entry.entry_id}_mac_address_part_3"
        self._attr_icon = "mdi:wifi"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["MAC_ADDRESS_PART_3"])
                if value is not None:
                    return value
                return None


class JrAmpHourNETSensor(MidniteSolarSensor):
    """Representation of a whizbang jr. net amp-hours sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "JrAmpHourNET"
        self._attr_unique_id = f"{entry.entry_id}_jramphournet"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            advanced_status_data = self.coordinator.data["data"].get("advanced_status")
            if advanced_status_data:
                value = advanced_status_data.get(REGISTER_MAP["JrAmpHourNET"])
                if value is not None:
                    return value / 10.0
                return None


class DEVICE_ID_LSWSensor(MidniteSolarSensor):
    """Representation of a device id (low word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DEVICE_ID_LSW"
        self._attr_unique_id = f"{entry.entry_id}_device_id_lsw"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["DEVICE_ID_LSW"])
                if value is not None:
                    return value
                return None


class DEVICE_ID_MSWSensor(MidniteSolarSensor):
    """Representation of a device id (high word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DEVICE_ID_MSW"
        self._attr_unique_id = f"{entry.entry_id}_device_id_msw"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["DEVICE_ID_MSW"])
                if value is not None:
                    return value
                return None


class STATUSROLLSensor(MidniteSolarSensor):
    """Representation of a 12-bit status value, updated once per second sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "STATUSROLL"
        self._attr_unique_id = f"{entry.entry_id}_statusroll"
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["STATUSROLL"])
                if value is not None:
                    return value
                return None


class RESTART_TIME_MSSensor(MidniteSolarSensor):
    """Representation of a time after which classic can wake up sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RESTART_TIME_MS"
        self._attr_unique_id = f"{entry.entry_id}_restart_time_ms"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "ms"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            time_settings_data = self.coordinator.data["data"].get("time_settings")
            if time_settings_data:
                value = time_settings_data.get(REGISTER_MAP["RESTART_TIME_MS"])
                if value is not None:
                    return value
                return None


class DISP_AVG_VBATTSensor(MidniteSolarSensor):
    """Representation of a average battery voltage (1 s) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DISP_AVG_VBATT"
        self._attr_unique_id = f"{entry.entry_id}_disp_avg_vbatt"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

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


class DISP_AVG_VPVSensor(MidniteSolarSensor):
    """Representation of a average pv input voltage (1 s) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DISP_AVG_VPV"
        self._attr_unique_id = f"{entry.entry_id}_disp_avg_vpv"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:solar-power"

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


class IBATT_DISPLAY_SSensor(MidniteSolarSensor):
    """Representation of a average battery current (1 s) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "IBATT_DISPLAY_S"
        self._attr_unique_id = f"{entry.entry_id}_ibatt_display_s"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["IBATT_DISPLAY_S"])
                if value is not None:
                    return value / 10.0
                return None


class KW_HOURSSensor(MidniteSolarSensor):
    """Representation of a energy to the battery (reset daily) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "KW_HOURS"
        self._attr_unique_id = f"{entry.entry_id}_kw_hours"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_suggested_display_precision = 2
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["KW_HOURS"])
                if value is not None:
                    return value / 100.0
                return None


class WATTSSensor(MidniteSolarSensor):
    """Representation of a average power to the battery sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WATTS"
        self._attr_unique_id = f"{entry.entry_id}_watts"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WATTS"])
                if value is not None:
                    return value
                return None


class PV_INPUT_CURRENTSensor(MidniteSolarSensor):
    """Representation of a average pv input current (1 s) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PV_INPUT_CURRENT"
        self._attr_unique_id = f"{entry.entry_id}_pv_input_current"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:solar-power"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["PV_INPUT_CURRENT"])
                if value is not None:
                    return value / 10.0
                return None


class VOC_LAST_MEASUREDSensor(MidniteSolarSensor):
    """Representation of a last measured open-circuit voltage at pv input sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VOC_LAST_MEASURED"
        self._attr_unique_id = f"{entry.entry_id}_voc_last_measured"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-triangle"

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


class HIGHEST_VINPUT_LOGSensor(MidniteSolarSensor):
    """Representation of a highest input voltage seen (eeprom) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "HIGHEST_VINPUT_LOG"
        self._attr_unique_id = f"{entry.entry_id}_highest_vinput_log"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            advanced_status_data = self.coordinator.data["data"].get("advanced_status")
            if advanced_status_data:
                value = advanced_status_data.get(REGISTER_MAP["HIGHEST_VINPUT_LOG"])
                if value is not None:
                    return value / 10.0
                return None


class MATCH_POINT_SHADOWSensor(MidniteSolarSensor):
    """Representation of a current wind power curve step (1-16) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MATCH_POINT_SHADOW"
        self._attr_unique_id = f"{entry.entry_id}_match_point_shadow"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            advanced_status_data = self.coordinator.data["data"].get("advanced_status")
            if advanced_status_data:
                value = advanced_status_data.get(REGISTER_MAP["MATCH_POINT_SHADOW"])
                if value is not None:
                    return value
                return None


class AMP_HOURS_DAILYSensor(MidniteSolarSensor):
    """Representation of a daily amp-hours reset at 23:59 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "AMP_HOURS_DAILY"
        self._attr_unique_id = f"{entry.entry_id}_amp_hours_daily"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = "Ah"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            energy_data = self.coordinator.data["data"].get("energy")
            if energy_data:
                value = energy_data.get(REGISTER_MAP["AMP_HOURS_DAILY"])
                if value is not None:
                    return value
                return None


class LIFETIME_KW_HOURS_1Sensor(MidniteSolarSensor):
    """Representation of a lifetime energy generation (low word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "LIFETIME_KW_HOURS_1"
        self._attr_unique_id = f"{entry.entry_id}_lifetime_kw_hours_1"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_suggested_display_precision = 2
        self._attr_icon = "mdi:history"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            energy_data = self.coordinator.data["data"].get("energy")
            if energy_data:
                value = energy_data.get(REGISTER_MAP["LIFETIME_KW_HOURS_1"])
                if value is not None:
                    return value / 100.0
                return None


class LIFETIME_KW_HOURS_1_HIGHSensor(MidniteSolarSensor):
    """Representation of a lifetime energy generation (high word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "LIFETIME_KW_HOURS_1_HIGH"
        self._attr_unique_id = f"{entry.entry_id}_lifetime_kw_hours_1_high"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_suggested_display_precision = 2
        self._attr_icon = "mdi:history"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            energy_data = self.coordinator.data["data"].get("energy")
            if energy_data:
                value = energy_data.get(REGISTER_MAP["LIFETIME_KW_HOURS_1_HIGH"])
                if value is not None:
                    return value / 100.0
                return None


class LIFETIME_AMP_HOURS_1Sensor(MidniteSolarSensor):
    """Representation of a lifetime amp-hour generation (low word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "LIFETIME_AMP_HOURS_1"
        self._attr_unique_id = f"{entry.entry_id}_lifetime_amp_hours_1"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = "Ah"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:history"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            energy_data = self.coordinator.data["data"].get("energy")
            if energy_data:
                value = energy_data.get(REGISTER_MAP["LIFETIME_AMP_HOURS_1"])
                if value is not None:
                    return value
                return None


class LIFETIME_AMP_HOURS_1_HIGHSensor(MidniteSolarSensor):
    """Representation of a lifetime amp-hour generation (high word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "LIFETIME_AMP_HOURS_1_HIGH"
        self._attr_unique_id = f"{entry.entry_id}_lifetime_amp_hours_1_high"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            energy_data = self.coordinator.data["data"].get("energy")
            if energy_data:
                value = energy_data.get(REGISTER_MAP["LIFETIME_AMP_HOURS_1_HIGH"])
                if value is not None:
                    return value / 10.0
                return None


class BATT_TEMPERATURESensor(MidniteSolarSensor):
    """Representation of a battery temperature sensor sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "BATT_TEMPERATURE"
        self._attr_unique_id = f"{entry.entry_id}_batt_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            temperatures_data = self.coordinator.data["data"].get("temperatures")
            if temperatures_data:
                value = temperatures_data.get(REGISTER_MAP["BATT_TEMPERATURE"])
                if value is not None:
                    return value / 10.0
                return None


class FET_TEMPERATURESensor(MidniteSolarSensor):
    """Representation of a power fet temperature sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "FET_TEMPERATURE"
        self._attr_unique_id = f"{entry.entry_id}_fet_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-high"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            temperatures_data = self.coordinator.data["data"].get("temperatures")
            if temperatures_data:
                value = temperatures_data.get(REGISTER_MAP["FET_TEMPERATURE"])
                if value is not None:
                    return value / 10.0
                return None


class PCB_TEMPERATURESensor(MidniteSolarSensor):
    """Representation of a classic top pcb temperature sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PCB_TEMPERATURE"
        self._attr_unique_id = f"{entry.entry_id}_pcb_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            temperatures_data = self.coordinator.data["data"].get("temperatures")
            if temperatures_data:
                value = temperatures_data.get(REGISTER_MAP["PCB_TEMPERATURE"])
                if value is not None:
                    return value / 10.0
                return None


class NITE_MINUTES_NO_PWRSensor(MidniteSolarSensor):
    """Representation of a counts up when no power, resets on power sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "NITE_MINUTES_NO_PWR"
        self._attr_unique_id = f"{entry.entry_id}_nite_minutes_no_pwr"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["NITE_MINUTES_NO_PWR"])
                if value is not None:
                    return value
                return None


class FLOAT_TIME_TODAY_SECSensor(MidniteSolarSensor):
    """Representation of a seconds spent in float today (reset at 23:59) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "FLOAT_TIME_TODAY_SEC"
        self._attr_unique_id = f"{entry.entry_id}_float_time_today_sec"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            time_settings_data = self.coordinator.data["data"].get("time_settings")
            if time_settings_data:
                value = time_settings_data.get(REGISTER_MAP["FLOAT_TIME_TODAY_SEC"])
                if value is not None:
                    return value
                return None


class ABSORB_TIMESensor(MidniteSolarSensor):
    """Representation of a absorb time counter, resets when reaching 0 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "ABSORB_TIME"
        self._attr_unique_id = f"{entry.entry_id}_absorb_time"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:clock-start"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            time_settings_data = self.coordinator.data["data"].get("time_settings")
            if time_settings_data:
                value = time_settings_data.get(REGISTER_MAP["ABSORB_TIME"])
                if value is not None:
                    return value
                return None


class PWM_READONLYSensor(MidniteSolarSensor):
    """Representation of a duty cycle command of pwm (not percent) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PWM_READONLY"
        self._attr_unique_id = f"{entry.entry_id}_pwm_readonly"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["PWM_READONLY"])
                if value is not None:
                    return value
                return None


class REASON_FOR_RESETSensor(MidniteSolarSensor):
    """Representation of a reason classic reset sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "REASON_FOR_RESET"
        self._attr_unique_id = f"{entry.entry_id}_reason_for_reset"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:alert-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["REASON_FOR_RESET"])
                if value is not None:
                    return value
                return None


class EQUALIZE_TIMESensor(MidniteSolarSensor):
    """Representation of a battery stage equalize counter (down) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQUALIZE_TIME"
        self._attr_unique_id = f"{entry.entry_id}_equalize_time"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:progress-wrench"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            time_settings_data = self.coordinator.data["data"].get("time_settings")
            if time_settings_data:
                value = time_settings_data.get(REGISTER_MAP["EQUALIZE_TIME"])
                if value is not None:
                    return value
                return None


class MPP_W_LASTSensor(MidniteSolarSensor):
    """Representation of a internal watts reference (~10% of last mpp) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MPP_W_LAST"
        self._attr_unique_id = f"{entry.entry_id}_mpp_w_last"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:lightning-bolt-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MPP_W_LAST"])
                if value is not None:
                    return value
                return None


class NO_DOUBLE_CLICK_TIMERSensor(MidniteSolarSensor):
    """Representation of a internal forced time between manual sweeps sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "NO_DOUBLE_CLICK_TIMER"
        self._attr_unique_id = f"{entry.entry_id}_no_double_click_timer"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["NO_DOUBLE_CLICK_TIMER"])
                if value is not None:
                    return value
                return None


class SLIDING_CURRENT_LIMITSensor(MidniteSolarSensor):
    """Representation of a sliding current limit (varies with v/temp) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "SLIDING_CURRENT_LIMIT"
        self._attr_unique_id = f"{entry.entry_id}_sliding_current_limit"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["SLIDING_CURRENT_LIMIT"])
                if value is not None:
                    return value / 10.0
                return None


class MIN_ABSORB_TIMESensor(MidniteSolarSensor):
    """Representation of a minimum absorb time (usually unused) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MIN_ABSORB_TIME"
        self._attr_unique_id = f"{entry.entry_id}_min_absorb_time"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MIN_ABSORB_TIME"])
                if value is not None:
                    return value
                return None


class GENERAL_PURPOSE_WORDSensor(MidniteSolarSensor):
    """Representation of a stored & retrieved with other eeprom (was battery type) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "GENERAL_PURPOSE_WORD"
        self._attr_unique_id = f"{entry.entry_id}_general_purpose_word"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["GENERAL_PURPOSE_WORD"])
                if value is not None:
                    return value
                return None


class EQUALIZE_RETRY_DAYSSensor(MidniteSolarSensor):
    """Representation of a auto eq retry days until giving up sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQUALIZE_RETRY_DAYS"
        self._attr_unique_id = f"{entry.entry_id}_equalize_retry_days"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["EQUALIZE_RETRY_DAYS"])
                if value is not None:
                    return value
                return None


class FORCE_FLAG_BITSSensor(MidniteSolarSensor):
    """Representation of a write-only flags that trigger special actions sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "FORCE_FLAG_BITS"
        self._attr_unique_id = f"{entry.entry_id}_force_flag_bits"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:flag"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["FORCE_FLAG_BITS"])
                if value is not None:
                    return value
                return None


class AUX1_VOLTS_LO_RELSensor(MidniteSolarSensor):
    """Representation of a aux 1 waste-not relative lower voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX1_VOLTS_LO_REL"
        self._attr_unique_id = f"{entry.entry_id}_aux1_volts_lo_rel"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["AUX1_VOLTS_LO_REL"])
                if value is not None:
                    return value / 10.0
                return None


class AUX1_VOLTS_HI_RELSensor(MidniteSolarSensor):
    """Representation of a aux 1 waste-not relative upper voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX1_VOLTS_HI_REL"
        self._attr_unique_id = f"{entry.entry_id}_aux1_volts_hi_rel"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["AUX1_VOLTS_HI_REL"])
                if value is not None:
                    return value / 10.0
                return None


class AUX2_VOLTS_LO_RELSensor(MidniteSolarSensor):
    """Representation of a aux 2 waste-not relative lower voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX2_VOLTS_LO_REL"
        self._attr_unique_id = f"{entry.entry_id}_aux2_volts_lo_rel"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["AUX2_VOLTS_LO_REL"])
                if value is not None:
                    return value / 10.0
                return None


class AUX2_VOLTS_HI_RELSensor(MidniteSolarSensor):
    """Representation of a aux 2 waste-not relative upper voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX2_VOLTS_HI_REL"
        self._attr_unique_id = f"{entry.entry_id}_aux2_volts_hi_rel"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["AUX2_VOLTS_HI_REL"])
                if value is not None:
                    return value / 10.0
                return None


class AUX1_VOLTS_LO_PV_ABSSensor(MidniteSolarSensor):
    """Representation of a aux 1 lower pv absolute threshold voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX1_VOLTS_LO_PV_ABS"
        self._attr_unique_id = f"{entry.entry_id}_aux1_volts_lo_pv_abs"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["AUX1_VOLTS_LO_PV_ABS"])
                if value is not None:
                    return value / 10.0
                return None


class AUX1_VOLTS_HI_PV_ABSSensor(MidniteSolarSensor):
    """Representation of a aux 1 higher pv absolute threshold voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX1_VOLTS_HI_PV_ABS"
        self._attr_unique_id = f"{entry.entry_id}_aux1_volts_hi_pv_abs"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            aux_control_data = self.coordinator.data["data"].get("aux_control")
            if aux_control_data:
                value = aux_control_data.get(REGISTER_MAP["AUX1_VOLTS_HI_PV_ABS"])
                if value is not None:
                    return value / 10.0
                return None


class VARIMAXSensor(MidniteSolarSensor):
    """Representation of a variable maximum current & voltage differential sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VARIMAX"
        self._attr_unique_id = f"{entry.entry_id}_varimax"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:arrow-expand-vertical"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            advanced_config_data = self.coordinator.data["data"].get("advanced_config")
            if advanced_config_data:
                value = advanced_config_data.get(REGISTER_MAP["VARIMAX"])
                if value is not None:
                    return value / 10.0
                return None


class AUX2_VOLTS_HI_PV_ABSSensor(MidniteSolarSensor):
    """Representation of a aux 2 higher pv absolute threshold voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX2_VOLTS_HI_PV_ABS"
        self._attr_unique_id = f"{entry.entry_id}_aux2_volts_hi_pv_abs"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            aux_control_data = self.coordinator.data["data"].get("aux_control")
            if aux_control_data:
                value = aux_control_data.get(REGISTER_MAP["AUX2_VOLTS_HI_PV_ABS"])
                if value is not None:
                    return value / 10.0
                return None


class ENABLE_FLAGS3Sensor(MidniteSolarSensor):
    """Representation of a enable forwarding of modbus traffic (follow-me) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "ENABLE_FLAGS3"
        self._attr_unique_id = f"{entry.entry_id}_enable_flags3"
        self._attr_icon = "mdi:check-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            advanced_config_data = self.coordinator.data["data"].get("advanced_config")
            if advanced_config_data:
                value = advanced_config_data.get(REGISTER_MAP["ENABLE_FLAGS3"])
                if value is not None:
                    return value
                return None


class ARC_FAULT_SENSITIVITYSensor(MidniteSolarSensor):
    """Representation of a arc fault protection sensitivity sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "ARC_FAULT_SENSITIVITY"
        self._attr_unique_id = f"{entry.entry_id}_arc_fault_sensitivity"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["ARC_FAULT_SENSITIVITY"])
                if value is not None:
                    return value
                return None


class VPV_TARGET_RDSensor(MidniteSolarSensor):
    """Representation of a pv input target (usually vmpp) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VPV_TARGET_RD"
        self._attr_unique_id = f"{entry.entry_id}_vpv_target_rd"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["VPV_TARGET_RD"])
                if value is not None:
                    return value / 10.0
                return None


class VPV_TARGET_WRSensor(MidniteSolarSensor):
    """Representation of a writeable pv target command sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VPV_TARGET_WR"
        self._attr_unique_id = f"{entry.entry_id}_vpv_target_wr"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["VPV_TARGET_WR"])
                if value is not None:
                    return value / 10.0
                return None


class SWEEP_INTERVAL_SECS_EEPROMSensor(MidniteSolarSensor):
    """Representation of a legacy p&o sweep interval (seconds) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "SWEEP_INTERVAL_SECS_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_sweep_interval_secs_eeprom"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["SWEEP_INTERVAL_SECS_EEPROM"])
                if value is not None:
                    return value
                return None


class MIN_SWP_VOLTAGE_EEPROMSensor(MidniteSolarSensor):
    """Representation of a minimum input voltage for hydro mppt mode sweep sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MIN_SWP_VOLTAGE_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_min_swp_voltage_eeprom"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MIN_SWP_VOLTAGE_EEPROM"])
                if value is not None:
                    return value / 10.0
                return None


class MAX_INPUT_CURRENT_EEPROMSensor(MidniteSolarSensor):
    """Representation of a maximum input current limit (default 99 a) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MAX_INPUT_CURRENT_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_max_input_current_eeprom"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MAX_INPUT_CURRENT_EEPROM"])
                if value is not None:
                    return value / 10.0
                return None


class SWEEP_DEPTHSensor(MidniteSolarSensor):
    """Representation of a legacy/hydro mode sweep depth as % of current mpp sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "SWEEP_DEPTH"
        self._attr_unique_id = f"{entry.entry_id}_sweep_depth"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["SWEEP_DEPTH"])
                if value is not None:
                    return value
                return None


class NEGATIVE_CURRENT_ADJSensor(MidniteSolarSensor):
    """Representation of a factory calibration - do not change sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "NEGATIVE_CURRENT_ADJ"
        self._attr_unique_id = f"{entry.entry_id}_negative_current_adj"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["NEGATIVE_CURRENT_ADJ"])
                if value is not None:
                    return value / 10.0
                return None


class CLIPPER_CMD_VOLTSSensor(MidniteSolarSensor):
    """Representation of a aux clipper reference varies with stage and headroom sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "CLIPPER_CMD_VOLTS"
        self._attr_unique_id = f"{entry.entry_id}_clipper_cmd_volts"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["CLIPPER_CMD_VOLTS"])
                if value is not None:
                    return value / 10.0
                return None


class WIND_NUMBER_OF_POLES_EEPROMSensor(MidniteSolarSensor):
    """Representation of a number of turbine alternator poles (unused) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_NUMBER_OF_POLES_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_wind_number_of_poles_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_NUMBER_OF_POLES_EEPROM"])
                if value is not None:
                    return value
                return None


class MPP_PERCENT_VOC_EEPROMSensor(MidniteSolarSensor):
    """Representation of a % of voc for u-set mode sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MPP_PERCENT_VOC_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_mpp_percent_voc_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MPP_PERCENT_VOC_EEPROM"])
                if value is not None:
                    return value
                return None


class WIND_TABLE_TO_USE_EEPROMSensor(MidniteSolarSensor):
    """Representation of a future power curve select sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_TABLE_TO_USE_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_wind_table_to_use_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_TABLE_TO_USE_EEPROM"])
                if value is not None:
                    return value
                return None


class UNIT_NAME_0Sensor(MidniteSolarSensor):
    """Representation of a 8-char ascii unit name - part 0 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "UNIT_NAME_0"
        self._attr_unique_id = f"{entry.entry_id}_unit_name_0"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["UNIT_NAME_0"])
                if value is not None:
                    return value
                return None


class UNIT_NAME_1Sensor(MidniteSolarSensor):
    """Representation of a 8-char ascii unit name - part 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "UNIT_NAME_1"
        self._attr_unique_id = f"{entry.entry_id}_unit_name_1"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["UNIT_NAME_1"])
                if value is not None:
                    return value
                return None


class UNIT_NAME_2Sensor(MidniteSolarSensor):
    """Representation of a 8-char ascii unit name - part 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "UNIT_NAME_2"
        self._attr_unique_id = f"{entry.entry_id}_unit_name_2"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["UNIT_NAME_2"])
                if value is not None:
                    return value
                return None


class UNIT_NAME_3Sensor(MidniteSolarSensor):
    """Representation of a 8-char ascii unit name - part 3 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "UNIT_NAME_3"
        self._attr_unique_id = f"{entry.entry_id}_unit_name_3"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["UNIT_NAME_3"])
                if value is not None:
                    return value
                return None


class CTI_ME0Sensor(MidniteSolarSensor):
    """Representation of a consolidated time register 0 (seconds since epoch) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "CTI_ME0"
        self._attr_unique_id = f"{entry.entry_id}_cti_me0"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["CTI_ME0"])
                if value is not None:
                    return value
                return None


class CTI_ME0_HIGHSensor(MidniteSolarSensor):
    """Representation of a consolidated time register 0 (high word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "CTI_ME0_HIGH"
        self._attr_unique_id = f"{entry.entry_id}_cti_me0_high"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["CTI_ME0_HIGH"])
                if value is not None:
                    return value
                return None


class CTI_ME1Sensor(MidniteSolarSensor):
    """Representation of a consolidated time register 1 (minutes) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "CTI_ME1"
        self._attr_unique_id = f"{entry.entry_id}_cti_me1"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["CTI_ME1"])
                if value is not None:
                    return value
                return None


class CTI_ME1_HIGHSensor(MidniteSolarSensor):
    """Representation of a consolidated time register 1 (high word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "CTI_ME1_HIGH"
        self._attr_unique_id = f"{entry.entry_id}_cti_me1_high"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["CTI_ME1_HIGH"])
                if value is not None:
                    return value
                return None


class CTI_ME2Sensor(MidniteSolarSensor):
    """Representation of a consolidated time register 2 (epoch days) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "CTI_ME2"
        self._attr_unique_id = f"{entry.entry_id}_cti_me2"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["CTI_ME2"])
                if value is not None:
                    return value
                return None


class REMOTE_BUTTONSSensor(MidniteSolarSensor):
    """Representation of a mngp buttons pressed sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "REMOTE_BUTTONS"
        self._attr_unique_id = f"{entry.entry_id}_remote_buttons"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["REMOTE_BUTTONS"])
                if value is not None:
                    return value
                return None


class PREVOCSensor(MidniteSolarSensor):
    """Representation of a voc before relay sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PREVOC"
        self._attr_unique_id = f"{entry.entry_id}_prevoc"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["PREVOC"])
                if value is not None:
                    return value
                return None


class AUX2_A2D_D2ASensor(MidniteSolarSensor):
    """Representation of a aux 2 a/d and d/a value sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX2_A2D_D2A"
        self._attr_unique_id = f"{entry.entry_id}_aux2_a2d_d2a"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            aux_control_data = self.coordinator.data["data"].get("aux_control")
            if aux_control_data:
                value = aux_control_data.get(REGISTER_MAP["AUX2_A2D_D2A"])
                if value is not None:
                    return value
                return None


class VOC_RDSensor(MidniteSolarSensor):
    """Representation of a last voc reading sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VOC_RD"
        self._attr_unique_id = f"{entry.entry_id}_voc_rd"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["VOC_RD"])
                if value is not None:
                    return value
                return None


class ABSORB_TIME_DUPLICATESensor(MidniteSolarSensor):
    """Representation of a duplicate absorb time counter sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "ABSORB_TIME_DUPLICATE"
        self._attr_unique_id = f"{entry.entry_id}_absorb_time_duplicate"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["ABSORB_TIME_DUPLICATE"])
                if value is not None:
                    return value
                return None


class SIESTA_TIME_SECSensor(MidniteSolarSensor):
    """Representation of a sleep timer (max 5 min) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "SIESTA_TIME_SEC"
        self._attr_unique_id = f"{entry.entry_id}_siesta_time_sec"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["SIESTA_TIME_SEC"])
                if value is not None:
                    return value
                return None


class SIESTA_ABORT_VOC_ADJSensor(MidniteSolarSensor):
    """Representation of a voc difference to abort siesta sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "SIESTA_ABORT_VOC_ADJ"
        self._attr_unique_id = f"{entry.entry_id}_siesta_abort_voc_adj"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["SIESTA_ABORT_VOC_ADJ"])
                if value is not None:
                    return value
                return None


class VBATT_REG_SET_P_TEMP_COMPSensor(MidniteSolarSensor):
    """Representation of a battery regulation target voltage, temp-compensated sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VBATT_REG_SET_P_TEMP_COMP"
        self._attr_unique_id = f"{entry.entry_id}_vbatt_reg_set_p_temp_comp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["VBATT_REG_SET_P_TEMP_COMP"])
                if value is not None:
                    return value / 10.0
                return None


class VBATT_NOMINAL_EEPROMSensor(MidniteSolarSensor):
    """Representation of a nominal battery bank voltage (12 v, 24 v, etc.) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VBATT_NOMINAL_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_vbatt_nominal_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["VBATT_NOMINAL_EEPROM"])
                if value is not None:
                    return value
                return None


class ENDING_AMPES_EEPROMSensor(MidniteSolarSensor):
    """Representation of a end of absorb amps threshold (float if reached) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "ENDING_AMPES_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_ending_ampes_eeprom"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["ENDING_AMPES_EEPROM"])
                if value is not None:
                    return value / 10.0
                return None


class ENDING_SOC_EEPROMSensor(MidniteSolarSensor):
    """Representation of a soc to end absorb (future soc use) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "ENDING_SOC_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_ending_soc_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["ENDING_SOC_EEPROM"])
                if value is not None:
                    return value
                return None


class REBUCK_VOLTS_EEPROMSensor(MidniteSolarSensor):
    """Representation of a re-bulk if battery drops below this for > 90 s sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "REBUCK_VOLTS_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_rebuck_volts_eeprom"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["REBUCK_VOLTS_EEPROM"])
                if value is not None:
                    return value / 10.0
                return None


class DAYS_BTW_BULK_ABS_EEPROMSensor(MidniteSolarSensor):
    """Representation of a days between bulk/absorb cycles sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DAYS_BTW_BULK_ABS_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_days_btw_bulk_abs_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DAYS_BTW_BULK_ABS_EEPROM"])
                if value is not None:
                    return value
                return None


class DAY_LOG_COMB_CAT_INDEXSensor(MidniteSolarSensor):
    """Representation of a daily logs combined category / day index sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DAY_LOG_COMB_CAT_INDEX"
        self._attr_unique_id = f"{entry.entry_id}_day_log_comb_cat_index"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DAY_LOG_COMB_CAT_INDEX"])
                if value is not None:
                    return value
                return None


class MIN_LOG_COMB_CAT_INDEXSensor(MidniteSolarSensor):
    """Representation of a minute logs combined category / sample offset sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MIN_LOG_COMB_CAT_INDEX"
        self._attr_unique_id = f"{entry.entry_id}_min_log_comb_cat_index"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MIN_LOG_COMB_CAT_INDEX"])
                if value is not None:
                    return value
                return None


class REBUCK_TIMER_SEC_EEPROMSensor(MidniteSolarSensor):
    """Representation of a re-bulk interval timer seconds sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "REBUCK_TIMER_SEC_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_rebuck_timer_sec_eeprom"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["REBUCK_TIMER_SEC_EEPROM"])
                if value is not None:
                    return value
                return None


class VOC_QUALIFY_TIMER_MS_EEPROM_LOWSensor(MidniteSolarSensor):
    """Representation of a qualifying time till turn-on (low word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VOC_QUALIFY_TIMER_MS_EEPROM_LOW"
        self._attr_unique_id = f"{entry.entry_id}_voc_qualify_timer_ms_eeprom_low"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["VOC_QUALIFY_TIMER_MS_EEPROM_LOW"])
                if value is not None:
                    return value
                return None


class VOC_QUALIFY_TIMER_MS_EEPROMSensor(MidniteSolarSensor):
    """Representation of a qualifying time till turn-on (ms) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VOC_QUALIFY_TIMER_MS_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_voc_qualify_timer_ms_eeprom"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["VOC_QUALIFY_TIMER_MS_EEPROM"])
                if value is not None:
                    return value
                return None


class IPV_MINUS_RAWSensor(MidniteSolarSensor):
    """Representation of a raw pv negative current from adc sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "IPV_MINUS_RAW"
        self._attr_unique_id = f"{entry.entry_id}_ipv_minus_raw"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["IPV_MINUS_RAW"])
                if value is not None:
                    return value
                return None


class RESTART_TIME_MS2Sensor(MidniteSolarSensor):
    """Representation of a countdown time to wake up (<= 500 ms) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RESTART_TIME_MS2"
        self._attr_unique_id = f"{entry.entry_id}_restart_time_ms2"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["RESTART_TIME_MS2"])
                if value is not None:
                    return value
                return None


class IBATT_RAW_ASensor(MidniteSolarSensor):
    """Representation of a battery current, unfiltered sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "IBATT_RAW_A"
        self._attr_unique_id = f"{entry.entry_id}_ibatt_raw_a"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["IBATT_RAW_A"])
                if value is not None:
                    return value / 10.0
                return None


class OUTPUT_VBATT_RAWSensor(MidniteSolarSensor):
    """Representation of a battery voltage, unfiltered sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "OUTPUT_VBATT_RAW"
        self._attr_unique_id = f"{entry.entry_id}_output_vbatt_raw"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["OUTPUT_VBATT_RAW"])
                if value is not None:
                    return value / 10.0
                return None


class INPUT_VPV_RAWSensor(MidniteSolarSensor):
    """Representation of a pv voltage, unfiltered sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "INPUT_VPV_RAW"
        self._attr_unique_id = f"{entry.entry_id}_input_vpv_raw"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["INPUT_VPV_RAW"])
                if value is not None:
                    return value / 10.0
                return None


class PK_HOLD_VPV_STAMPSensor(MidniteSolarSensor):
    """Representation of a solar mppt internal variable sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PK_HOLD_VPV_STAMP"
        self._attr_unique_id = f"{entry.entry_id}_pk_hold_vpv_stamp"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["PK_HOLD_VPV_STAMP"])
                if value is not None:
                    return value / 10.0
                return None


class VPV_TARGET_RD_TMPSensor(MidniteSolarSensor):
    """Representation of a temporary pv target voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VPV_TARGET_RD_TMP"
        self._attr_unique_id = f"{entry.entry_id}_vpv_target_rd_tmp"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["VPV_TARGET_RD_TMP"])
                if value is not None:
                    return value / 10.0
                return None


class SWP_DEEP_TIMEOUT_SECSensor(MidniteSolarSensor):
    """Representation of a solar mppt internal variable sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "SWP_DEEP_TIMEOUT_SEC"
        self._attr_unique_id = f"{entry.entry_id}_swp_deep_timeout_sec"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["SWP_DEEP_TIMEOUT_SEC"])
                if value is not None:
                    return value
                return None


class LOW_WATTS_EEPASensor(MidniteSolarSensor):
    """Representation of a classic rests when watts < this for > 90 s (non-wind) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "LOW_WATTS_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_low_watts_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["LOW_WATTS_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_LOW_WATTS_EEPASensor(MidniteSolarSensor):
    """Representation of a wind low watts threshold (default 50 w) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_LOW_WATTS_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_low_watts_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_LOW_WATTS_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_WINDOW_WATTS_REF_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power window reference to keep running sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_WINDOW_WATTS_REF_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_window_watts_ref_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_WINDOW_WATTS_REF_EEPA"])
                if value is not None:
                    return value
                return None


class WINDOW_WATTS_RO_DELTA_EEPASensor(MidniteSolarSensor):
    """Representation of a delta watts below windlowwatts for power wiggling sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WINDOW_WATTS_RO_DELTA_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_window_watts_ro_delta_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WINDOW_WATTS_RO_DELTA_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_TIMEOUT_REF_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power low timeout to go resting (default 90 s) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_TIMEOUT_REF_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_timeout_ref_eepa"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_TIMEOUT_REF_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_TIMEOUT2_REF_EEPASensor(MidniteSolarSensor):
    """Representation of a half-hour wind timeout reference (default 1800 s) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_TIMEOUT2_REF_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_timeout2_ref_eepa"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_TIMEOUT2_REF_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_TIMEOUT_SECONDSSensor(MidniteSolarSensor):
    """Representation of a wind timeout counter - > wind_timeout_ref -> rest sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_TIMEOUT_SECONDS"
        self._attr_unique_id = f"{entry.entry_id}_wind_timeout_seconds"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_TIMEOUT_SECONDS"])
                if value is not None:
                    return value
                return None


class WIND_TIMEOUT2_SECONDSSensor(MidniteSolarSensor):
    """Representation of a wind timeout counter 2 - > wind_timeout2_ref -> rest sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_TIMEOUT2_SECONDS"
        self._attr_unique_id = f"{entry.entry_id}_wind_timeout2_seconds"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_TIMEOUT2_SECONDS"])
                if value is not None:
                    return value
                return None


class MIN_VPV_TURN_ONSensor(MidniteSolarSensor):
    """Representation of a minimum input voltage to exit resting sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MIN_VPV_TURN_ON"
        self._attr_unique_id = f"{entry.entry_id}_min_vpv_turn_on"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MIN_VPV_TURN_ON"])
                if value is not None:
                    return value
                return None


class VPV_B4_TURN_OFFSensor(MidniteSolarSensor):
    """Representation of a internal reference of vpv when going to resting sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VPV_B4_TURN_OFF"
        self._attr_unique_id = f"{entry.entry_id}_vpv_b4_turn_off"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["VPV_B4_TURN_OFF"])
                if value is not None:
                    return value
                return None


class H2O_SWEEP_AMPS_10TIME6_EEPASensor(MidniteSolarSensor):
    """Representation of a hydro sweep speed reference sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "H2O_SWEEP_AMPS_10TIME6_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_h2o_sweep_amps_10time6_eepa"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["H2O_SWEEP_AMPS_10TIME6_EEPA"])
                if value is not None:
                    return value / 10.0
                return None


class ENDING_AMPS_TIMER_SECSensor(MidniteSolarSensor):
    """Representation of a timer for ending amps (60 s reference) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "ENDING_AMPS_TIMER_SEC"
        self._attr_unique_id = f"{entry.entry_id}_ending_amps_timer_sec"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["ENDING_AMPS_TIMER_SEC"])
                if value is not None:
                    return value / 10.0
                return None


class PK_AMPS_OVER_LIMIT_HI_EEPASensor(MidniteSolarSensor):
    """Representation of a factory calibration - leave as is sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PK_AMPS_OVER_LIMIT_HI_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_pk_amps_over_limit_hi_eepa"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["PK_AMPS_OVER_LIMIT_HI_EEPA"])
                if value is not None:
                    return value / 10.0
                return None


class PK_AMPS_OVER_LIMIT_LO_EEPASensor(MidniteSolarSensor):
    """Representation of a factory calibration - leave as is sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PK_AMPS_OVER_LIMIT_LO_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_pk_amps_over_limit_lo_eepa"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["PK_AMPS_OVER_LIMIT_LO_EEPA"])
                if value is not None:
                    return value / 10.0
                return None


class WIND_POWER_TABLE_V_0_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve step 0 (v cut-in) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_V_0_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_v_0_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_V_0_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_V_1_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve step 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_V_1_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_v_1_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_V_1_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_V_2_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve step 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_V_2_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_v_2_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_V_2_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_V_3_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve step 3 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_V_3_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_v_3_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_V_3_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_V_4_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve step 4 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_V_4_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_v_4_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_V_4_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_V_5_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve step 5 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_V_5_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_v_5_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_V_5_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_V_6_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve step 6 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_V_6_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_v_6_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_V_6_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_V_7_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve step 7 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_V_7_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_v_7_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_V_7_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_I_0_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve current step 0 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_I_0_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_i_0_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_I_0_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_I_1_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve current step 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_I_1_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_i_1_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_I_1_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_I_2_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve current step 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_I_2_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_i_2_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_I_2_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_I_3_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve current step 3 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_I_3_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_i_3_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_I_3_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_I_4_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve current step 4 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_I_4_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_i_4_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_I_4_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_I_5_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve current step 5 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_I_5_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_i_5_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_I_5_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_I_6_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve current step 6 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_I_6_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_i_6_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_I_6_EEPA"])
                if value is not None:
                    return value
                return None


class WIND_POWER_TABLE_I_7_EEPASensor(MidniteSolarSensor):
    """Representation of a wind power curve current step 7 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_POWER_TABLE_I_7_EEPA"
        self._attr_unique_id = f"{entry.entry_id}_wind_power_table_i_7_eepa"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_POWER_TABLE_I_7_EEPA"])
                if value is not None:
                    return value
                return None


class PK_AMPS_OVER_TRIP_EEPROMSensor(MidniteSolarSensor):
    """Representation of a factory calibration - leave as is sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PK_AMPS_OVER_TRIP_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_pk_amps_over_trip_eeprom"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["PK_AMPS_OVER_TRIP_EEPROM"])
                if value is not None:
                    return value / 10.0
                return None


class MNGP_REVISIONSensor(MidniteSolarSensor):
    """Representation of a preliminary - shows unit connected sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MNGP_REVISION"
        self._attr_unique_id = f"{entry.entry_id}_mngp_revision"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MNGP_REVISION"])
                if value is not None:
                    return value
                return None


class MNLP_REVISIONSensor(MidniteSolarSensor):
    """Representation of a preliminary - shows unit connected sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MNLP_REVISION"
        self._attr_unique_id = f"{entry.entry_id}_mnlp_revision"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MNLP_REVISION"])
                if value is not None:
                    return value
                return None


class CLASSIC_MODBUS_ADDR_EEPROMSensor(MidniteSolarSensor):
    """Representation of a classic modbus address (default 10) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "CLASSIC_MODBUS_ADDR_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_classic_modbus_addr_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["CLASSIC_MODBUS_ADDR_EEPROM"])
                if value is not None:
                    return value
                return None


class BATTERY_TEMP_PASSED_EEPROMSensor(MidniteSolarSensor):
    """Representation of a follow-me temperature sensor value sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "BATTERY_TEMP_PASSED_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_battery_temp_passed_eeprom"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["BATTERY_TEMP_PASSED_EEPROM"])
                if value is not None:
                    return value
                return None


class MODBUS_CONTROL_EEPROMSensor(MidniteSolarSensor):
    """Representation of a follow-me modbus control sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MODBUS_CONTROL_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_modbus_control_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["MODBUS_CONTROL_EEPROM"])
                if value is not None:
                    return value
                return None


class CLASSIC_FME_PASSED_BITS_EEPROMSensor(MidniteSolarSensor):
    """Representation of a follow-me state bits sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "CLASSIC_FME_PASSED_BITS_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_classic_fme_passed_bits_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["CLASSIC_FME_PASSED_BITS_EEPROM"])
                if value is not None:
                    return value
                return None


class WIND_SYNCH_A_EEPROMSensor(MidniteSolarSensor):
    """Representation of a wind power tracking amps sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_SYNCH_A_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_wind_synch_a_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_SYNCH_A_EEPROM"])
                if value is not None:
                    return value
                return None


class WIND_SYNCH_V_EEPROMSensor(MidniteSolarSensor):
    """Representation of a wind power tracking volts sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIND_SYNCH_V_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_wind_synch_v_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIND_SYNCH_V_EEPROM"])
                if value is not None:
                    return value
                return None


class FOLLOW_ME_PASS_REF_EEPROMSensor(MidniteSolarSensor):
    """Representation of a follow-me enabled if > 0 - set to at least number of units in loop sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "FOLLOW_ME_PASS_REF_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_follow_me_pass_ref_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["FOLLOW_ME_PASS_REF_EEPROM"])
                if value is not None:
                    return value
                return None


class DABT_U32_DEBUG_01Sensor(MidniteSolarSensor):
    """Representation of a debug register 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DABT_U32_DEBUG_01"
        self._attr_unique_id = f"{entry.entry_id}_dabt_u32_debug_01"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DABT_U32_DEBUG_01"])
                if value is not None:
                    return value
                return None


class DABT_U32_DEBUG_02Sensor(MidniteSolarSensor):
    """Representation of a debug register 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DABT_U32_DEBUG_02"
        self._attr_unique_id = f"{entry.entry_id}_dabt_u32_debug_02"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DABT_U32_DEBUG_02"])
                if value is not None:
                    return value
                return None


class DABT_U32_DEBUG_03Sensor(MidniteSolarSensor):
    """Representation of a debug register 3 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DABT_U32_DEBUG_03"
        self._attr_unique_id = f"{entry.entry_id}_dabt_u32_debug_03"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DABT_U32_DEBUG_03"])
                if value is not None:
                    return value
                return None


class DABT_U32_DEBUG_04Sensor(MidniteSolarSensor):
    """Representation of a debug register 4 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DABT_U32_DEBUG_04"
        self._attr_unique_id = f"{entry.entry_id}_dabt_u32_debug_04"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DABT_U32_DEBUG_04"])
                if value is not None:
                    return value
                return None


class CLEAR_LOGS_CATSensor(MidniteSolarSensor):
    """Representation of a clear various logging values sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "CLEAR_LOGS_CAT"
        self._attr_unique_id = f"{entry.entry_id}_clear_logs_cat"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["CLEAR_LOGS_CAT"])
                if value is not None:
                    return value
                return None


class CLEAR_LOGS_COUNTER_10MSSensor(MidniteSolarSensor):
    """Representation of a timer for sending second clearlogscat command before timeout sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "CLEAR_LOGS_COUNTER_10MS"
        self._attr_unique_id = f"{entry.entry_id}_clear_logs_counter_10ms"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["CLEAR_LOGS_COUNTER_10MS"])
                if value is not None:
                    return value
                return None


class USER_VARIABLE_02Sensor(MidniteSolarSensor):
    """Representation of a general purpose user variable sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "USER_VARIABLE_02"
        self._attr_unique_id = f"{entry.entry_id}_user_variable_02"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["USER_VARIABLE_02"])
                if value is not None:
                    return value
                return None


class WIZBANG_RX_BUFFER_TEMP_SH1Sensor(MidniteSolarSensor):
    """Representation of a raw whizbang junior buffer read 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIZBANG_RX_BUFFER_TEMP_SH1"
        self._attr_unique_id = f"{entry.entry_id}_wizbang_rx_buffer_temp_sh1"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIZBANG_RX_BUFFER_TEMP_SH1"])
                if value is not None:
                    return value
                return None


class WIZBANG_RX_BUFFER_TEMP_SH2Sensor(MidniteSolarSensor):
    """Representation of a raw whizbang junior buffer read 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIZBANG_RX_BUFFER_TEMP_SH2"
        self._attr_unique_id = f"{entry.entry_id}_wizbang_rx_buffer_temp_sh2"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIZBANG_RX_BUFFER_TEMP_SH2"])
                if value is not None:
                    return value
                return None


class WIZBANG_RX_BUFFER_TEMP_SH3Sensor(MidniteSolarSensor):
    """Representation of a raw whizbang junior buffer read 3 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIZBANG_RX_BUFFER_TEMP_SH3"
        self._attr_unique_id = f"{entry.entry_id}_wizbang_rx_buffer_temp_sh3"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIZBANG_RX_BUFFER_TEMP_SH3"])
                if value is not None:
                    return value
                return None


class WIZBANG_RX_BUFFER_TEMP_SH4Sensor(MidniteSolarSensor):
    """Representation of a raw whizbang junior buffer read 4 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WIZBANG_RX_BUFFER_TEMP_SH4"
        self._attr_unique_id = f"{entry.entry_id}_wizbang_rx_buffer_temp_sh4"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WIZBANG_RX_BUFFER_TEMP_SH4"])
                if value is not None:
                    return value
                return None


class WJRB_CMD_S_EEPROMSensor(MidniteSolarSensor):
    """Representation of a whizbang junior command - default 0x35 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_CMD_S_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_cmd_s_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_CMD_S_EEPROM"])
                if value is not None:
                    return value
                return None


class WJRB_RAW_CURRENTSensor(MidniteSolarSensor):
    """Representation of a whizbang junior raw current sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_RAW_CURRENT"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_raw_current"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_RAW_CURRENT"])
                if value is not None:
                    return value / 10.0
                return None


class WJRB_NUMERATOR_SS_EEPROMSensor(MidniteSolarSensor):
    """Representation of a whizbang junior gain adjustment - default 0 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_NUMERATOR_SS_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_numerator_ss_eeprom"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_NUMERATOR_SS_EEPROM"])
                if value is not None:
                    return value
                return None


class WJRB_AMP_HOUR_POSITIVESensor(MidniteSolarSensor):
    """Representation of a whizbang jr. positive amp-hours (low word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_AMP_HOUR_POSITIVE"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_amp_hour_positive"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_AMP_HOUR_POSITIVE"])
                if value is not None:
                    return value / 10.0
                return None


class WJRB_AMP_HOUR_POSITIVE_HIGHSensor(MidniteSolarSensor):
    """Representation of a whizbang jr. positive amp-hours (high word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_AMP_HOUR_POSITIVE_HIGH"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_amp_hour_positive_high"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_AMP_HOUR_POSITIVE_HIGH"])
                if value is not None:
                    return value / 10.0
                return None


class WJRB_AMP_HOUR_NEGATIVESensor(MidniteSolarSensor):
    """Representation of a whizbang jr. negative amp-hours (low word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_AMP_HOUR_NEGATIVE"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_amp_hour_negative"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_AMP_HOUR_NEGATIVE"])
                if value is not None:
                    return value / 10.0
                return None


class WJRB_AMP_HOUR_NEGATIVE_HIGHSensor(MidniteSolarSensor):
    """Representation of a whizbang jr. negative amp-hours (high word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_AMP_HOUR_NEGATIVE_HIGH"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_amp_hour_negative_high"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_AMP_HOUR_NEGATIVE_HIGH"])
                if value is not None:
                    return value / 10.0
                return None


class WJRB_AMP_HOUR_NETSensor(MidniteSolarSensor):
    """Representation of a whizbang jr. net amp-hours (low word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_AMP_HOUR_NET"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_amp_hour_net"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_AMP_HOUR_NET"])
                if value is not None:
                    return value / 10.0
                return None


class WJRB_AMP_HOUR_NET_HIGHSensor(MidniteSolarSensor):
    """Representation of a whizbang jr. net amp-hours (high word) sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_AMP_HOUR_NET_HIGH"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_amp_hour_net_high"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_AMP_HOUR_NET_HIGH"])
                if value is not None:
                    return value / 10.0
                return None


class WJRB_CURRENT_32_SIGNED_EEPROMSensor(MidniteSolarSensor):
    """Representation of a whizbang jr. amps (scaled & rounded) - signed ± 3,276.7 a sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_CURRENT_32_SIGNED_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_current_32_signed_eeprom"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_CURRENT_32_SIGNED_EEPROM"])
                if value is not None:
                    return value / 10.0
                return None


class WJRB_RAW_CRC_AND_TEMPSensor(MidniteSolarSensor):
    """Representation of a raw crc << 8 | temp & 0xff + 50°c sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WJRB_RAW_CRC_AND_TEMP"
        self._attr_unique_id = f"{entry.entry_id}_wjrb_raw_crc_and_temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-alert"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["WJRB_RAW_CRC_AND_TEMP"])
                if value is not None:
                    return value
                return None


class IP_ADDRESS_LSB_1Sensor(MidniteSolarSensor):
    """Representation of a ip address part 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "IP_ADDRESS_LSB_1"
        self._attr_unique_id = f"{entry.entry_id}_ip_address_lsb_1"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["IP_ADDRESS_LSB_1"])
                if value is not None:
                    return value
                return None


class IP_ADDRESS_LSB_2Sensor(MidniteSolarSensor):
    """Representation of a ip address part 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "IP_ADDRESS_LSB_2"
        self._attr_unique_id = f"{entry.entry_id}_ip_address_lsb_2"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["IP_ADDRESS_LSB_2"])
                if value is not None:
                    return value
                return None


class GATEWAY_ADDRESS_LSB_1Sensor(MidniteSolarSensor):
    """Representation of a gateway address part 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "GATEWAY_ADDRESS_LSB_1"
        self._attr_unique_id = f"{entry.entry_id}_gateway_address_lsb_1"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["GATEWAY_ADDRESS_LSB_1"])
                if value is not None:
                    return value
                return None


class GATEWAY_ADDRESS_LSB_2Sensor(MidniteSolarSensor):
    """Representation of a gateway address part 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "GATEWAY_ADDRESS_LSB_2"
        self._attr_unique_id = f"{entry.entry_id}_gateway_address_lsb_2"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["GATEWAY_ADDRESS_LSB_2"])
                if value is not None:
                    return value
                return None


class SUBNET_MASK_LSB_1Sensor(MidniteSolarSensor):
    """Representation of a subnet mask part 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "SUBNET_MASK_LSB_1"
        self._attr_unique_id = f"{entry.entry_id}_subnet_mask_lsb_1"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["SUBNET_MASK_LSB_1"])
                if value is not None:
                    return value
                return None


class SUBNET_MASK_LSB_2Sensor(MidniteSolarSensor):
    """Representation of a subnet mask part 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "SUBNET_MASK_LSB_2"
        self._attr_unique_id = f"{entry.entry_id}_subnet_mask_lsb_2"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:help-circle"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["SUBNET_MASK_LSB_2"])
                if value is not None:
                    return value
                return None


class DNS_1_LSB_1Sensor(MidniteSolarSensor):
    """Representation of a primary dns part 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DNS_1_LSB_1"
        self._attr_unique_id = f"{entry.entry_id}_dns_1_lsb_1"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DNS_1_LSB_1"])
                if value is not None:
                    return value
                return None


class DNS_1_LSB_2Sensor(MidniteSolarSensor):
    """Representation of a primary dns part 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DNS_1_LSB_2"
        self._attr_unique_id = f"{entry.entry_id}_dns_1_lsb_2"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DNS_1_LSB_2"])
                if value is not None:
                    return value
                return None


class DNS_2_LSB_1Sensor(MidniteSolarSensor):
    """Representation of a secondary dns part 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DNS_2_LSB_1"
        self._attr_unique_id = f"{entry.entry_id}_dns_2_lsb_1"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DNS_2_LSB_1"])
                if value is not None:
                    return value
                return None


class DNS_2_LSB_2Sensor(MidniteSolarSensor):
    """Representation of a secondary dns part 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DNS_2_LSB_2"
        self._attr_unique_id = f"{entry.entry_id}_dns_2_lsb_2"
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:network"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["DNS_2_LSB_2"])
                if value is not None:
                    return value
                return None



# Special sensors that need custom logic (combining multiple registers, etc.)
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
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["REASON_FOR_RESTING"])
                if value is not None:
                    return REST_REASONS.get(value, f"Unknown ({value})")
        return None
