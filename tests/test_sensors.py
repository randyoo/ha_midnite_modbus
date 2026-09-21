"""Tests for the values the integration reports, quoted from the register map.

No Midnite Classic and no Home Assistant are needed; the register map is the
authority for every expected number here.
"""

from __future__ import annotations

import pytest

from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry

from midnite_solar.sensor import (
    BatteryTemperatureSensor,
    DNSSensor1,
    DNSSensor2,
    FETTemperatureSensor,
    GatewayAddressSensor,
    IPAddressSensor,
    LifetimeAmpHoursSensor,
    LifetimeEnergySensor,
    PCBTemperatureSensor,
    SlidingCurrentLimitSensor,
    SubnetMaskSensor,
)


@pytest.fixture
def hass():
    from homeassistant.core import Hass

    return Hass()


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def sensor(hass, entry, cls, group, registers):
    coordinator = FakeCoordinator(hass, FakeApi(), {group: dict(registers)})
    return cls(coordinator, entry), coordinator


class TestTemperatureNoiseFilter:
    """4132/4133/4134 are "([4132] /10)" degrees C, negative as two's complement."""

    def test_stable_readings_are_reported(self, hass, entry):
        sensor_obj, _ = sensor(hass, entry, BatteryTemperatureSensor, "temperatures", {4132: 250})
        assert sensor_obj.native_value == pytest.approx(25.0)

    def test_negative_temperatures_are_signed(self, hass, entry):
        sensor_obj, _ = sensor(hass, entry, BatteryTemperatureSensor, "temperatures", {4132: 65535})
        assert sensor_obj.native_value == pytest.approx(-0.1)

    @pytest.mark.parametrize(
        ("raw", "expected"), [(250, 25.0), (500, 50.0), (1500, 150.0), (65436, -10.0), (65535, -0.1)]
    )
    def test_every_temperature_sensor_scales_the_same(self, hass, entry, raw, expected):
        for cls, address in (
            (BatteryTemperatureSensor, 4132),
            (FETTemperatureSensor, 4133),
            (PCBTemperatureSensor, 4134),
        ):
            sensor_obj, _ = sensor(hass, entry, cls, "temperatures", {address: raw})
            assert sensor_obj.native_value == pytest.approx(expected)

    def test_a_reading_outside_physical_range_is_dropped_immediately(self, hass, entry):
        """No Classic sensor is ever at 300 °C, so that is dropped on first sight."""
        sensor_obj, _ = sensor(hass, entry, BatteryTemperatureSensor, "temperatures", {4132: 3000})
        assert sensor_obj.native_value is None

    def test_a_single_bogus_reading_is_dropped(self, hass, entry):
        """An unplugged probe reads far outside anything physical."""
        sensor_obj, _ = sensor(hass, entry, BatteryTemperatureSensor, "temperatures", {4132: 250})
        for _ in range(3):
            sensor_obj.native_value
        coordinator = sensor_obj.coordinator
        coordinator.data["data"]["temperatures"][4132] = 3000  # 300 °C
        assert sensor_obj.native_value is None
        assert sensor_obj.extra_state_attributes == {"rejected_readings": 1}
        coordinator.data["data"]["temperatures"][4132] = 250
        assert sensor_obj.native_value == pytest.approx(25.0)

    def test_the_real_temperature_survives_repeated_spikes(self, hass, entry):
        """The classic symptom: good readings and 300 °C readings alternating."""
        sensor_obj, _ = sensor(hass, entry, BatteryTemperatureSensor, "temperatures", {4132: 250})
        published = []
        for raw in [250, 250, 250, 250, 3000, 250, 3000, 250, 3000, 250]:
            sensor_obj.coordinator.data["data"]["temperatures"][4132] = raw
            value = sensor_obj.native_value
            if value is not None:
                published.append(value)
        assert published[-1] == pytest.approx(25.0)
        assert max(published) < 100.0

    def test_a_warm_battery_is_still_reported(self, hass, entry):
        """Absorbing can push a battery up; the filter must follow, not stall."""
        sensor_obj, _ = sensor(hass, entry, BatteryTemperatureSensor, "temperatures", {4132: 250})
        for _ in range(3):
            sensor_obj.native_value
        published = []
        for raw in (320, 340, 360, 380, 400):
            sensor_obj.coordinator.data["data"]["temperatures"][4132] = raw
            value = sensor_obj.native_value
            if value is not None:
                published.append(value)
        assert published, "a gradual warm-up must not be filtered away forever"
        assert published[-1] == pytest.approx(36.0) or published[0] == pytest.approx(32.0)


class TestScalingFixes:
    """Registers the map gives with no divisor."""

    def test_sliding_current_limit_is_whole_amps(self, hass, entry):
        """Spec: "4152 R Sliding Current Limit [4152] Amps"."""
        sensor_obj, _ = sensor(hass, entry, SlidingCurrentLimitSensor, "settings", {4152: 12})
        assert sensor_obj.native_value == 12.0

    def test_lifetime_energy_is_tenths_of_kilowatt_hours(self, hass, entry):
        """Map formula has no divisor, but the Classic's display shows one decimal
        place: bench-confirmed register 109917 reads as 10991.7 kWh, so it is tenths."""
        sensor_obj, _ = sensor(hass, entry, LifetimeEnergySensor, "energy", {4126: 12345, 4127: 0})
        assert sensor_obj.native_value == 1234.5

    def test_lifetime_energy_uses_the_high_word(self, hass, entry):
        sensor_obj, _ = sensor(hass, entry, LifetimeEnergySensor, "energy", {4126: 1, 4127: 1})
        assert sensor_obj.native_value == pytest.approx(6553.7)

    def test_the_bench_lifetime_energy(self, hass, entry):
        """The exact registers read back from the live Classic: 10991.7 kWh."""
        sensor_obj, _ = sensor(hass, entry, LifetimeEnergySensor, "energy", {4126: 0xAD5D, 4127: 0x0001})
        assert sensor_obj.native_value == pytest.approx(10991.7)

    def test_lifetime_amp_hours_is_amp_hours(self, hass, entry):
        """Spec: "(([4129] << 16) + [4128]) Amp Hours" - no divisor (bench: 202213 Ah)."""
        sensor_obj, _ = sensor(hass, entry, LifetimeAmpHoursSensor, "energy", {4128: 4321, 4129: 2})
        assert sensor_obj.native_value == (2 << 16) + 4321


class TestNetworkAddresses:
    """A real Classic stores the address reversed from how the map prints it.

    Bench-confirmed (192.168.88.24): 20482=0xA8C0, 20483=0x1858 - the lower register
    holds the first two octets and each register is read low byte first.
    """

    @pytest.mark.parametrize(
        ("cls", "low_address"),
        [
            (IPAddressSensor, 20482),
            (GatewayAddressSensor, 20484),
            (SubnetMaskSensor, 20486),
            (DNSSensor1, 20488),
            (DNSSensor2, 20490),
        ],
    )
    def test_lower_register_supplies_the_first_octet(self, hass, entry, cls, low_address):
        registers = {low_address: 0xA8C0, low_address + 1: 0x1858}
        sensor_obj, _ = sensor(hass, entry, cls, "network", registers)
        assert sensor_obj.native_value == "192.168.88.24"

    def test_the_octets_are_never_reversed(self, hass, entry):
        """The map's literal order would report 192.168.88.24 as 24.88.168.192."""
        sensor_obj, _ = sensor(hass, entry, IPAddressSensor, "network", {20482: 0xA8C0, 20483: 0x1858})
        assert sensor_obj.native_value == "192.168.88.24"
        assert sensor_obj.native_value != "24.88.168.192"

    @pytest.mark.parametrize(
        ("low", "high", "expected"),
        [
            (0x007F, 0x0100, "127.0.0.1"),
            (0xFEA9, 0x0101, "169.254.1.1"),
            (0x0000, 0x0000, "0.0.0.0"),
        ],
    )
    def test_address_formatting_cases(self, hass, entry, low, high, expected):
        sensor_obj, _ = sensor(hass, entry, IPAddressSensor, "network", {20482: low, 20483: high})
        assert sensor_obj.native_value == expected
