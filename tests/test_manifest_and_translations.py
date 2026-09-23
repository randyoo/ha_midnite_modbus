"""Tests for manifest.json and translations/en.json.

These two files are Home Assistant's interface to the integration, and they rot in
a way no code test can see: a flow that returns a new error string shows a blank in
the UI, and a manifest key the schema does not know is silently ignored. The rules
below come from Home Assistant's own integration-manifest documentation.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

COMPONENT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "midnite_solar"
MANIFEST = json.loads((COMPONENT / "manifest.json").read_text())
STRINGS = json.loads((COMPONENT / "translations" / "en.json").read_text())
FLOW_SOURCE = (COMPONENT / "config_flow.py").read_text()

# From Home Assistant's manifest documentation.
REQUIRED_KEYS = {
    "domain",
    "name",
    "codeowners",
    "documentation",
    "requirements",
    "iot_class",
    "version",
}
ALLOWED_KEYS = {
    "after_dependencies",
    "domain",
    "bluetooth",
    "codeowners",
    "config_flow",
    "dependencies",
    "dhcp",
    "documentation",
    "homekit",
    "integration_type",
    "integration_type",
    "iot_class",
    "iot_standards",
    "issue_tracker",
    "loggers",
    "mqtt",
    "name",
    "quality_scale",
    "requirements",
    "single_config_entry",
    "ssdp",
    "supported_by",
    "usb",
    "version",
    "zeroconf",
}
IOT_CLASSES = {
    "assumed_state",
    "cloud_polling",
    "cloud_push",
    "local_polling",
    "local_push",
    "calculated",
}
INTEGRATION_TYPES = {"device", "entity", "hardware", "helper", "hub", "service", "system", "virtual"}


def error_keys_the_flow_shows():
    """Every string the flow puts in errors["base"]."""
    return set(re.findall(r'errors\["base"\] = "([a-z_]+)"', FLOW_SOURCE))


def abort_reasons_the_flow_returns():
    """Every reason the flow can finish with."""
    found = set(re.findall(r'reason="([a-z_]+)"', FLOW_SOURCE))
    found |= set(re.findall(r'raise AbortFlow\("([a-z_]+)"\)', FLOW_SOURCE))
    return found


class TestManifest:
    def test_the_keys_home_assistant_requires_are_there(self):
        missing = REQUIRED_KEYS - set(MANIFEST)
        assert missing == set()

    def test_no_key_is_spelled_wrong_or_made_up(self):
        unknown = set(MANIFEST) - ALLOWED_KEYS
        assert unknown == set()

    def test_the_domain_matches_the_folder(self):
        assert MANIFEST["domain"] == COMPONENT.name

    def test_the_iot_class_is_one_home_assistant_accepts(self):
        """This integration talks Modbus TCP to the device directly."""
        assert MANIFEST["iot_class"] == "local_polling"
        assert MANIFEST["iot_class"] in IOT_CLASSES

    def test_the_integration_type_is_set(self):
        """One Classic per config entry, not a gateway to many devices."""
        assert MANIFEST["integration_type"] == "device"
        assert MANIFEST["integration_type"] in INTEGRATION_TYPES

    def test_a_config_flow_is_declared_and_exists(self):
        assert MANIFEST["config_flow"] is True
        assert (COMPONENT / "config_flow.py").exists()

    def test_pymodbus_is_a_requirement(self):
        assert any("pymodbus" in requirement for requirement in MANIFEST["requirements"])

    def test_the_loggers_are_the_libraries_that_log(self):
        assert MANIFEST["loggers"] == ["pymodbus"]

    def test_registered_devices_is_not_a_manifest_key(self):
        """It belongs inside a dhcp matcher, where it asks for IP-update discovery."""
        assert "registered_devices" not in MANIFEST
        assert {"registered_devices": True} in MANIFEST["dhcp"]

    def test_the_dhcp_matchers_are_well_formed(self):
        for matcher in MANIFEST["dhcp"]:
            assert set(matcher) <= {"hostname", "macaddress", "registered_devices", "manufacturer", "description", "vid", "pid"}

    def test_discovery_is_narrowed_to_midnite_hardware(self):
        """A bare "*" hostname would offer this integration for every device on the LAN."""
        hostname_matchers = [m for m in MANIFEST["dhcp"] if "hostname" in m]
        assert hostname_matchers, "DHCP discovery is declared in the manifest"
        for matcher in hostname_matchers:
            assert matcher.get("macaddress"), "hostname matching needs the OUI beside it"

    def test_the_documentation_url_points_somewhere(self):
        assert MANIFEST["documentation"].startswith("https://")

    def test_the_version_is_a_version(self):
        assert re.fullmatch(r"\d+\.\d+\.\d+", MANIFEST["version"])


class TestTranslations:
    def test_only_the_blocks_home_assistant_reads_are_present(self):
        assert set(STRINGS) == {"config", "options"}

    def test_every_error_the_flow_can_show_is_written_out(self):
        missing = error_keys_the_flow_shows() - set(STRINGS["config"]["error"])
        assert missing == set()

    def test_the_missing_host_error_has_text(self):
        assert STRINGS["config"]["error"]["missing_host"]

    def test_every_abort_reason_the_flow_can_return_is_written_out(self):
        missing = abort_reasons_the_flow_returns() - set(STRINGS["config"]["abort"])
        assert missing == set(), "an abort without a string shows as a blank card"

    def test_the_already_configured_abort_is_there(self):
        assert "already_configured" in STRINGS["config"]["abort"]

    def test_the_reconfigure_abort_is_written_out(self):
        assert STRINGS["config"]["abort"]["reconfigure_success"]

    def test_the_user_step_labels_every_field_it_asks_for(self):
        fields = set(STRINGS["config"]["step"]["user"]["data"])
        assert {"host", "port", "scan_interval"} <= fields

    def test_the_options_flow_step_is_the_one_the_code_uses(self):
        """async_step_init is the step Home Assistant will show; every field
        its schema asks for - both cadences, the bridge toggle, and the write
        PIN - carries a label, so nothing renders as a bare key."""
        assert "init" in STRINGS["options"]["step"]
        assert {
            "scan_interval",
            "sensor_interval",
            "bridge_enabled",
            "write_pin",
        } == set(STRINGS["options"]["step"]["init"]["data"])

    def test_the_discovered_description_has_the_placeholders_the_flow_passes(self):
        description = STRINGS["config"]["step"]["user"]["description_discovered"]
        assert "{{ ip }}" in description and "{{ mac }}" in description

    def test_no_dead_entity_name_blocks(self):
        """Entity names come from the code; a translations block for them is never read."""
        assert "entity" not in STRINGS
        assert "select" not in STRINGS

    def test_no_translation_is_empty(self):
        def walk(node, path):
            if isinstance(node, dict):
                for key, value in node.items():
                    walk(value, f"{path}.{key}")
            else:
                assert isinstance(node, str) and node.strip(), f"{path} is empty"

        walk(STRINGS, "translations")


class TestNothingStaleInTheStrings:
    """A string nobody can reach is a string nobody maintains."""

    @pytest.mark.parametrize("step", ["user"])
    def test_the_config_steps_the_flow_implements(self, step):
        assert f"async_step_{step}" in FLOW_SOURCE

    def test_the_options_step_id_matches_the_handler(self):
        from midnite_solar import config_flow

        assert 'step_id="init"' in pathlib.Path(config_flow.__file__).read_text()
