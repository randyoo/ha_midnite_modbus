"""The test double must not be blinder than the code it stands in for.

Two behaviours of the fakes are load-bearing for other suites, so they are pinned
here directly rather than only implied by the tests that happen to use them:

* `FakeCoordinator.get_register_value` has to enforce group membership the way the
  real coordinator does, or a value parked in the wrong group reads back and a
  latent "entity reads a register its group never polled" bug goes unseen.
* `ConfigEntry` has to model `async_on_unload`, so the update-listener accumulation
  test in test_setup_lifecycle.py means what it claims.
* `FakeApi.late_values` has to answer a single-register read with something other
  than what was written and nothing else, so the wind tables' neighbour-aware
  read-back is testing the Classic, not the fake.
* `ConfigFlow.async_set_unique_id` has to return the entry that already holds the
  id (as core does), or "add this Classic twice" cannot be tested at all.
"""

from __future__ import annotations

import asyncio

import pytest

from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass

from midnite_solar.const import REGISTER_GROUPS, REGISTER_MAP


def group_that_polls(address):
    return next(name for name, regs in REGISTER_GROUPS.items() if address in regs)


class TestGetRegisterValueIsGroupAware:
    def test_a_register_reads_back_from_the_group_that_polls_it(self):
        address = REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"]  # 4149
        group = group_that_polls(address)
        coordinator = FakeCoordinator(Hass(), FakeApi(), {group: {address: 576}})
        assert coordinator.get_register_value(address) == 576

    def test_a_value_in_the_wrong_group_is_not_returned(self):
        """The whole point: a register only answers from its own polling group."""
        address = REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"]
        real_group = group_that_polls(address)
        wrong_group = next(
            name for name in REGISTER_GROUPS if name != real_group and name != "serial"
        )
        coordinator = FakeCoordinator(Hass(), FakeApi(), {wrong_group: {address: 576}})
        assert coordinator.get_register_value(address) is None

    def test_an_unpolled_register_returns_nothing(self):
        coordinator = FakeCoordinator(Hass(), FakeApi(), {"status": {9999: 1}})
        assert coordinator.get_register_value(9999) is None


class TestLateValues:
    def test_a_late_value_answers_where_a_write_landed(self):
        api = FakeApi()
        api.write_register(4301, 0x4446)
        api.late_values[4301] = 0x4846
        assert api.read_holding_registers(4301, 1).registers == [0x4846]

    def test_nothing_else_is_affected(self):
        api = FakeApi()
        api.late_values[4301] = 0x4846
        assert api.read_holding_registers(4302, 1).registers == [0]


class TestUniqueReturn:
    def test_the_flow_sees_the_entry_that_already_has_the_id(self):
        from homeassistant.config_entries import ConfigFlow

        flow = ConfigFlow()
        already = ConfigEntry(entry_id="e")
        already.unique_id = "60:1d:0f:00:cc:dd"
        flow._entries = [already]
        found = asyncio.run(flow.async_set_unique_id("60:1d:0f:00:cc:dd"))
        assert found is already

    def test_an_unclaimed_id_returns_nothing(self):
        from homeassistant.config_entries import ConfigFlow

        flow = ConfigFlow()
        flow._entries = []
        assert asyncio.run(flow.async_set_unique_id("ab:cd")) is None


class TestConfigEntryUnloadModel:
    def test_on_unload_runs_and_clears_the_queued_callbacks(self):
        entry = ConfigEntry(entry_id="e")
        ran = []
        entry.async_on_unload(lambda: ran.append(1))
        entry.async_test_unload()
        assert ran == [1]
        # A second unload runs nothing: the queue was drained, as HA's is.
        entry.async_test_unload()
        assert ran == [1]


class TestBridgeDoubles:
    """The bridge's doubles are held to real behaviour too: an easier fake
    than aiohttp/zeroconf would test the double, not the bridge."""

    def test_view_responses_serialise_eagerly_like_a_real_response(self):
        """aiohttp builds its body at self.json time; a body it could not
        send must fail in the test the way it fails on the wire."""
        from homeassistant.components.http import HomeAssistantView

        view = HomeAssistantView()
        assert view.json({"ok": True}, status_code=400).status == 400
        with pytest.raises(TypeError):
            view.json({"bad": object()})

    def test_the_view_base_answers_unauthenticated_until_told_otherwise(self):
        """Real HomeAssistantView.requires_auth defaults False - so the
        bridge's own True (pinned in test_bridge_api.py) has to SET it."""
        from homeassistant.components.http import HomeAssistantView

        assert HomeAssistantView.requires_auth is False

    def test_the_zeroconf_double_records_exactly_the_used_surface(self):
        """BridgeAdvertiser only ever calls these four; a fifth call site
        would raise AttributeError here rather than silently pass."""
        import zeroconf

        client = zeroconf.Zeroconf()
        info = zeroconf.ServiceInfo("_t._tcp.local.", "n._t._tcp.local.")
        client.register_service(info)
        client.unregister_service(info)
        client.close()
        assert client.registered == [info]
        assert client.unregistered == [info]
        assert client.closed is True

    def test_a_bad_request_body_raises_like_json_parsing_does(self):
        from fakes import FakeRequest

        request = FakeRequest(None, FakeRequest.BAD)
        with pytest.raises(ValueError):
            asyncio.run(request.json())

    def test_internal_reads_record_the_retries_they_were_given(self):
        """The sweep's bounded retry budget is a contract; a fake that
        dropped the number could not show the sweep exceeding it."""
        from fakes import RecordingInternalApi

        api = RecordingInternalApi(payload=b"\x01" * 64)
        result = api.read_internal(5, 64, 3 << 10, 2)
        assert api.internal_reads == [(5, 64, 3 << 10, 2)]
        assert len(result.payload) == 64
