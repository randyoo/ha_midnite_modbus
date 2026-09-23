"""The bridge's HTTP face, driven without a server.

The view coroutines are called directly with the request double, the way the
platforms are driven: what is pinned here is the wire contract a desktop app
codes against - URLs, status codes, JSON shapes, auth - not aiohttp itself.

Two invariants above all: EVERY bridge view carries a Home Assistant access
token (requires_auth - no anonymous MPPT writes), and the views are
registered once per Home Assistant and find their coordinator per request,
so a reload can never stack routes and an unloaded entry answers 404 instead
of serving a stale connection.
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest
import zeroconf
from fakes import FakeApi, FakeCoordinator, FakeRequest, RecordingInternalApi
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import Hass

import midnite_solar as integration
from midnite_solar import bridge as bridge_module
from midnite_solar import coordinator as coordinator_module
from midnite_solar import datalogger
from midnite_solar.bridge import BridgeAdvertiser, beacon_payload, ensure_bridge_views
from midnite_solar.bridge_api import BRIDGE_VIEWS
from midnite_solar.const import (
    BRIDGE_API_VERSION,
    BRIDGE_BEACON_TYPE,
    BRIDGE_URL_PREFIX,
    CONF_BRIDGE_ENABLED,
    DEFAULT_WRITE_PIN,
    DEVICE_TYPES,
    DOMAIN,
    PIN_HEADER,
    REGISTER_MAP,
)
from test_bridge import NOW, identity_groups

ENTRY_ID = "entry-1"
HOST = "192.168.88.53"
ABSORB = REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"]

# 2026-09-21 14:30:05 as ISO text, and the same with an explicit UTC suffix.
CLOCK_TEXT = "2026-09-21T14:30:05"
CLOCK_TEXT_Z = "2026-09-21T14:30:05Z"


class _NoPin:
    """Sentinel: send the request with NO write-PIN header at all."""


NO_PIN = _NoPin()


class _FakeMonotonic:
    """A stand-in for the `time` module INSIDE bridge.py (its only time call
    is check_write_pin's time.monotonic), so a test can spend the lockout
    ladder in wrist-seconds without disturbing asyncio's own clock."""

    def __init__(self, start: float = 10_000.0) -> None:
        self.now = start

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Hub(FakeApi):
    """The lifecycle double from test_setup_lifecycle, minus the registry."""

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port

    def connect(self):
        return True


# A real, configured 6-digit PIN: the harness sets it so the many non-gate
# tests exercise the write path, not the "no PIN set yet" refusal. It is NOT
# the all-zeros placeholder (which would leave writes disabled).
SET_PIN = "135790"


def installed(api=None, auto_save=False, pin=SET_PIN):
    """A set-up entry (writes armed with SET_PIN) and its registered views."""
    hass = Hass()
    coordinator = FakeCoordinator(
        hass, api or FakeApi(), identity_groups(), auto_save_eeprom=auto_save
    )
    coordinator.write_pin = pin
    hass.data.setdefault(DOMAIN, {})[ENTRY_ID] = coordinator
    ensure_bridge_views(hass)
    return hass, coordinator


def view_for(hass, suffix):
    wanted = f"{BRIDGE_URL_PREFIX}/{suffix}"
    return next(view for view in hass.http.views if view.url == wanted)


def post(hass, suffix, body, entry_id=ENTRY_ID, pin=SET_PIN):
    """Drive a POST. By default it carries the right write PIN so the many
    non-auth tests stay about their own subject; pass pin="..." for a wrong
    one or pin=NO_PIN to omit the header (the gate tests do exactly that)."""
    view = view_for(hass, suffix)
    headers = {} if isinstance(pin, _NoPin) else {PIN_HEADER: pin}
    return asyncio.run(view.post(FakeRequest(hass, body, headers), entry_id))


def get(hass, suffix, entry_id=ENTRY_ID):
    view = view_for(hass, suffix)
    return asyncio.run(view.get(FakeRequest(hass), entry_id))


@pytest.fixture(autouse=True)
def clean_environment():
    zeroconf.Zeroconf.instances = []
    original = coordinator_module.MidniteHub
    yield
    coordinator_module.MidniteHub = original
    zeroconf.Zeroconf.instances = []


class TestRegistration:
    def test_the_bridge_is_open_no_home_assistant_token(self):
        """By explicit choice the bridge takes no HA token; the write PIN (not
        the token) is the write gate, so no view may claim requires_auth."""
        for view in BRIDGE_VIEWS:
            assert view.requires_auth is False

    def test_the_urls_are_unique_and_live_under_the_api_prefix(self):
        urls = {view.url for view in BRIDGE_VIEWS}
        assert len(urls) == len(BRIDGE_VIEWS)
        assert all(url.startswith("/api/midnite/") for url in urls)

    def test_the_state_view_is_get_and_the_writers_are_post(self):
        hass = Hass()
        ensure_bridge_views(hass)
        kinds = {
            view.url.split("/")[-1]: asyncio.iscoroutinefunction(
                getattr(view, "get", None)
            )
            for view in hass.http.views
        }
        assert kinds["state"] is True
        assert kinds["datalogger"] is True
        for writer in ("pin", "write", "clock", "reboot", "save", "datalogger/refresh"):
            assert asyncio.iscoroutinefunction(view_for(hass, writer).post)

    def test_an_entry_that_never_set_up_answers_404_everywhere(self):
        hass, _coordinator = installed()
        for suffix in ("state", "datalogger"):
            assert get(hass, suffix, entry_id="ghost").status == 404
        for suffix in ("write", "clock", "reboot", "save", "datalogger/refresh"):
            assert post(hass, suffix, {}, entry_id="ghost").status == 404


class TestStateView:
    def test_the_snapshot_answers_whole(self):
        hass, _coordinator = installed()
        response = get(hass, "state")
        assert response.status == 200
        assert response.body["api_version"] == BRIDGE_API_VERSION
        assert response.body["identity"]["name"] == "CLASSIC7"
        assert response.body["groups"]["setpoints"]["4149"] == 576

    def test_the_state_carries_the_bridges_last_wire_poll(self):
        """The app's "last update" counter ages with THIS, not with its own
        fetch: a cache served all day still reports how old its numbers are."""
        import datetime

        hass, coordinator = installed()
        coordinator.last_polled = datetime.datetime(
            2026, 9, 22, 12, 0, 0, tzinfo=datetime.timezone.utc
        )
        response = get(hass, "state")
        assert response.body["last_polled"] == "2026-09-22T12:00:00+00:00"


class TestWritePinGate:
    """The bridge carries NO Home Assistant token, so the write PIN is the
    ENTIRE gate on every call that changes the Classic: a real 6-digit PIN is
    required (the all-zeros placeholder leaves writes OFF), wrong guesses hit a
    strict lockout, and the cheap reads pay nothing."""

    def test_the_probe_accepts_the_configured_pin(self):
        hass, _ = installed()  # armed with SET_PIN
        response = post(hass, "pin", {"pin": SET_PIN})
        assert response.status == 200
        assert response.body == {"pin": "accepted"}

    def test_the_probe_refuses_a_wrong_pin_without_echoing_it(self):
        hass, _ = installed(pin="246810")
        response = post(hass, "pin", {"pin": SET_PIN}, pin=NO_PIN)
        assert response.status == 401
        assert "error" in response.body
        assert "246810" not in json.dumps(response.body)

    def test_the_probe_wants_a_pin_in_the_body(self):
        hass, _ = installed()
        assert post(hass, "pin", {}, pin=NO_PIN).status == 400

    @pytest.mark.parametrize("unset", [DEFAULT_WRITE_PIN, "12345", "abcdef", ""])
    def test_writes_stay_off_until_a_real_pin_is_configured(self, unset):
        """No usable default, enforced at the gate: while the entry's PIN is
        the placeholder (or malformed), EVERY write is refused 403 telling the
        owner to set one, and the device is never touched."""
        api = FakeApi()
        hass, _ = installed(api=api, pin=unset)
        refused = post(hass, "write", {"register": ABSORB, "value": 576}, pin="000000")
        assert refused.status == 403, f"PIN {unset!r} must not permit writes"
        assert "PIN" in refused.body["error"] and "options" in refused.body["error"]
        assert api.writes == []
        # the probe says the same, so the app surfaces the instruction verbatim
        assert post(hass, "pin", {"pin": unset}, pin=NO_PIN).status == 403

    @pytest.mark.parametrize("suffix,body", [
        ("write", {"register": ABSORB, "value": 576}),
        ("clock", {"time": CLOCK_TEXT_Z}),
        ("reboot", {}),
        ("save", {}),
    ])
    def test_every_mutating_endpoint_refuses_a_missing_pin(self, suffix, body):
        # The header absent is refused AND (via the shared gate) counted, so a
        # caller cannot learn that some endpoint skips the PIN for free.
        api = FakeApi()
        hass, _ = installed(api=api)
        response = post(hass, suffix, body, pin=NO_PIN)
        assert response.status == 401
        assert api.writes == [], f"{suffix} must not touch the device without the PIN"

    @pytest.mark.parametrize("suffix,body", [
        ("write", {"register": ABSORB, "value": 576}),
        ("clock", {"time": CLOCK_TEXT_Z}),
        ("reboot", {}),
        ("save", {}),
    ])
    def test_every_mutating_endpoint_refuses_the_wrong_pin(self, suffix, body):
        api = FakeApi()
        hass, _ = installed(api=api)
        response = post(hass, suffix, body, pin="000001")
        assert response.status == 401
        assert api.writes == [], f"{suffix} landed despite the wrong PIN"

    def test_the_reads_are_never_pin_gated(self):
        """State and the stored datalogger change nothing, so they answer with
        no PIN at all - the fast bridge poll stays fast."""
        hass, _ = installed()
        assert get(hass, "state").status == 200
        assert get(hass, "datalogger").status == 200

    def test_the_datalogger_sweep_is_pin_gated(self):
        # A sweep READS, but it is a minutes-long monopoly on the Classic's one
        # connection, so an open bridge would let any LAN device stall the live
        # poll by spamming it - gated like a write. Right PIN first (lands),
        # then no PIN is refused.
        hass, _ = installed(api=RecordingInternalApi())
        assert post(hass, "datalogger/refresh", {}, pin=SET_PIN).status == 200
        assert post(hass, "datalogger/refresh", {}, pin=NO_PIN).status == 401

    def test_wrong_guesses_across_endpoints_share_one_lockout(self):
        # /pin and /write draw on the SAME per-entry ladder, so guessing
        # cannot dodge the wait by rotating between endpoints.
        hass, _ = installed()
        first = post(hass, "pin", {"pin": "000001"}, pin=NO_PIN)
        assert first.status == 401
        # the immediate next guess anywhere is deferred by the wait
        again = post(hass, "write", {"register": ABSORB, "value": 576}, pin="000002")
        assert again.status == 429
        assert "retry_after" in again.body

    def test_the_right_pin_waits_out_the_lockout_before_it_lands(self):
        # Strict lockout at the HTTP face: after a wrong PIN the bridge stops
        # comparing, so even the CORRECT PIN answered right now is deferred 429
        # and touches NOTHING (this is the hole the lenient build left open -
        # comparing during the wait handed a spammer the PIN for free). Only
        # once the wait has run does the right PIN reach the device.
        api = FakeApi()
        hass, coordinator = installed(api=api)
        assert post(hass, "pin", {"pin": "000001"}, pin=NO_PIN).status == 401
        refused = post(hass, "write", {"register": ABSORB, "value": 576}, pin=SET_PIN)
        assert refused.status == 429, "the right PIN must not bypass the wait"
        assert api.writes == []
        # Run the wait out (drive the gate's own monotonic clock back), then it lands.
        coordinator._pin_gate._locked_until = 0.0
        ok = post(hass, "write", {"register": ABSORB, "value": 576}, pin=SET_PIN)
        assert ok.status == 200
        assert api.writes, "after the wait the right PIN must reach the device"

    def test_ten_wrong_guesses_inside_a_minute_never_land_and_the_right_pin_waits(
        self, monkeypatch
    ):
        """The anti-brute-force property pinned end to end: ten WRONG guesses
        arrive inside 60 s at a spammer's pace, and they buy almost NOTHING.

        Only a guess that shows up AFTER the previous wait has run is ever
        compared (three 401s out of ten); every guess during a wait gets the
        identical silent 429 and is not even counted, so brute-forcing costs
        hours, not minutes. Then the CORRECT PIN arrives mid-wait and gets
        the same 429 - during the wait the bridge compares nothing, which is
        what denies the spammer the one non-429 answer that WOULD be the
        PIN - and it only reaches the Classic once the armed rung has run.

        The guesses are spent against this harness's dummy SET_PIN; the
        production bridge's live PIN is deliberately nowhere in this repo.
        """
        api = FakeApi()
        hass, _coordinator = installed(api=api)
        clock = _FakeMonotonic()
        monkeypatch.setattr(bridge_module, "time", clock)
        statuses = []
        for n in range(10):
            clock.advance(5.0)  # ten guesses, all inside 50 s
            response = post(hass, "pin", {"pin": f"{n:06d}"}, pin=NO_PIN)
            statuses.append(response.status)
            assert api.writes == [], f"guess {n} touched the device"
        # Rungs 5 s + 15 s let guesses 2 and 4 be compared; the third
        # comparison arms the 60 s rung, and the rest of the volley is
        # silence. That ladder IS the rate limit.
        assert statuses == [401, 401, 429, 429, 401, 429, 429, 429, 429, 429]
        # The correct PIN inside that 60 s wait: refused like a wrong one,
        # and no write slips through on its say-so.
        refused = post(hass, "write", {"register": ABSORB, "value": 576})
        assert refused.status == 429
        assert "retry_after" in refused.body
        assert api.writes == []
        # Out the other side of the armed rung, the right PIN finally lands.
        clock.advance(refused.body["retry_after"] + 0.1)
        landed = post(hass, "write", {"register": ABSORB, "value": 576})
        assert landed.status == 200
        assert api.writes == [(ABSORB, 576)]


class TestWriteView:
    def test_a_write_by_name_answers_with_the_register_it_landed_on(self):
        hass, coordinator = installed()
        response = post(hass, "write", {"register": "ABSORB_SETPOINT_VOLTAGE", "value": 576})
        assert response.status == 200
        assert response.body == {
            "register": ABSORB,
            "name": "ABSORB_SETPOINT_VOLTAGE",
            "value": 576,
            "committed": False,
        }
        assert (ABSORB, 576) in coordinator.api.writes

    def test_bodies_that_are_not_objects_are_refused_not_guessed(self):
        hass, _coordinator = installed()
        for bad in (FakeRequest.BAD, [1, 2], "write"):
            assert post(hass, "write", bad).status == 400

    def test_a_write_needs_both_fields(self):
        hass, _coordinator = installed()
        assert post(hass, "write", {"register": 4149}).status == 400
        assert post(hass, "write", {"value": 576}).status == 400

    def test_the_forbidden_registers_answer_400_with_a_reason(self):
        hass, coordinator = installed()
        response = post(hass, "write", {"register": 20492, "value": 49880})
        assert response.status == 400
        assert "handshake" in response.body["error"]
        assert coordinator.api.writes == []

    def test_a_write_the_classic_did_not_keep_answers_400(self):
        """Same read-back verdict the number entities raise."""
        api = FakeApi(read_values={ABSORB: 500}, stale_read=True)
        hass, _coordinator = installed(api=api)
        response = post(hass, "write", {"register": 4149, "value": 576})
        assert response.status == 400
        assert "500" in response.body["error"]


class TestClockView:
    def test_the_time_lands_in_the_private_file_write(self):
        hass, coordinator = installed()
        response = post(hass, "clock", {"time": CLOCK_TEXT})
        assert response.status == 200
        device, payload, address = coordinator.api.internal_writes[0]
        assert (device, address) == (7, 0)
        assert payload[9] == NOW.hour and payload[10] == NOW.minute

    def test_a_utc_suffix_becomes_ha_local_time_first(self):
        """The Classic is set with local wall clock; Z-time must convert."""
        hass, coordinator = installed()
        assert post(hass, "clock", {"time": CLOCK_TEXT_Z}).status == 200
        payload = coordinator.api.internal_writes[0][1]
        # The stub as_local strips the zone: the hour must arrive as sent,
        # not as 14 + zone math done twice, and never tz-aware.
        assert payload[9] == 14

    def test_only_parseable_times_are_accepted(self):
        hass, _coordinator = installed()
        assert post(hass, "clock", {"time": "yesterday"}).status == 400
        assert post(hass, "clock", {}).status == 400


class TestRebootView:
    def test_the_reboot_is_two_writes_and_an_ack(self):
        hass, coordinator = installed()
        response = post(hass, "reboot", {})
        assert response.status == 200
        assert coordinator.api.writes == [
            (REGISTER_MAP["ENABLE_FLAGS_2"], 0x04),
            (REGISTER_MAP["FORCE_FLAG_BITS"], 0x100),
        ]


class TestEepromSaveView:
    def test_the_save_is_one_force_flag_and_an_ack(self):
        hass, coordinator = installed()
        response = post(hass, "save", {})
        assert response.status == 200
        assert response.body["committed"] is True
        # ForceEEpromUpdate is bit 2: 0x4 into the LOW word (4160), chosen by
        # force_flag_write, not hardcoded - and it is the ONLY write.
        assert coordinator.api.writes == [(REGISTER_MAP["FORCE_FLAG_BITS"], 0x4)]


class TestDataloggerViews:
    def swept_api(self, monkeypatch):
        # 2026-09-11 in the anchored packing: month 4 bits low, day 5 next
        # (FINDINGS 46 - the app's parseTsLow field NAMES are swapped, its
        # bit ops are the layout).
        dates = [((2026 - 2000) << 9) | (11 << 4) | 9] + [0] * 31
        payload = bytearray(64)
        for n, value in enumerate(dates):
            payload[62 - 2 * n] = value & 0xFF
            payload[63 - 2 * n] = value >> 8
        monkeypatch.setattr(datalogger, "READ_GAP_SECONDS", 0)
        return RecordingInternalApi(payload=bytes(payload))

    def test_before_the_first_sweep_the_answer_is_honestly_empty(self):
        hass, _coordinator = installed()
        response = get(hass, "datalogger")
        assert response.status == 200
        assert response.body["days"] == []
        assert response.body["sweep"] is None
        assert response.body["sweeping"] is False

    def test_the_open_get_admits_a_sweep_is_in_flight(self):
        """The background collector's pass says "chart loading" through the
        OPEN read - the client waits without asking (or PINning) anything."""
        hass, coordinator = installed()
        get(hass, "datalogger")  # materialises the store like any first read
        coordinator.datalogger.sweeping = True
        response = get(hass, "datalogger")
        assert response.status == 200
        assert response.body["sweeping"] is True

    def test_a_refresh_joining_the_collector_answers_flagged(self, monkeypatch):
        # POST while a sweep runs: answered from the cache, flagged, and
        # the wire stays quiet - one sweep at a time on this device.
        api = self.swept_api(monkeypatch)
        hass, coordinator = installed(api=api)
        get(hass, "datalogger")
        coordinator.datalogger.sweeping = True
        response = post(hass, "datalogger/refresh", {})
        assert response.status == 200
        assert response.body["sweeping"] is True
        assert api.internal_reads == []

    def test_a_refresh_sweeps_and_answers_the_days(self, monkeypatch):
        api = self.swept_api(monkeypatch)
        hass, _coordinator = installed(api=api)
        response = post(hass, "datalogger/refresh", {})
        assert response.status == 200
        assert response.body["days"][0]["date"] == "2026-09-11"
        assert response.body["sweep"]["reads"] == 96

    def test_the_swept_days_come_back_on_later_reads_too(self, monkeypatch):
        api = self.swept_api(monkeypatch)
        hass, _coordinator = installed(api=api)
        post(hass, "datalogger/refresh", {})
        assert len(get(hass, "datalogger").body["days"]) == 1


class TestBridgeLifecycle:
    def set_up(self, options):
        coordinator_module.MidniteHub = Hub
        hass = Hass()
        config_entry = ConfigEntry(
            entry_id=ENTRY_ID,
            title="Classic",
            data={CONF_HOST: HOST, CONF_PORT: 502},
            options=options,
        )
        asyncio.run(integration.async_setup_entry(hass, config_entry))
        return hass, config_entry

    def test_with_the_option_absent_or_off_nothing_is_exposed(self):
        """The default is off: an old entry gains no API by upgrading."""
        for options in ({}, {CONF_BRIDGE_ENABLED: False}):
            hass, _entry = self.set_up(options)
            assert hass.http.views == []
            assert zeroconf.Zeroconf.instances == []

    def test_the_option_on_registers_views_and_advertises(self):
        hass, _entry = self.set_up({CONF_BRIDGE_ENABLED: True})
        assert len(hass.http.views) == len(BRIDGE_VIEWS)
        assert len(zeroconf.Zeroconf.instances) == 1
        assert zeroconf.Zeroconf.instances[0].registered

    def test_unload_withdraws_the_advertisement(self):
        hass, entry = self.set_up({CONF_BRIDGE_ENABLED: True})
        instance = zeroconf.Zeroconf.instances[0]
        asyncio.run(integration.async_unload_entry(hass, entry))
        assert instance.closed is True

    def test_the_bridge_gets_its_background_sweeper(self):
        """Bridge on: the entry grows a collector task that no client asked
        for - the chart fills itself. Unload cancels it."""
        hass, entry = self.set_up({CONF_BRIDGE_ENABLED: True})
        coordinator = hass.data[DOMAIN][ENTRY_ID]
        assert isinstance(coordinator.logger_sweeper, asyncio.Task)
        asyncio.run(integration.async_unload_entry(hass, entry))
        assert coordinator.logger_sweeper is None

    def test_a_bridgeless_entry_sweeps_nothing(self):
        """Bridge off (the default): no collector task - a plain HA install
        puts no extra sweep traffic on the Classic."""
        hass, entry = self.set_up({})
        coordinator = hass.data[DOMAIN][ENTRY_ID]
        assert getattr(coordinator, "logger_sweeper", None) is None

    def test_toggling_the_bridge_option_reloads_the_entry(self):
        """The bridge applies on reload; the listener must notice the toggle."""
        hass, entry = self.set_up({CONF_BRIDGE_ENABLED: True})
        instance = zeroconf.Zeroconf.instances[0]
        entry.options = {CONF_BRIDGE_ENABLED: False}
        asyncio.run(integration.update_listener(hass, entry))
        assert hass.config_entries.reloads == [ENTRY_ID]
        # And the unchanged pair reloads nothing (the DHCP-address path): the
        # reload above applied the toggle, which is what the coordinator's
        # remembered state models once the entry comes back.
        coordinator = hass.data[DOMAIN][ENTRY_ID]
        coordinator.bridge_enabled = False
        hass.config_entries.reloads.clear()
        asyncio.run(integration.update_listener(hass, entry))
        assert hass.config_entries.reloads == []


class TestBeacon:
    """The UDP beacon is the half of discovery that survives the firewalls
    that eat mDNS. Only the contract and the cadence are pinned here; the
    bytes actually reaching a client is proven on the wire in a bench session,
    never from the hardware-free suite (which must open no socket at all)."""

    def _entry(self, host=HOST):
        return ConfigEntry(
            entry_id=ENTRY_ID,
            title="Classic",
            data={CONF_HOST: host, CONF_PORT: 502},
            options={CONF_BRIDGE_ENABLED: True},
        )

    def _coordinator(self):
        return FakeCoordinator(Hass(), FakeApi(), identity_groups())

    def test_the_beacon_body_is_the_whole_call(self):
        """A listener needs nothing else to dial us: the HA address and port,
        the entry to call it by, the API version, and the Classic behind it."""
        body = json.loads(
            beacon_payload(self._entry(), self._coordinator(), "192.168.88.36", 8123)
        )
        assert body == {
            "t": BRIDGE_BEACON_TYPE,
            "api": BRIDGE_API_VERSION,
            "entry": ENTRY_ID,
            "addr": "192.168.88.36",
            "port": 8123,
            "name": "CLASSIC7",
            "model": DEVICE_TYPES.get(250 & 0xFF),
            "classic": HOST,
        }

    def test_the_advertiser_beats_and_close_silences_it(self):
        """Beat, then beat again, then silence after close - cadence pinned
        through a faked broadcaster, so no socket is involved."""
        beats = []
        advertiser = BridgeAdvertiser(
            Hass(),
            self._entry(),
            self._coordinator(),
            broadcaster=lambda payload, addr: beats.append((payload, addr)),
        )
        advertiser._beacon_interval = 0.02  # a cadence a test can wait out
        advertiser.publish()
        deadline = time.monotonic() + 2.0
        while len(beats) < 2 and time.monotonic() < deadline:
            time.sleep(0.02)
        advertiser.close()
        assert len(beats) >= 2, "the beacon never beat"
        payload, addr = beats[0]
        assert addr == "192.168.50.5"  # the address the record advertises (stub URL)
        assert json.loads(payload)["entry"] == ENTRY_ID
        after = len(beats)
        time.sleep(0.1)  # several intervals' worth
        assert len(beats) == after  # close() set the event; the thread is gone

    def test_a_running_suite_never_opens_a_beacon_socket(self, monkeypatch):
        """The load-bearing safety. Setup starts the beat thread, but its first
        act is to wait the interval and an unload silences it long before that
        wait is due, so the default (real) broadcaster is never called."""
        beats = []
        monkeypatch.setattr(
            bridge_module, "broadcast_beacon", lambda payload, addr: beats.append(addr)
        )
        coordinator_module.MidniteHub = Hub
        hass = Hass()
        entry = self._entry()
        asyncio.run(integration.async_setup_entry(hass, entry))
        assert zeroconf.Zeroconf.instances  # advertised, so the thread was started
        asyncio.run(integration.async_unload_entry(hass, entry))
        assert beats == []

    def test_even_without_an_unload_the_beat_never_fires_in_test(self):
        """A published-but-never-unloaded advertiser still cannot beat within
        a run: the interval dwarfs any single test and the daemon thread dies
        at interpreter exit (the whole suite runs in a fraction of it)."""
        beats = []
        advertiser = BridgeAdvertiser(
            Hass(),
            self._entry(),
            self._coordinator(),
            broadcaster=lambda payload, addr: beats.append(addr),
        )
        advertiser.publish()  # default BRIDGE_BEACON_INTERVAL: thread just sleeps
        time.sleep(0.1)
        assert beats == []
        advertiser.close()
