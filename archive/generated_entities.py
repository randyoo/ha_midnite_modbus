
# Generated Entity Classes
# DO NOT EDIT - Generated from REGISTER_CATEGORIES_ENHANCED.csv
# Run generate_entities.py to update


================================================================================
SENSORS
================================================================================

# B Sensors

class UNIT_IDSensor(MidniteSolarSensor):
    """Representation of a unit id sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "UNIT_ID"
        self._attr_unique_id = f"{entry.entry_id}_unit_id"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4101)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class UNIT_SW_DATE_ROSensor(MidniteSolarSensor):
    """Representation of a unit sw date ro sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "UNIT_SW_DATE_RO"
        self._attr_unique_id = f"{entry.entry_id}_unit_sw_date_ro"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4102)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class INFO_FLAGS_BITS3Sensor(MidniteSolarSensor):
    """Representation of a info flags bits3 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "INFO_FLAGS_BITS3"
        self._attr_unique_id = f"{entry.entry_id}_info_flags_bits3"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4104)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class MAC_ADDRESS_PART_1Sensor(MidniteSolarSensor):
    """Representation of a mac address part 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MAC_ADDRESS_PART_1"
        self._attr_unique_id = f"{entry.entry_id}_mac_address_part_1"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4106)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class MAC_ADDRESS_PART_2Sensor(MidniteSolarSensor):
    """Representation of a mac address part 2 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MAC_ADDRESS_PART_2"
        self._attr_unique_id = f"{entry.entry_id}_mac_address_part_2"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4107)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class MAC_ADDRESS_PART_3Sensor(MidniteSolarSensor):
    """Representation of a mac address part 3 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MAC_ADDRESS_PART_3"
        self._attr_unique_id = f"{entry.entry_id}_mac_address_part_3"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4108)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class STATUSROLLSensor(MidniteSolarSensor):
    """Representation of a statusroll sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "STATUSROLL"
        self._attr_unique_id = f"{entry.entry_id}_statusroll"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4113)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class RESTART_TIME_MSSensor(MidniteSolarSensor):
    """Representation of a restart time ms sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RESTART_TIME_MS"
        self._attr_unique_id = f"{entry.entry_id}_restart_time_ms"
        self._attr_device_class = SensorDeviceClass.duration
        self._attr_native_unit_of_measurement = ms
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4114)
            if value is not None:
                return value / 10.0 if ms == "V" or ms == "A" else value
        return None


class DISP_AVG_VBATTSensor(MidniteSolarSensor):
    """Representation of a disp avg vbatt sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DISP_AVG_VBATT"
        self._attr_unique_id = f"{entry.entry_id}_disp_avg_vbatt"
        self._attr_device_class = SensorDeviceClass.voltage
        self._attr_native_unit_of_measurement = V
        self._attr_state_class = SensorStateClass.measurement
        self._attr_suggested_display_precision = 1
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4115)
            if value is not None:
                return value / 10.0 if V == "V" or V == "A" else value
        return None


class DISP_AVG_VPVSensor(MidniteSolarSensor):
    """Representation of a disp avg vpv sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "DISP_AVG_VPV"
        self._attr_unique_id = f"{entry.entry_id}_disp_avg_vpv"
        self._attr_device_class = SensorDeviceClass.voltage
        self._attr_native_unit_of_measurement = V
        self._attr_state_class = SensorStateClass.measurement
        self._attr_suggested_display_precision = 1
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4116)
            if value is not None:
                return value / 10.0 if V == "V" or V == "A" else value
        return None


class IBATT_DISPLAY_SSensor(MidniteSolarSensor):
    """Representation of a ibatt display s sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "IBATT_DISPLAY_S"
        self._attr_unique_id = f"{entry.entry_id}_ibatt_display_s"
        self._attr_device_class = SensorDeviceClass.current
        self._attr_native_unit_of_measurement = A
        self._attr_state_class = SensorStateClass.measurement
        self._attr_suggested_display_precision = 1
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4117)
            if value is not None:
                return value / 10.0 if A == "V" or A == "A" else value
        return None


class KW_HOURSSensor(MidniteSolarSensor):
    """Representation of a kw hours sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "KW_HOURS"
        self._attr_unique_id = f"{entry.entry_id}_kw_hours"
        self._attr_device_class = SensorDeviceClass.energy
        self._attr_native_unit_of_measurement = kWh
        self._attr_state_class = SensorStateClass.total_increasing
        self._attr_suggested_display_precision = 2
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4118)
            if value is not None:
                return value / 10.0 if kWh == "V" or kWh == "A" else value
        return None


class WATTSSensor(MidniteSolarSensor):
    """Representation of a watts sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WATTS"
        self._attr_unique_id = f"{entry.entry_id}_watts"
        self._attr_device_class = SensorDeviceClass.power
        self._attr_native_unit_of_measurement = W
        self._attr_state_class = SensorStateClass.measurement
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4119)
            if value is not None:
                return value / 10.0 if W == "V" or W == "A" else value
        return None


class COMBO_CHARGE_STAGESensor(MidniteSolarSensor):
    """Representation of a combo charge stage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "COMBO_CHARGE_STAGE"
        self._attr_unique_id = f"{entry.entry_id}_combo_charge_stage"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4120)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class PV_INPUT_CURRENTSensor(MidniteSolarSensor):
    """Representation of a pv input current sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PV_INPUT_CURRENT"
        self._attr_unique_id = f"{entry.entry_id}_pv_input_current"
        self._attr_device_class = SensorDeviceClass.current
        self._attr_native_unit_of_measurement = A
        self._attr_state_class = SensorStateClass.measurement
        self._attr_suggested_display_precision = 1
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4121)
            if value is not None:
                return value / 10.0 if A == "V" or A == "A" else value
        return None


class VOC_LAST_MEASUREDSensor(MidniteSolarSensor):
    """Representation of a voc last measured sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VOC_LAST_MEASURED"
        self._attr_unique_id = f"{entry.entry_id}_voc_last_measured"
        self._attr_device_class = SensorDeviceClass.voltage
        self._attr_native_unit_of_measurement = V
        self._attr_state_class = SensorStateClass.measurement
        self._attr_suggested_display_precision = 1
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4122)
            if value is not None:
                return value / 10.0 if V == "V" or V == "A" else value
        return None


class AMP_HOURS_DAILYSensor(MidniteSolarSensor):
    """Representation of a amp hours daily sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "AMP_HOURS_DAILY"
        self._attr_unique_id = f"{entry.entry_id}_amp_hours_daily"
        self._attr_device_class = SensorDeviceClass.energy
        self._attr_native_unit_of_measurement = Ah
        self._attr_state_class = SensorStateClass.total_increasing
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4125)
            if value is not None:
                return value / 10.0 if Ah == "V" or Ah == "A" else value
        return None


class LIFETIME_KW_HOURS_1Sensor(MidniteSolarSensor):
    """Representation of a lifetime kw hours 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "LIFETIME_KW_HOURS_1"
        self._attr_unique_id = f"{entry.entry_id}_lifetime_kw_hours_1"
        self._attr_device_class = SensorDeviceClass.energy
        self._attr_native_unit_of_measurement = kWh
        self._attr_state_class = SensorStateClass.total_increasing
        self._attr_suggested_display_precision = 2
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4126)
            if value is not None:
                return value / 10.0 if kWh == "V" or kWh == "A" else value
        return None


class LIFETIME_AMP_HOURS_1Sensor(MidniteSolarSensor):
    """Representation of a lifetime amp hours 1 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "LIFETIME_AMP_HOURS_1"
        self._attr_unique_id = f"{entry.entry_id}_lifetime_amp_hours_1"
        self._attr_device_class = SensorDeviceClass.energy
        self._attr_native_unit_of_measurement = Ah
        self._attr_state_class = SensorStateClass.total_increasing
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4128)
            if value is not None:
                return value / 10.0 if Ah == "V" or Ah == "A" else value
        return None


class BATT_TEMPERATURESensor(MidniteSolarSensor):
    """Representation of a batt temperature sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "BATT_TEMPERATURE"
        self._attr_unique_id = f"{entry.entry_id}_batt_temperature"
        self._attr_device_class = SensorDeviceClass.temperature
        self._attr_native_unit_of_measurement = °C
        self._attr_state_class = SensorStateClass.measurement
        self._attr_suggested_display_precision = 1
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4132)
            if value is not None:
                return value / 10.0 if °C == "V" or °C == "A" else value
        return None


class FET_TEMPERATURESensor(MidniteSolarSensor):
    """Representation of a fet temperature sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "FET_TEMPERATURE"
        self._attr_unique_id = f"{entry.entry_id}_fet_temperature"
        self._attr_device_class = SensorDeviceClass.temperature
        self._attr_native_unit_of_measurement = °C
        self._attr_state_class = SensorStateClass.measurement
        self._attr_suggested_display_precision = 1
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4133)
            if value is not None:
                return value / 10.0 if °C == "V" or °C == "A" else value
        return None


class PCB_TEMPERATURESensor(MidniteSolarSensor):
    """Representation of a pcb temperature sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PCB_TEMPERATURE"
        self._attr_unique_id = f"{entry.entry_id}_pcb_temperature"
        self._attr_device_class = SensorDeviceClass.temperature
        self._attr_native_unit_of_measurement = °C
        self._attr_state_class = SensorStateClass.measurement
        self._attr_suggested_display_precision = 1
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4134)
            if value is not None:
                return value / 10.0 if °C == "V" or °C == "A" else value
        return None


class FLOAT_TIME_TODAY_SECSensor(MidniteSolarSensor):
    """Representation of a float time today sec sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "FLOAT_TIME_TODAY_SEC"
        self._attr_unique_id = f"{entry.entry_id}_float_time_today_sec"
        self._attr_device_class = SensorDeviceClass.duration
        self._attr_native_unit_of_measurement = s
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4138)
            if value is not None:
                return value / 10.0 if s == "V" or s == "A" else value
        return None


class ABSORB_TIMESensor(MidniteSolarSensor):
    """Representation of a absorb time sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "ABSORB_TIME"
        self._attr_unique_id = f"{entry.entry_id}_absorb_time"
        self._attr_device_class = SensorDeviceClass.duration
        self._attr_native_unit_of_measurement = s
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4139)
            if value is not None:
                return value / 10.0 if s == "V" or s == "A" else value
        return None


class EQUALIZE_TIMESensor(MidniteSolarSensor):
    """Representation of a equalize time sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQUALIZE_TIME"
        self._attr_unique_id = f"{entry.entry_id}_equalize_time"
        self._attr_device_class = SensorDeviceClass.duration
        self._attr_native_unit_of_measurement = s
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if B == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4143)
            if value is not None:
                return value / 10.0 if s == "V" or s == "A" else value
        return None


# A Sensors

class MATCH_POINT_SHADOWSensor(MidniteSolarSensor):
    """Representation of a match point shadow sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MATCH_POINT_SHADOW"
        self._attr_unique_id = f"{entry.entry_id}_match_point_shadow"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if A == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4124)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class MPP_W_LASTSensor(MidniteSolarSensor):
    """Representation of a mpp w last sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "MPP_W_LAST"
        self._attr_unique_id = f"{entry.entry_id}_mpp_w_last"
        self._attr_device_class = SensorDeviceClass.power
        self._attr_native_unit_of_measurement = W
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if A == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4145)
            if value is not None:
                return value / 10.0 if W == "V" or W == "A" else value
        return None


class VARIMAXSensor(MidniteSolarSensor):
    """Representation of a varimax sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "VARIMAX"
        self._attr_unique_id = f"{entry.entry_id}_varimax"
        self._attr_device_class = SensorDeviceClass.current
        self._attr_native_unit_of_measurement = A
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if A == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4180)
            if value is not None:
                return value / 10.0 if A == "V" or A == "A" else value
        return None


class ENABLE_FLAGS3Sensor(MidniteSolarSensor):
    """Representation of a enable flags3 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "ENABLE_FLAGS3"
        self._attr_unique_id = f"{entry.entry_id}_enable_flags3"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if A == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4182)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


# D Sensors

class RESERVED_4105Sensor(MidniteSolarSensor):
    """Representation of a reserved 4105 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RESERVED_4105"
        self._attr_unique_id = f"{entry.entry_id}_reserved_4105"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if D == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4105)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class RESERVED_4171Sensor(MidniteSolarSensor):
    """Representation of a reserved 4171 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RESERVED_4171"
        self._attr_unique_id = f"{entry.entry_id}_reserved_4171"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if D == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4171)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class RESERVED_4185Sensor(MidniteSolarSensor):
    """Representation of a reserved 4185 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RESERVED_4185"
        self._attr_unique_id = f"{entry.entry_id}_reserved_4185"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if D == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4185)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class RESERVED_4188Sensor(MidniteSolarSensor):
    """Representation of a reserved 4188 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RESERVED_4188"
        self._attr_unique_id = f"{entry.entry_id}_reserved_4188"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if D == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4188)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class RESERVED_4195Sensor(MidniteSolarSensor):
    """Representation of a reserved 4195 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RESERVED_4195"
        self._attr_unique_id = f"{entry.entry_id}_reserved_4195"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if D == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4195)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


class RESERVED_4196Sensor(MidniteSolarSensor):
    """Representation of a reserved 4196 sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RESERVED_4196"
        self._attr_unique_id = f"{entry.entry_id}_reserved_4196"
        self._attr_device_class = SensorDeviceClass.None
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = SensorStateClass.None
        self._attr_suggested_display_precision = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if D == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value(4196)
            if value is not None:
                return value / 10.0 if "" == "V" or "" == "A" else value
        return None


================================================================================
NUMBERS
================================================================================

# B Numbers

class BATTERY_OUTPUT_CURRENT_LIMITNumber(MidniteSolarNumber):
    """Number to set battery output current limit."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "BATTERY_OUTPUT_CURRENT_LIMIT"
        self._attr_unique_id = f"{entry.entry_id}_battery_output_current_limit"
        self._attr_native_unit_of_measurement = A
        self.register_address = REGISTER_MAP["BATTERY_OUTPUT_CURRENT_LIMIT"]
        # Typical range based on unit
        if A == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif A == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif A == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 1.0
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class ABSORB_SETPOINT_VOLTAGENumber(MidniteSolarNumber):
    """Number to set absorb setpoint voltage."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "ABSORB_SETPOINT_VOLTAGE"
        self._attr_unique_id = f"{entry.entry_id}_absorb_setpoint_voltage"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class FLOAT_VOLTAGE_SETPOINTNumber(MidniteSolarNumber):
    """Number to set float voltage setpoint."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "FLOAT_VOLTAGE_SETPOINT"
        self._attr_unique_id = f"{entry.entry_id}_float_voltage_setpoint"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["FLOAT_VOLTAGE_SETPOINT"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class EQUALIZE_VOLTAGE_SETPOINTNumber(MidniteSolarNumber):
    """Number to set equalize voltage setpoint."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQUALIZE_VOLTAGE_SETPOINT"
        self._attr_unique_id = f"{entry.entry_id}_equalize_voltage_setpoint"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["EQUALIZE_VOLTAGE_SETPOINT"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class ABSORB_TIME_EEPROMNumber(MidniteSolarNumber):
    """Number to set absorb time eeprom."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "ABSORB_TIME_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_absorb_time_eeprom"
        self._attr_native_unit_of_measurement = s
        self.register_address = REGISTER_MAP["ABSORB_TIME_EEPROM"]
        # Typical range based on unit
        if s == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif s == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif s == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 60.0
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class EQUALIZE_TIME_EEPROMNumber(MidniteSolarNumber):
    """Number to set equalize time eeprom."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQUALIZE_TIME_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_equalize_time_eeprom"
        self._attr_native_unit_of_measurement = s
        self.register_address = REGISTER_MAP["EQUALIZE_TIME_EEPROM"]
        # Typical range based on unit
        if s == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif s == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif s == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 60.0
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class EQUALIZE_INTERVAL_DAYS_EEPROMNumber(MidniteSolarNumber):
    """Number to set equalize interval days eeprom."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "EQUALIZE_INTERVAL_DAYS_EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_equalize_interval_days_eeprom"
        self._attr_native_unit_of_measurement = days
        self.register_address = REGISTER_MAP["EQUALIZE_INTERVAL_DAYS_EEPROM"]
        # Typical range based on unit
        if days == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif days == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif days == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 1.0
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


# A Numbers

class MINUTE_LOG_INTERVAL_SECNumber(MidniteSolarNumber):
    """Number to set minute log interval sec."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "MINUTE_LOG_INTERVAL_SEC"
        self._attr_unique_id = f"{entry.entry_id}_minute_log_interval_sec"
        self._attr_native_unit_of_measurement = s
        self.register_address = REGISTER_MAP["MINUTE_LOG_INTERVAL_SEC"]
        # Typical range based on unit
        if s == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif s == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif s == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 60.0
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class MODBUS_PORT_REGISTERNumber(MidniteSolarNumber):
    """Number to set modbus port register."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "MODBUS_PORT_REGISTER"
        self._attr_unique_id = f"{entry.entry_id}_modbus_port_register"
        self._attr_native_unit_of_measurement = ""
        self.register_address = REGISTER_MAP["MODBUS_PORT_REGISTER"]
        # Typical range based on unit
        if "" == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif "" == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif "" == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.0
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class MAX_BATTERY_TEMP_COMP_VOLTAGENumber(MidniteSolarNumber):
    """Number to set max battery temp comp voltage."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "MAX_BATTERY_TEMP_COMP_VOLTAGE"
        self._attr_unique_id = f"{entry.entry_id}_max_battery_temp_comp_voltage"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["MAX_BATTERY_TEMP_COMP_VOLTAGE"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class MIN_BATTERY_TEMP_COMP_VOLTAGENumber(MidniteSolarNumber):
    """Number to set min battery temp comp voltage."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "MIN_BATTERY_TEMP_COMP_VOLTAGE"
        self._attr_unique_id = f"{entry.entry_id}_min_battery_temp_comp_voltage"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["MIN_BATTERY_TEMP_COMP_VOLTAGE"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class BATTERY_TEMP_COMP_VALUENumber(MidniteSolarNumber):
    """Number to set battery temp comp value."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "BATTERY_TEMP_COMP_VALUE"
        self._attr_unique_id = f"{entry.entry_id}_battery_temp_comp_value"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["BATTERY_TEMP_COMP_VALUE"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class AUX1_VOLTS_LO_ABSNumber(MidniteSolarNumber):
    """Number to set aux1 volts lo abs."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX1_VOLTS_LO_ABS"
        self._attr_unique_id = f"{entry.entry_id}_aux1_volts_lo_abs"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["AUX1_VOLTS_LO_ABS"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class AUX1_DELAY_T_MSNumber(MidniteSolarNumber):
    """Number to set aux1 delay t ms."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX1_DELAY_T_MS"
        self._attr_unique_id = f"{entry.entry_id}_aux1_delay_t_ms"
        self._attr_native_unit_of_measurement = ms
        self.register_address = REGISTER_MAP["AUX1_DELAY_T_MS"]
        # Typical range based on unit
        if ms == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif ms == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif ms == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 100.0
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class AUX1_HOLD_T_MSNumber(MidniteSolarNumber):
    """Number to set aux1 hold t ms."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX1_HOLD_T_MS"
        self._attr_unique_id = f"{entry.entry_id}_aux1_hold_t_ms"
        self._attr_native_unit_of_measurement = ms
        self.register_address = REGISTER_MAP["AUX1_HOLD_T_MS"]
        # Typical range based on unit
        if ms == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif ms == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif ms == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 100.0
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class AUX2_PWM_VWIDTHNumber(MidniteSolarNumber):
    """Number to set aux2 pwm vwidth."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX2_PWM_VWIDTH"
        self._attr_unique_id = f"{entry.entry_id}_aux2_pwm_vwidth"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["AUX2_PWM_VWIDTH"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class AUX1_VOLTS_HI_ABSNumber(MidniteSolarNumber):
    """Number to set aux1 volts hi abs."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX1_VOLTS_HI_ABS"
        self._attr_unique_id = f"{entry.entry_id}_aux1_volts_hi_abs"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["AUX1_VOLTS_HI_ABS"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class AUX2_VOLTS_HI_ABSNumber(MidniteSolarNumber):
    """Number to set aux2 volts hi abs."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX2_VOLTS_HI_ABS"
        self._attr_unique_id = f"{entry.entry_id}_aux2_volts_hi_abs"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["AUX2_VOLTS_HI_ABS"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class VBATT_OFFSETNumber(MidniteSolarNumber):
    """Number to set vbatt offset."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "VBATT_OFFSET"
        self._attr_unique_id = f"{entry.entry_id}_vbatt_offset"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["VBATT_OFFSET"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


class VPV_OFFSETNumber(MidniteSolarNumber):
    """Number to set vpv offset."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_name = "VPV_OFFSET"
        self._attr_unique_id = f"{entry.entry_id}_vpv_offset"
        self._attr_native_unit_of_measurement = V
        self.register_address = REGISTER_MAP["VPV_OFFSET"]
        # Typical range based on unit
        if V == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif V == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif V == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = 0.1
        
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)


================================================================================
SELECTS
================================================================================

# A Selects

class USB_COMM_MODESelect(MidniteSolarSelect):
    """Select to set usb comm mode."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the select."""
        super().__init__(coordinator, entry)
        self._attr_name = "USB_COMM_MODE"
        self._attr_unique_id = f"{entry.entry_id}_usb_comm_mode"
        self.register_address = REGISTER_MAP["USB_COMM_MODE"]
        # Options will be defined based on register specifics
        
    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        value = self.coordinator.get_register_value(4146)
        if value is not None:
            # Map value to option - will be customized per select
            return "Option " + str(value)
        return None
    
    async def async_select_option(self, option: str) -> None:
        """Update the selected option."""
        # Map option to value - will be customized per select
        await self._async_set_value(0)


class MPPT_MODESelect(MidniteSolarSelect):
    """Select to set mppt mode."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the select."""
        super().__init__(coordinator, entry)
        self._attr_name = "MPPT_MODE"
        self._attr_unique_id = f"{entry.entry_id}_mppt_mode"
        self.register_address = REGISTER_MAP["MPPT_MODE"]
        # Options will be defined based on register specifics
        
    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        value = self.coordinator.get_register_value(4164)
        if value is not None:
            # Map value to option - will be customized per select
            return "Option " + str(value)
        return None
    
    async def async_select_option(self, option: str) -> None:
        """Update the selected option."""
        # Map option to value - will be customized per select
        await self._async_set_value(0)


class AUX_1_AND_2_FUNCTIONSelect(MidniteSolarSelect):
    """Select to set aux 1 and 2 function."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the select."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX_1_AND_2_FUNCTION"
        self._attr_unique_id = f"{entry.entry_id}_aux_1_and_2_function"
        self.register_address = REGISTER_MAP["AUX_1_AND_2_FUNCTION"]
        # Options will be defined based on register specifics
        
    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        value = self.coordinator.get_register_value(4165)
        if value is not None:
            # Map value to option - will be customized per select
            return "Option " + str(value)
        return None
    
    async def async_select_option(self, option: str) -> None:
        """Update the selected option."""
        # Map option to value - will be customized per select
        await self._async_set_value(0)


================================================================================
ENTITY REGISTRATION HELPERS
================================================================================

# SENSOR Registration Helper
def get_sensor_list(entry: Any) -> list:
    """Get list of entities based on configuration."""
    # B sensors
    entities.append(UNIT_IDSensor(coordinator, entry))
    entities.append(UNIT_SW_DATE_ROSensor(coordinator, entry))
    entities.append(INFO_FLAGS_BITS3Sensor(coordinator, entry))
    entities.append(MAC_ADDRESS_PART_1Sensor(coordinator, entry))
    entities.append(MAC_ADDRESS_PART_2Sensor(coordinator, entry))
    entities.append(MAC_ADDRESS_PART_3Sensor(coordinator, entry))
    entities.append(STATUSROLLSensor(coordinator, entry))
    entities.append(RESTART_TIME_MSSensor(coordinator, entry))
    entities.append(DISP_AVG_VBATTSensor(coordinator, entry))
    entities.append(DISP_AVG_VPVSensor(coordinator, entry))
    entities.append(IBATT_DISPLAY_SSensor(coordinator, entry))
    entities.append(KW_HOURSSensor(coordinator, entry))
    entities.append(WATTSSensor(coordinator, entry))
    entities.append(COMBO_CHARGE_STAGESensor(coordinator, entry))
    entities.append(PV_INPUT_CURRENTSensor(coordinator, entry))
    entities.append(VOC_LAST_MEASUREDSensor(coordinator, entry))
    entities.append(AMP_HOURS_DAILYSensor(coordinator, entry))
    entities.append(LIFETIME_KW_HOURS_1Sensor(coordinator, entry))
    entities.append(LIFETIME_AMP_HOURS_1Sensor(coordinator, entry))
    entities.append(BATT_TEMPERATURESensor(coordinator, entry))
    entities.append(FET_TEMPERATURESensor(coordinator, entry))
    entities.append(PCB_TEMPERATURESensor(coordinator, entry))
    entities.append(FLOAT_TIME_TODAY_SECSensor(coordinator, entry))
    entities.append(ABSORB_TIMESensor(coordinator, entry))
    entities.append(EQUALIZE_TIMESensor(coordinator, entry))
    # A sensors
    if should_create_entity(entry, "MATCH_POINT_SHADOW"):
        entities.append(MATCH_POINT_SHADOWSensor(coordinator, entry))
    if should_create_entity(entry, "MPP_W_LAST"):
        entities.append(MPP_W_LASTSensor(coordinator, entry))
    if should_create_entity(entry, "VARIMAX"):
        entities.append(VARIMAXSensor(coordinator, entry))
    if should_create_entity(entry, "ENABLE_FLAGS3"):
        entities.append(ENABLE_FLAGS3Sensor(coordinator, entry))
    # D sensors
    if should_create_entity(entry, "RESERVED_4105"):
        entities.append(RESERVED_4105Sensor(coordinator, entry))
    if should_create_entity(entry, "RESERVED_4171"):
        entities.append(RESERVED_4171Sensor(coordinator, entry))
    if should_create_entity(entry, "RESERVED_4185"):
        entities.append(RESERVED_4185Sensor(coordinator, entry))
    if should_create_entity(entry, "RESERVED_4188"):
        entities.append(RESERVED_4188Sensor(coordinator, entry))
    if should_create_entity(entry, "RESERVED_4195"):
        entities.append(RESERVED_4195Sensor(coordinator, entry))
    if should_create_entity(entry, "RESERVED_4196"):
        entities.append(RESERVED_4196Sensor(coordinator, entry))
    return entities

# NUMBER Registration Helper
def get_number_list(entry: Any) -> list:
    """Get list of entities based on configuration."""
    # B numbers
    entities.append(BATTERY_OUTPUT_CURRENT_LIMITNumber(coordinator, entry))
    entities.append(ABSORB_SETPOINT_VOLTAGENumber(coordinator, entry))
    entities.append(FLOAT_VOLTAGE_SETPOINTNumber(coordinator, entry))
    entities.append(EQUALIZE_VOLTAGE_SETPOINTNumber(coordinator, entry))
    entities.append(ABSORB_TIME_EEPROMNumber(coordinator, entry))
    entities.append(EQUALIZE_TIME_EEPROMNumber(coordinator, entry))
    entities.append(EQUALIZE_INTERVAL_DAYS_EEPROMNumber(coordinator, entry))
    # A numbers
    if should_create_entity(entry, "MINUTE_LOG_INTERVAL_SEC"):
        entities.append(MINUTE_LOG_INTERVAL_SECNumber(coordinator, entry))
    if should_create_entity(entry, "MODBUS_PORT_REGISTER"):
        entities.append(MODBUS_PORT_REGISTERNumber(coordinator, entry))
    if should_create_entity(entry, "MAX_BATTERY_TEMP_COMP_VOLTAGE"):
        entities.append(MAX_BATTERY_TEMP_COMP_VOLTAGENumber(coordinator, entry))
    if should_create_entity(entry, "MIN_BATTERY_TEMP_COMP_VOLTAGE"):
        entities.append(MIN_BATTERY_TEMP_COMP_VOLTAGENumber(coordinator, entry))
    if should_create_entity(entry, "BATTERY_TEMP_COMP_VALUE"):
        entities.append(BATTERY_TEMP_COMP_VALUENumber(coordinator, entry))
    if should_create_entity(entry, "AUX1_VOLTS_LO_ABS"):
        entities.append(AUX1_VOLTS_LO_ABSNumber(coordinator, entry))
    if should_create_entity(entry, "AUX1_DELAY_T_MS"):
        entities.append(AUX1_DELAY_T_MSNumber(coordinator, entry))
    if should_create_entity(entry, "AUX1_HOLD_T_MS"):
        entities.append(AUX1_HOLD_T_MSNumber(coordinator, entry))
    if should_create_entity(entry, "AUX2_PWM_VWIDTH"):
        entities.append(AUX2_PWM_VWIDTHNumber(coordinator, entry))
    if should_create_entity(entry, "AUX1_VOLTS_HI_ABS"):
        entities.append(AUX1_VOLTS_HI_ABSNumber(coordinator, entry))
    if should_create_entity(entry, "AUX2_VOLTS_HI_ABS"):
        entities.append(AUX2_VOLTS_HI_ABSNumber(coordinator, entry))
    if should_create_entity(entry, "VBATT_OFFSET"):
        entities.append(VBATT_OFFSETNumber(coordinator, entry))
    if should_create_entity(entry, "VPV_OFFSET"):
        entities.append(VPV_OFFSETNumber(coordinator, entry))
    return entities

# SELECT Registration Helper
def get_select_list(entry: Any) -> list:
    """Get list of entities based on configuration."""
    # A selects
    if should_create_entity(entry, "USB_COMM_MODE"):
        entities.append(USB_COMM_MODESelect(coordinator, entry))
    if should_create_entity(entry, "MPPT_MODE"):
        entities.append(MPPT_MODESelect(coordinator, entry))
    if should_create_entity(entry, "AUX_1_AND_2_FUNCTION"):
        entities.append(AUX_1_AND_2_FUNCTIONSelect(coordinator, entry))
    return entities

================================================================================
SUMMARY
================================================================================

Total Sensors: 35
  - Basic: 25
  - Advanced: 4
  - Debug: 6

Total Numbers: 20
  - Basic: 7
  - Advanced: 13
  - Debug: 0

Total Selects: 3
  - Basic: 0
  - Advanced: 3
  - Debug: 0
