"""The bridge engine: the snapshot, the write path, and the mDNS record.

The bridge exists because the Classic's Ethernet port serves ONE Modbus client and this
integration is that client: everything else - the future desktop app first
of all - gets in through these functions instead of the socket. So the
contract pinned here is the API's contract: the snapshot shape, the same
write/verify/EEPROM-commit path the entities use, the registers no client
may ever write, and what the LAN advertisement must contain for a desktop
app to find the bridge unaided.

No socket, per the suite's one hard rule: zeroconf is the recording double
in tests/_ha_stub, and the route probe is monkeypatched like every other
blocking call.
"""

from __future__ import annotations

import asyncio
import datetime
import socket

import pytest
import zeroconf
from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import Hass
from homeassistant.exceptions import HomeAssistantError

from midnite_solar import bridge as bridge_module
from midnite_solar.bridge import (
    BridgeAdvertiser,
    async_bridge_clock,
    async_bridge_reboot,
    async_bridge_write,
    async_start_bridge,
    async_stop_bridge,
    build_snapshot,
    check_write_pin,
    ensure_bridge_views,
    resolve_register,
)
from midnite_solar.const import (
    BRIDGE_API_VERSION,
    BRIDGE_ADS_KEY,
    BRIDGE_MDNS_TYPE,
    CLOCK_FILE_ADDRESS,
    CLOCK_FILE_DEVICE,
    DEFAULT_WRITE_PIN,
    DOMAIN,
    FORCE_FLAGS,
    PIN_LOCKOUT_STEPS,
    REGISTER_MAP,
)
from midnite_solar.text import registers_for_name

ENTRY_ID = "entry-1"
CLASSIC_HOST = "192.168.88.24"

# 2026-09-21 14:30:05 (a Monday), the same worked example PROTOCOL.md uses.
NOW = datetime.datetime(2026, 9, 21, 14, 30, 5)


def identity_groups():
    """The polled groups a named CLASSIC7 with a known clock reports."""
    name = registers_for_name("CLASSIC7")
    return {
        "device_info": {
            REGISTER_MAP["UNIT_ID"]: 250,
            REGISTER_MAP["UNIT_NAME_0"]: name[0],
            REGISTER_MAP["UNIT_NAME_1"]: name[1],
            REGISTER_MAP["UNIT_NAME_2"]: name[2],
            REGISTER_MAP["UNIT_NAME_3"]: name[3],
            REGISTER_MAP["MAC_ADDRESS_PART_1"]: 0xCCDD,
            REGISTER_MAP["MAC_ADDRESS_PART_2"]: 0x0F00,
            REGISTER_MAP["MAC_ADDRESS_PART_3"]: 0x601D,
        },
        "serial": {
            REGISTER_MAP["SERIAL_NUMBER_MSB_RO"]: 0,
            REGISTER_MAP["SERIAL_NUMBER_LSB_RO"]: 49880,
        },
        "clock": {
            REGISTER_MAP["CTIME_SECONDS_MINUTES"]: 5 | (30 << 8),
            REGISTER_MAP["CTIME_HOURS_WEEKDAY"]: 14,
            REGISTER_MAP["CTIME_DAY_MONTH"]: 21 | (9 << 8),
            REGISTER_MAP["CTIME_YEAR"]: 2026,
        },
        "firmware": {
            REGISTER_MAP["APP_VERSION"]: (1 << 12) | (7 << 8) | (5 << 4),
            REGISTER_MAP["NET_VERSION"]: (1 << 12) | (6 << 8) | (3 << 4),
            REGISTER_MAP["APP_REV_LOW"]: 1758,
            REGISTER_MAP["APP_REV_HIGH"]: 0,
            REGISTER_MAP["NET_REV_LOW"]: 2041,
            REGISTER_MAP["NET_REV_HIGH"]: 0,
        },
        "setpoints": {REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"]: 576},
    }


def a_classic(auto_save_eeprom=False):
    hass = Hass()
    coordinator = FakeCoordinator(
        hass, FakeApi(), identity_groups(), auto_save_eeprom=auto_save_eeprom
    )
    return hass, coordinator


def an_entry():
    return ConfigEntry(
        entry_id=ENTRY_ID,
        title="Classic 250",
        data={CONF_HOST: CLASSIC_HOST},
    )


@pytest.fixture(autouse=True)
def clear_zeroconf_double():
    """The recording zeroconf never leaks instances between tests."""
    zeroconf.Zeroconf.instances = []
    yield
    zeroconf.Zeroconf.instances = []


class TestSnapshot:
    def snapshot(self):
        _hass, coordinator = a_classic()
        return build_snapshot(coordinator)

    def test_the_contract_version_and_the_name_table_travel_with_every_answer(self):
        answer = self.snapshot()
        assert answer["api_version"] == BRIDGE_API_VERSION
        assert answer["names"]["ABSORB_SETPOINT_VOLTAGE"] == 4149

    def test_groups_answer_with_string_keys_and_raw_values(self):
        answer = self.snapshot()
        assert answer["online"] is True
        assert answer["groups"]["setpoints"]["4149"] == 576

    def test_the_identity_is_the_classics_own_not_the_entries(self):
        identity = self.snapshot()["identity"]
        assert identity["name"] == "CLASSIC7"
        assert identity["mac"] == "60:1d:0f:00:cc:dd"
        assert identity["model"] == "Classic 250"
        assert identity["serial"] == "49880"

    def test_the_clock_and_firmware_arrive_decoded(self):
        answer = self.snapshot()
        assert answer["clock"] == "2026-09-21T14:30:05"
        assert answer["firmware"]["app_version"] == "1.7.5"
        assert answer["firmware"]["net_version"] == "1.6.3"
        assert answer["firmware"]["app_rev"] == 1758
        assert answer["firmware"]["net_rev"] == 2041

    def test_an_never_refreshed_coordinator_is_offline_not_wrong(self):
        hass = Hass()
        coordinator = FakeCoordinator(hass, FakeApi(), {})
        answer = build_snapshot(coordinator)
        assert answer["online"] is False
        assert answer["clock"] is None
        assert answer["groups"] == {}

    def test_the_client_can_see_the_commit_policy(self):
        """The EEPROM commit is opt-in; the snapshot says which mode."""
        assert build_snapshot(a_classic()[1])["auto_save_eeprom"] is False
        assert build_snapshot(a_classic(auto_save_eeprom=True)[1])["auto_save_eeprom"] is True

    def test_the_wire_stamp_says_when_the_classic_was_last_polled(self):
        """A client's own fetch time says nothing about the data's age; the
        coordinator's successful-poll stamp is the honest answer."""
        _hass, coordinator = a_classic()
        coordinator.last_polled = datetime.datetime(
            2026, 9, 22, 12, 0, 0, tzinfo=datetime.timezone.utc
        )
        assert build_snapshot(coordinator)["last_polled"] == "2026-09-22T12:00:00+00:00"

    def test_a_never_polled_bridge_stamps_nothing(self):
        _hass, coordinator = a_classic()
        coordinator.last_polled = None
        assert build_snapshot(coordinator)["last_polled"] is None


class TestResolve:
    def test_names_and_numbers_both_land_on_the_register(self):
        assert resolve_register("ABSORB_SETPOINT_VOLTAGE") == 4149
        assert resolve_register("absorb_setpoint_voltage") == 4149
        assert resolve_register("4149") == 4149
        assert resolve_register(4149) == 4149

    def test_the_unlock_registers_are_not_writable_by_anyone_but_the_hub(self):
        for forbidden in (
            REGISTER_MAP["UNLOCK_SERIAL_MSB"],
            REGISTER_MAP["UNLOCK_SERIAL_LSB"],
        ):
            with pytest.raises(HomeAssistantError):
                resolve_register(forbidden)

    def test_the_app_untouchables_are_not_writable(self):
        for address in (4188, 4195, 4201, 4300, 4394, 4399):
            with pytest.raises(HomeAssistantError):
                resolve_register(address)

    def test_the_network_block_is_not_a_casual_lan_target(self):
        """A write there moves the address the Classic answers on."""
        for address in (20481, 20482, 20491):
            with pytest.raises(HomeAssistantError):
                resolve_register(address)

    def test_ranges_that_cannot_be_addresses_are_refused(self):
        for bad in (0, -1, 65536):
            with pytest.raises(HomeAssistantError):
                resolve_register(bad)

    def test_there_is_no_register_named_maybe(self):
        with pytest.raises(HomeAssistantError):
            resolve_register("ABSORB_VOLTS_MAYBE")

    def test_a_bool_is_not_a_number_here(self):
        # True would otherwise be register 1.
        with pytest.raises(HomeAssistantError):
            resolve_register(True)


class TestBridgeWrite:
    def write(self, target, value, commit=False, auto_save=False, **api_kwargs):
        hass = Hass()
        api = FakeApi(**api_kwargs)
        coordinator = FakeCoordinator(hass, api, {}, auto_save_eeprom=auto_save)
        return asyncio.run(
            async_bridge_write(hass, coordinator, target, value, commit)
        ), api

    def test_a_write_lands_and_the_reply_names_the_register(self):
        answer, api = self.write("ABSORB_SETPOINT_VOLTAGE", 576)
        assert answer == {
            "register": 4149,
            "name": "ABSORB_SETPOINT_VOLTAGE",
            "value": 576,
            "committed": False,
        }
        assert (4149, 576) in api.writes

    def test_the_commit_is_still_the_opt_in_one(self):
        answer, api = self.write(4149, 576)
        assert answer["committed"] is False
        assert (REGISTER_MAP["FORCE_FLAG_BITS"], 1 << FORCE_FLAGS["ForceEEpromUpdate"]) not in api.writes

    def test_an_explicit_commit_commits_once_without_the_switch(self):
        answer, api = self.write(4149, 576, commit=True)
        assert answer["committed"] is True
        assert api.writes[-1] == (
            REGISTER_MAP["FORCE_FLAG_BITS"],
            1 << FORCE_FLAGS["ForceEEpromUpdate"],
        )

    def test_the_switch_on_commits_without_being_asked(self):
        answer, _api = self.write(4149, 576, auto_save=True)
        assert answer["committed"] is True

    def test_a_write_protected_classic_is_reported_not_silently_accepted(self):
        """Same read-back check the number entities raise with."""
        api_with_old_value = FakeApi(read_values={4149: 500}, stale_read=True)
        hass = Hass()
        coordinator = FakeCoordinator(hass, api_with_old_value, {})
        with pytest.raises(HomeAssistantError):
            asyncio.run(async_bridge_write(hass, coordinator, 4149, 576))

    def test_values_that_do_not_fit_a_register_are_refused(self):
        for bad in (65536, -1, 57.6, True, "576"):
            with pytest.raises(HomeAssistantError):
                self.write(4149, bad)

    def test_a_forbidden_write_never_reaches_the_wire(self):
        hass = Hass()
        api = FakeApi()
        coordinator = FakeCoordinator(hass, api, {})
        with pytest.raises(HomeAssistantError):
            asyncio.run(async_bridge_write(hass, coordinator, 20492, 49880))
        assert api.writes == []


class TestBridgeClockAndReboot:
    def test_the_clock_goes_to_the_private_file_the_app_used(self):
        answer, (hass, coordinator) = self.run(NOW)
        assert answer == {"clock": NOW.isoformat()}
        device, payload, address = coordinator.api.internal_writes[0]
        assert (device, address) == (CLOCK_FILE_DEVICE, CLOCK_FILE_ADDRESS)
        assert payload[9] == 14 and payload[10] == 30 and payload[11] == 0
        assert payload[12] == (2026 >> 8) & 0xFF and payload[13] == 2026 & 0xFF

    def run(self, when):
        hass, coordinator = a_classic()
        answer = asyncio.run(async_bridge_clock(hass, coordinator, when))
        return answer, (hass, coordinator)

    def test_the_reboot_is_the_two_written_sequence(self):
        hass, coordinator = a_classic()
        answer = asyncio.run(async_bridge_reboot(hass, coordinator))
        assert answer["reboot"] == "sent"
        assert coordinator.api.writes == [
            (REGISTER_MAP["ENABLE_FLAGS_2"], 0x04),
            (REGISTER_MAP["FORCE_FLAG_BITS"], 1 << FORCE_FLAGS["ForceNite"]),
        ]


class TestAdvertisement:
    def advertiser(self, hass=None, coordinator=None):
        hass = hass or Hass()
        coordinator = coordinator or FakeCoordinator(
            hass, FakeApi(), identity_groups()
        )
        return BridgeAdvertiser(hass, an_entry(), coordinator), hass

    def test_the_record_says_who_and_where_without_being_told_anything(self):
        advertiser, _hass = self.advertiser()
        advertiser.publish()
        instance = zeroconf.Zeroconf.instances[0]
        info = instance.registered[0]
        assert info.type == BRIDGE_MDNS_TYPE
        assert info.name.startswith(
            "Midnite Bridge CLASSIC7 (60:1d:0f:00:cc:dd)"
        )
        assert info.name.endswith(BRIDGE_MDNS_TYPE)
        # The stub network answers with the canned HA URL; the record must
        # carry its host and port, not the Classic's.
        assert info.addresses == [socket.inet_aton("192.168.50.5")]
        assert info.port == 8123
        assert info.properties[b"api"] == str(BRIDGE_API_VERSION).encode()
        assert info.properties[b"entry"] == ENTRY_ID.encode()
        assert info.properties[b"classic"] == CLASSIC_HOST.encode()

    def test_the_a_record_name_is_this_bridges_own_not_a_shared_one(self):
        """A shared server name would resolve a second bridge's clients to
        the wrong machine; the MAC makes the name unique per Classic."""
        advertiser, _hass = self.advertiser()
        advertiser.publish()
        info = zeroconf.Zeroconf.instances[0].registered[0]
        assert info.server == "midnite-bridge-60-1d-0f-00-cc-dd.local."

    def test_a_nameless_classic_gets_an_entry_id_shaped_server(self):
        hass = Hass()
        coordinator = FakeCoordinator(hass, FakeApi(), {})
        advertiser, _hass = self.advertiser(hass=hass, coordinator=coordinator)
        advertiser.publish()
        assert zeroconf.Zeroconf.instances[0].registered[0].server == (
            f"midnite-bridge-{ENTRY_ID}.local."
        )

    def test_the_stub_url_loses_its_port_to_the_record(self):
        hass = Hass()
        hass.data["network_stub_url"] = "http://10.9.8.7:8444"
        advertiser, _hass = self.advertiser(hass=hass)
        advertiser.publish()
        assert zeroconf.Zeroconf.instances[0].registered[0].port == 8444

    def test_a_nameless_classic_is_advertised_by_its_entry_id(self):
        hass = Hass()
        coordinator = FakeCoordinator(hass, FakeApi(), {})
        advertiser, _hass = self.advertiser(hass=hass, coordinator=coordinator)
        advertiser.publish()
        info = zeroconf.Zeroconf.instances[0].registered[0]
        assert ENTRY_ID in info.name

    def test_publishing_twice_advertises_once(self):
        advertiser, _hass = self.advertiser()
        advertiser.publish()
        advertiser.publish()
        assert len(zeroconf.Zeroconf.instances) == 1

    def test_close_withdraws_the_record_and_releases_the_socket(self):
        advertiser, _hass = self.advertiser()
        advertiser.publish()
        instance = zeroconf.Zeroconf.instances[0]
        advertiser.close()
        assert len(instance.unregistered) == 1
        assert instance.closed is True
        advertiser.close()  # safe twice
        assert len(instance.unregistered) == 1

    def test_the_route_probe_fallback_runs_no_probe_here(self, monkeypatch):
        """No URL known (fresh HAOS default): probe for the route instead."""

        def no_url(hass, **kwargs):
            raise bridge_module.NoURLAvailableError("nothing configured")

        monkeypatch.setattr(bridge_module, "get_url", no_url)
        monkeypatch.setattr(
            BridgeAdvertiser,
            "_local_ip",
            staticmethod(lambda: "10.0.0.9"),
        )
        advertiser, _hass = self.advertiser()
        advertiser.publish()
        info = zeroconf.Zeroconf.instances[0].registered[0]
        assert info.addresses == [socket.inet_aton("10.0.0.9")]
        assert info.port == 8123  # the documented default when unknown


class TestStartStop:
    def test_the_views_are_registered_once_per_home_assistant(self):
        hass = Hass()
        assert ensure_bridge_views(hass) is True
        assert len(hass.http.views) == 8  # +state +pin +write +clock +reboot +save +datalogger +refresh
        assert ensure_bridge_views(hass) is False
        assert len(hass.http.views) == 8

    def test_start_advertises_and_remembers_the_bridge_for_the_entry(self):
        hass, coordinator = a_classic()
        asyncio.run(async_start_bridge(hass, an_entry(), coordinator))
        assert hass.data[BRIDGE_ADS_KEY][ENTRY_ID] is not None
        assert coordinator.datalogger is not None
        assert len(zeroconf.Zeroconf.instances[0].registered) == 1

    def test_the_bridge_collects_its_own_datalogger_cache(self):
        """Views open means the cache fills itself: a background collector
        rides the entry's bridge. It parks on its warm-up sleep (no reads
        yet - the startup polls own the wire first), and the stop cancels
        it instead of leaking a task onto the loop. Start and stop share
        ONE asyncio.run: a task born in a finished loop is cancelled by
        that loop's teardown, which would say nothing about the stop."""
        hass, coordinator = a_classic()
        # async_stop_bridge finds the coordinator the way Home Assistant
        # stores it - the same seat installed() gives the API tests.
        hass.data.setdefault(DOMAIN, {})[ENTRY_ID] = coordinator

        async def start_then_stop():
            await async_start_bridge(hass, an_entry(), coordinator)
            sweeper = coordinator.logger_sweeper
            assert isinstance(sweeper, asyncio.Task)
            await asyncio.sleep(0)  # the collector takes its first beat
            assert not sweeper.done(), "it must park on the warm-up, not run"
            assert coordinator.api.internal_reads == [], "warm-up put reads on the wire"
            await async_stop_bridge(hass, an_entry())
            return sweeper

        sweeper = asyncio.run(start_then_stop())
        assert sweeper.cancelled()
        assert coordinator.logger_sweeper is None

    def test_a_lan_without_mdns_still_gets_the_api(self, monkeypatch):
        def no_route(self):
            raise OSError("network unreachable")

        monkeypatch.setattr(BridgeAdvertiser, "_advertised_endpoint", no_route)
        hass, coordinator = a_classic()
        asyncio.run(async_start_bridge(hass, an_entry(), coordinator))
        # No advertisement, but the entry's bridge is still stored (so the
        # teardown below has something to undo) and views are up.
        assert hass.data[BRIDGE_ADS_KEY][ENTRY_ID] is not None
        assert len(hass.http.views) == 8

    def test_stop_withdraws_and_is_safe_a_second_time(self):
        hass, coordinator = a_classic()
        entry = an_entry()
        asyncio.run(async_start_bridge(hass, entry, coordinator))
        instance = zeroconf.Zeroconf.instances[0]
        assert asyncio.run(async_stop_bridge(hass, entry)) is True
        assert instance.closed is True
        assert asyncio.run(async_stop_bridge(hass, entry)) is False


class TestWritePinGate:
    """The gate, on the ENGINE: a wrong (or missing) PIN buys an exponentially
    longer wait during which the bridge compares NOTHING, so a guesser earns
    one comparison per rung. `now` is passed in so the ladder is pinned without
    a single real second elapsing (per the suite's no-sleeping rule)."""

    def entry(self, pin="135790"):
        _hass, coordinator = a_classic()
        coordinator.write_pin = pin
        return coordinator

    def test_an_unconfigured_placeholder_entry_refuses_every_write(self):
        # No usable default, on the ENGINE: a fresh entry still carrying the
        # all-zeros placeholder refuses ANY write 403 - even the placeholder
        # itself as a "guess" - because the open bridge would otherwise be
        # writable by anyone who knew the well-known default.
        _hass, untouched = a_classic()  # no options written yet
        assert check_write_pin(untouched, DEFAULT_WRITE_PIN)[0] == 403
        assert check_write_pin(untouched, "135790")[0] == 403

    def test_the_right_pin_lands_silently(self):
        assert check_write_pin(self.entry(), "135790") is None

    def test_a_wrong_pin_is_401_and_starts_the_first_rung(self):
        refused = check_write_pin(self.entry(), "00000", now=1000.0)
        assert refused[0] == 401
        assert refused[1]["retry_after"] == PIN_LOCKOUT_STEPS[0]

    def test_no_pin_at_all_is_a_guess_not_a_free_pass(self):
        # A caller that omits the header is refused AND counted, so it cannot
        # probe "does this bridge skip the PIN" for free.
        assert check_write_pin(self.entry(), None, now=1000.0)[0] == 401

    def test_the_refusal_never_repeats_the_pin(self):
        # The configured PIN is 246810; a wrong guess must not leak it back.
        refused = check_write_pin(self.entry("246810"), "135790", now=1000.0)
        assert refused[0] == 401
        assert "246810" not in str(refused)

    def test_the_wait_grows_exponentially_over_consecutive_misses(self):
        coordinator = self.entry()
        clock = 1000.0
        for rung, wait in enumerate(PIN_LOCKOUT_STEPS):
            refused = check_write_pin(coordinator, "x", now=clock)
            assert refused[0] == 401, f"rung {rung} must be a fresh refusal"
            assert refused[1]["retry_after"] == wait
            clock += wait + 0.5  # step past this wait to earn the next rung
        # the ladder CAPS: a seventh miss still waits only the last rung
        capped = check_write_pin(coordinator, "x", now=clock)
        assert capped[1]["retry_after"] == PIN_LOCKOUT_STEPS[-1]

    def test_a_miss_during_a_wait_is_deferred_and_does_not_re_extend(self):
        coordinator = self.entry()
        assert check_write_pin(coordinator, "x", now=5000.0)[0] == 401
        # A retry-storm mid-wait is refused 429 and does NOT push the timer
        # back, so guessing can never make the lockout outlast its own rung.
        deferred = check_write_pin(coordinator, "x", now=5000.0 + PIN_LOCKOUT_STEPS[0] - 1)
        assert deferred[0] == 429
        assert deferred[1]["retry_after"] > 0
        # the NEXT miss, once the wait has run, advances exactly one rung
        next_rung = check_write_pin(coordinator, "x", now=5000.0 + PIN_LOCKOUT_STEPS[0] + 0.5)
        assert next_rung[1]["retry_after"] == PIN_LOCKOUT_STEPS[1]

    def test_the_bridge_does_not_compare_during_the_wait(self):
        # THE anti-oracle regression, and the property the lenient build got
        # wrong: mid-wait a RIGHT candidate and a WRONG one must be
        # indistinguishable, or a spammer just reads the one oddball answer as
        # the PIN. Same status, same retry_after, whatever the guess.
        coordinator = self.entry()
        assert check_write_pin(coordinator, "x", now=9000.0)[0] == 401  # start a wait
        wrong = check_write_pin(coordinator, "00000", now=9000.0 + 1)
        right = check_write_pin(coordinator, "135790", now=9000.0 + 1)
        assert wrong[0] == right[0] == 429, "the right PIN must NOT leak through mid-wait"
        assert wrong[1]["retry_after"] == right[1]["retry_after"]

    def test_the_right_pin_waits_out_the_lockout_then_clears_the_ladder(self):
        # The strict Apple trade-off: after a typo the owner's own right PIN is
        # refused until the wait runs - then it lands, and the next wrong guess
        # restarts at rung 0 (the run was cleared, not carried).
        coordinator = self.entry()
        base = 9000.0
        assert check_write_pin(coordinator, "x", now=base)[0] == 401
        assert check_write_pin(coordinator, "135790", now=base + 0.5)[0] == 429  # mid-wait: refused
        assert (
            check_write_pin(coordinator, "135790", now=base + PIN_LOCKOUT_STEPS[0] + 0.5) is None
        )  # after the wait: lands
        reset = check_write_pin(coordinator, "x", now=base + PIN_LOCKOUT_STEPS[0] + 1.0)
        assert reset[1]["retry_after"] == PIN_LOCKOUT_STEPS[0]

    def test_the_lockout_is_held_on_the_coordinator_across_calls(self):
        # One gate per entry: the SECOND call sees the first call's miss.
        coordinator = self.entry()
        assert check_write_pin(coordinator, "x", now=20000.0)[0] == 401
        assert check_write_pin(coordinator, "x", now=20000.5)[0] == 429
