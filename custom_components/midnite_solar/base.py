"""Module defines entity descriptions for Midnite Solar components."""

from dataclasses import dataclass

from homeassistant.helpers.entity import EntityDescription


@dataclass
class MidniteBaseEntityDescription(EntityDescription):
    """The entity description shared by the platforms.

    It carries device identity only: every entity reads its registers through
    the coordinator directly, so there is no value_fn plumbing (the old default
    was a lambda nothing ever called).
    """

    @staticmethod
    def serial_number(coordinator):
        """The Classic's serial number, from registers 28673/28674.

        The register map identifies a Classic by this number: it is what the
        write unlock is built from and what a label on the case says. The
        32-bit device ID in 4111/4112 is a device type stamp, not a serial.
        """
        if not coordinator.data or "data" not in coordinator.data:
            return None
        serial_data = coordinator.data["data"].get("serial")
        if not serial_data:
            return None
        from .const import REGISTER_MAP
        from .register_values import serial_from_registers

        msb = serial_data.get(REGISTER_MAP["SERIAL_NUMBER_MSB_RO"])
        lsb = serial_data.get(REGISTER_MAP["SERIAL_NUMBER_LSB_RO"])
        if msb is None or lsb is None:
            return None
        # A string: the device registry takes serial_number as text and logs a
        # breaking change for ints ("This will stop working in Home Assistant
        # 2026.12.0", observed every platform on the dev bench 2026-09-20).
        return str(serial_from_registers(msb, lsb))

    @staticmethod
    def get_device_info(coordinator, entry, domain):
        """Extract device info from coordinator data.

        This runs once per entity on nearly every state check (roughly 150
        entities per update), so it logs nothing on the happy path.
        """
        # Try to get device ID from coordinator data (registers 4111-4112)
        if coordinator.data and "data" in coordinator.data:
            device_info_data = coordinator.data["data"].get("device_info")
            if device_info_data:
                from .const import REGISTER_MAP, DEVICE_TYPES
                
                low_word = device_info_data.get(REGISTER_MAP["DEVICE_ID_LOW_WORD"])
                high_word = device_info_data.get(REGISTER_MAP["DEVICE_ID_HIGH_WORD"])
                if low_word is not None and high_word is not None:
                    device_id = (high_word << 16) | low_word
                    # Try to get device model from UNIT_ID register
                    unit_id_value = device_info_data.get(REGISTER_MAP["UNIT_ID"])
                    if unit_id_value is not None:
                        device_type = unit_id_value & 0xFF  # Get LSB (unit type)
                        model = DEVICE_TYPES.get(device_type, f"Unknown ({device_type})")
                    else:
                        model = "Midnite Solar Device"
                     
                    # Get PCB revision from UNIT_ID register (bits 8-15)
                    pcb_revision = None
                    if unit_id_value is not None:
                        pcb_revision = (unit_id_value >> 8) & 0xFF
                     
                    # Get software build date
                    sw_date_ro = device_info_data.get(REGISTER_MAP["UNIT_SW_DATE_RO"])
                    sw_date_month_day = device_info_data.get(REGISTER_MAP["UNIT_SW_DATE_MONTH_DAY"])
                    sw_build_date = None
                    if sw_date_ro is not None and sw_date_month_day is not None:
                        # Format: YYYY-MM-DD from two registers.
                        # Register 4102 contains year, register 4103 has MSB=month,
                        # LSB=day. f-string formatting cannot raise ValueError or
                        # TypeError here, so there is nothing to catch.
                        year = sw_date_ro & 0xFFFF  # Get full 16-bit value for year
                        month = (sw_date_month_day >> 8) & 0xFF  # Extract high byte (MSB)
                        day = sw_date_month_day & 0xFF  # Extract low byte (LSB)
                        sw_build_date = f"{year:04d}-{month:02d}-{day:02d}"
                     
                    return {
                        "identifiers": {(domain, str(device_id))},
                        "name": f"{model} ({device_id})",
                        "manufacturer": "Midnite Solar",
                        "model": model,
                        "hw_version": f"PCB {pcb_revision}" if pcb_revision is not None else None,
                        "sw_version": sw_build_date,
                        "serial_number": MidniteBaseEntityDescription.serial_number(coordinator),
                    }
        
        # Fallback to entry_id if device ID not available
        return {
            "identifiers": {(domain, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
            "serial_number": MidniteBaseEntityDescription.serial_number(coordinator),
        }
