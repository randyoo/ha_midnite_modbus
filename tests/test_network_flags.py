"""Tests for the two Network Settings Flags in Table 20481-1.

From the register map:

  20481 | IP Settings | [20481] | Network Settings Flags. See Table 20481-1
  Table 20481-1: "DHCP | 0x0001 | Set this bit to enable DHCP."
                 "Web Access | 0x0002 | Set this bit to enable online access to
                  your Classic through http://www.mymidnite.com"
  "† Read Only if the DHCP flag is set. To assign a static IP to the Classic,
   first clear the DHCP flag in the IP Settings Register (20481)."
"""

import pytest
from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.helpers.entity import EntityCategory

from midnite_solar.binary_sensor import NETWORK_FLAG_ENTITIES, NetworkFlagBinarySensor
from midnite_solar.const import (
    NETWORK_FLAGS,
    REGISTER_GROUPS,
    REGISTER_MAP,
)
from midnite_solar.coordinator import register_blocks


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def flag_sensor(entry, flag, value=None):
    group = {} if value is None else {REGISTER_MAP["IP_SETTINGS_FLAGS"]: value}
    coordinator = FakeCoordinator(Hass(), FakeApi(), {"network": group})
    return NetworkFlagBinarySensor(coordinator, entry, flag)


class TestTable:
    def test_the_flags_are_the_maps_bit_values(self):
        assert NETWORK_FLAGS == {"DHCP": 0x0001, "WebAccess": 0x0002}

    def test_the_register_is_20481(self):
        assert REGISTER_MAP["IP_SETTINGS_FLAGS"] == 20481

    def test_it_is_polled_and_costs_no_extra_request(self):
        """20481 sits in front of the network block that was already being read."""
        assert REGISTER_MAP["IP_SETTINGS_FLAGS"] in REGISTER_GROUPS["network"]
        assert register_blocks(REGISTER_GROUPS["network"]) == [(20481, 20491)]

    def test_both_flags_have_entities(self):
        assert set(NETWORK_FLAG_ENTITIES) == set(NETWORK_FLAGS)


class TestDHCPFlag:
    def test_set_when_the_bit_is_set(self, entry):
        assert flag_sensor(entry, "DHCP", 0x0001).is_on is True

    def test_clear_when_only_web_access_is_set(self, entry):
        assert flag_sensor(entry, "DHCP", 0x0002).is_on is False

    def test_both_flags_are_read_independently(self, entry):
        coordinator = FakeCoordinator(
            Hass(), FakeApi(), {"network": {REGISTER_MAP["IP_SETTINGS_FLAGS"]: 0x0003}}
        )
        dhcp = NetworkFlagBinarySensor(coordinator, entry, "DHCP")
        web = NetworkFlagBinarySensor(coordinator, entry, "WebAccess")
        assert dhcp.is_on is True
        assert web.is_on is True

    def test_it_is_on_by_default_because_it_explains_the_other_registers(self, entry):
        entity = flag_sensor(entry, "DHCP", 0)
        assert entity.entity_registry_enabled_default is True
        assert entity.name == "DHCP Enabled"
        assert entity.unique_id == "entry-1_network_flag_dhcp"

    def test_no_reading_is_unknown(self, entry):
        assert flag_sensor(entry, "DHCP").is_on is None

    def test_the_raw_register_travels_with_it(self, entry):
        assert flag_sensor(entry, "DHCP", 0x0003).extra_state_attributes == {"ip_settings": 3}


class TestWebAccessFlag:
    def test_set_when_the_bit_is_set(self, entry):
        assert flag_sensor(entry, "WebAccess", 0x0002).is_on is True

    def test_clear_when_only_dhcp_is_set(self, entry):
        assert flag_sensor(entry, "WebAccess", 0x0001).is_on is False

    def test_it_is_off_by_default(self, entry):
        entity = flag_sensor(entry, "WebAccess", 0)
        assert entity.entity_registry_enabled_default is False
        assert entity.entity_category == EntityCategory.DIAGNOSTIC
        assert entity.unique_id == "entry-1_network_flag_webaccess"

    def test_no_reading_is_unknown(self, entry):
        assert flag_sensor(entry, "WebAccess").is_on is None


class TestFlagsAreNotInfoFlags:
    """Register 20481 is a different table from 4130/4131; keep them apart."""

    def test_the_two_tables_are_kept_apart(self):
        """20481 is Table 20481-1; 4130/4131 are Table 4130-1. Different registers."""
        from midnite_solar.const import INFO_FLAGS

        assert REGISTER_MAP["IP_SETTINGS_FLAGS"] not in (
            REGISTER_MAP["INFO_FLAGS_LOW"],
            REGISTER_MAP["INFO_FLAGS_HIGH"],
        )
        assert len(INFO_FLAGS) == 25

    def test_the_device_info_comes_from_the_one_place(self, entry):
        from midnite_solar.base import MidniteBaseEntityDescription
        from midnite_solar.const import DOMAIN

        entity = flag_sensor(entry, "DHCP", 1)
        assert entity.device_info == MidniteBaseEntityDescription.get_device_info(
            entity.coordinator, entry, DOMAIN
        )
