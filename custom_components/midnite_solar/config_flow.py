"""Config flow for the Midnite Solar integration."""

from __future__ import annotations

import logging
from typing import Any

from pymodbus.client import ModbusTcpClient
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.device_registry import format_mac

# The 2025.12+ path; the pre-2025.12 homeassistant.components.dhcp module no
# longer carries the type at all (mypy proved it against the installed HA),
# so the old fallback was dead code that only ever confused the type checker.
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

# Reuse the write gate's OWN predicate, so the options form and the gate agree
# on what a real PIN is by construction, not by two copies drifting. Importing
# bridge here is not circular (bridge never imports config_flow) and the module
# is already loaded by the time a flow opens.
from .bridge import write_pin_is_set
from .const import (
    CONF_BRIDGE_ENABLED,
    CONF_SCAN_INTERVAL,
    CONF_SENSOR_INTERVAL,
    CONF_WRITE_PIN,
    DEFAULT_BRIDGE_ENABLED,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SENSOR_INTERVAL,
    DEFAULT_WRITE_PIN,
    DEVICE_TYPES,
    DOMAIN,
)
from .register_values import format_mac_from_registers

_LOGGER = logging.getLogger(__name__)

# Bounded timeout for the one-off read a discovery/config/import step makes to
# identify or verify a device, so no flow ever sits on a dead 502 port for the
# pymodbus default (3 s, and 3 s x 3 retries once retries are left on).
DISCOVERY_TIMEOUT = 3.0

# The MAC address registers 4106-4108, the same three the MAC sensor reads.
# A manual entry claims this as its unique id so a later DHCP discovery of the
# same Classic matches the entry instead of offering a duplicate card.
MAC_WIRE_ADDRESS = 4105  # zero-indexed register 4106
MAC_REGISTER_COUNT = 3


def _probe_client(host: str, port: int) -> ModbusTcpClient:
    """A one-off probe client with the hub's bounded-socket policy.

    Every flow socket goes through here: the pymodbus defaults (3 s timeout
    with 3 retries) would let a half-dead Classic hold a config flow ~12 s per
    read, and a flow is not allowed to linger on a single-connection device.
    """
    return ModbusTcpClient(
        host,
        port=port,
        timeout=DISCOVERY_TIMEOUT,
        retries=0,
    )


def _read_mac(client: ModbusTcpClient):
    """Read registers 4106-4108 and return the canonical MAC, or None.

    None - including a raising read - means the device answered the
    verification read but not the MAC probe. That must not veto the entry:
    identification is a bonus on a connection already proven, and a socket
    that dies on the SECOND read still leaves a Classic that demonstrably
    answers the first one.
    """
    try:
        result = client.read_holding_registers(
            address=MAC_WIRE_ADDRESS, count=MAC_REGISTER_COUNT
        )
    except Exception:
        _LOGGER.debug(
            "MAC probe raised; entry proceeds without a unique id", exc_info=True
        )
        return None
    if result is None or result.isError() or len(result.registers) < MAC_REGISTER_COUNT:
        return None
    return format_mac_from_registers(*result.registers)


class MidniteSolarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Midnite Solar."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        super().__init__()
        self.discovery_info: DhcpServiceInfo | None = None

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        _LOGGER.info(
            "DHCP discovery: Classic candidate at %s (MAC %s)",
            discovery_info.ip,
            discovery_info.macaddress,
        )

        # Format the MAC address properly for unique ID using Home Assistant's standard format
        formatted_mac = format_mac(discovery_info.macaddress)

        # Set unique ID to prevent duplicate setups
        await self.async_set_unique_id(formatted_mac, raise_on_progress=False)

        # A Classic that is already set up is never set up twice. Its address may
        # have changed since - a DHCP lease is not permanent - so the entry is
        # updated and reloaded rather than left pointing at an address that no
        # longer answers. Aborting first, as this used to do, meant that after a
        # lease renewal Home Assistant kept polling the old address and the device
        # could only be recovered by deleting and re-adding it.
        for entry in self._async_current_entries():
            if entry.unique_id != formatted_mac:
                continue
            if entry.data.get(CONF_HOST) != discovery_info.ip:
                _LOGGER.info(
                    "Classic %s moved from %s to %s; updating the entry",
                    entry.title,
                    entry.data.get(CONF_HOST),
                    discovery_info.ip,
                )
                # HA's async_update_entry is SYNC (it has always
                # returned bool; awaiting it - as this file once did -
                # raises TypeError the instant a DHCP address change lands
                # on a real Home Assistant).
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_HOST: discovery_info.ip}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
            else:
                _LOGGER.info(
                    "Device with MAC %s at %s is already configured as '%s'; skipping discovery",
                    discovery_info.macaddress,
                    discovery_info.ip,
                    entry.title,
                )
            return self.async_abort(reason="already_configured")

        # Store discovery info for user confirmation
        self.discovery_info = discovery_info

        # Set initial title placeholder - will be updated with model if successful
        self.context["title_placeholders"] = {"name": "Midnite Solar"}

        # Try to read device model from the device for better identification in UI
        try:
            _LOGGER.info("Reading device model from discovered %s", discovery_info.ip)
            client = _probe_client(discovery_info.ip, DEFAULT_PORT)
            try:
                connected = await self.hass.async_add_executor_job(client.connect)
                if connected:
                    # Read UNIT_ID register to get device type
                    result = await self.hass.async_add_executor_job(
                        lambda: client.read_holding_registers(address=4100, count=2)
                    )

                    if result and not result.isError():
                        # Register 4101 contains device type in LSB
                        unit_id = (
                            result.registers[0] if len(result.registers) > 0 else None
                        )
                        if unit_id is not None:
                            device_type = unit_id & 0xFF  # Get LSB (unit type)
                            model_name = DEVICE_TYPES.get(
                                device_type, f"Midnite Device ({device_type})"
                            )
                            _LOGGER.info("Discovered device model: %s", model_name)
                            # Set the model as the name for badge display:
                            # the WHOLE placeholder dict goes in at once
                            # (HA types context as a Mapping; core
                            # integrations assign the dict, never mutate
                            # through it).
                            self.context["title_placeholders"] = {"name": model_name}
                        else:
                            _LOGGER.info(
                                "Could not read UNIT_ID register - result.registers is empty"
                            )
                    else:
                        _LOGGER.info("Failed to read device registers: %s", result)
                else:
                    _LOGGER.info(
                        "Could not connect to device at %s for model identification",
                        discovery_info.ip,
                    )
            finally:
                # close() in finally: if the read raises, the discovery socket is
                # still given back, so one unlucky DHCP callback leaks no fd.
                client.close()
        except Exception as e:
            _LOGGER.warning(
                "Error reading device model during discovery: %s", e, exc_info=True
            )

        # Show user confirmation with pre-filled IP and port
        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "ip": discovery_info.ip,
                "mac": discovery_info.macaddress,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step (manual or DHCP discovery)."""
        # Check if we came from DHCP discovery (local alias: mypy narrows
        # locals through `is None` checks but never attributes).
        discovery = self.discovery_info
        discovered = discovery is not None
        _LOGGER.info(
            "User step from %s discovery", "DHCP" if discovered else "manual entry"
        )

        errors: dict[str, str] = {}

        if user_input is not None:
            # If triggered by discovery, user_input may only contain confirmation
            # If triggered manually, user_input contains full form data

            # For DHCP discovery, pre-fill the host and port from discovery info
            if discovery is not None and CONF_HOST not in user_input:
                user_input[CONF_HOST] = discovery.ip
                user_input[CONF_PORT] = DEFAULT_PORT
            elif discovery is None and CONF_HOST not in user_input:
                # Manual entry requires host
                errors["base"] = "missing_host"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_HOST): str,
                            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                            vol.Optional(
                                CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                            ): int,
                        }
                    ),
                    errors=errors,
                )

            # Check for duplicate entries
            self._async_abort_entries_match(
                {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                }
            )

            # Test connection, bounded like every other flow socket and closed
            # in finally so a read that raises (the documented fate of a
            # half-dead 502 port) cannot leak the socket.
            mac = None
            probed = False
            client = _probe_client(
                user_input[CONF_HOST], user_input.get(CONF_PORT, DEFAULT_PORT)
            )
            try:
                connected = await self.hass.async_add_executor_job(client.connect)
                if not connected:
                    errors["base"] = "cannot_connect"
                else:
                    # Try to read a register to verify communication
                    result = await self.hass.async_add_executor_job(
                        lambda: client.read_holding_registers(address=4100, count=1)
                    )
                    if result.isError():
                        errors["base"] = "cannot_read"
                    elif not discovered:
                        # A manual entry claims the Classic's MAC as its unique
                        # id (read registers 4106-4108 in the same session).
                        # Without one, a later DHCP discovery of the same device
                        # cannot match it - only host+port blocked a duplicate -
                        # so a lease move surfaced a second "add this device?"
                        # card for a Classic that was already set up.
                        probed = True
                        mac = await self.hass.async_add_executor_job(_read_mac, client)
            except Exception:
                _LOGGER.exception("Unexpected exception during connection test")
                errors["base"] = "unknown"
            finally:
                client.close()

            # The duplicate-by-MAC check runs after the finally, not inside the
            # test above: its AbortFlow would otherwise be caught by that broad
            # except and mis-reported as "unknown".
            if not errors and probed:
                if mac is None:
                    _LOGGER.info(
                        "%s did not report its MAC - the entry will have no "
                        "unique id and cannot be matched by discovery",
                        user_input[CONF_HOST],
                    )
                elif await self.async_set_unique_id(mac) is not None:
                    self._abort_if_unique_id_configured()

            if not errors:
                # Determine title based on discovery or manual entry
                if discovered and self.discovery_info:
                    title = f"Midnite Solar @ {user_input[CONF_HOST]}"
                else:
                    title = f"Midnite Solar @ {user_input[CONF_HOST]}"

                # Separate scan_interval from data to store in options
                entry_data = {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                }
                entry_options = {}
                if CONF_SCAN_INTERVAL in user_input:
                    entry_options[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

                return self.async_create_entry(
                    title=title, data=entry_data, options=entry_options
                )

        # Show appropriate form based on discovery status
        if discovered and self.discovery_info:
            # For DHCP discovery, show a confirmation dialog with device details
            # and pre-filled values.
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self.discovery_info.ip): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): int,
                }
            )

            return self.async_show_form(
                step_id="user",
                data_schema=data_schema,
                description_placeholders={
                    "ip": self.discovery_info.ip,
                    "mac": self.discovery_info.macaddress,
                },
                errors=errors,
            )
        # For manual entry, show the full configuration form.
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): int,
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Handle import from YAML configuration."""
        self._async_abort_entries_match(
            {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input[CONF_PORT]}
        )

        client = _probe_client(user_input[CONF_HOST], user_input[CONF_PORT])
        try:
            connected = await self.hass.async_add_executor_job(client.connect)
            if not connected:
                return self.async_abort(reason="cannot_connect")

            # Try to read a register to verify communication
            result = await self.hass.async_add_executor_job(
                lambda: client.read_holding_registers(address=4100, count=1)
            )
            if result.isError():
                return self.async_abort(reason="cannot_read")

            # Imported entries claim the MAC unique id too, so a YAML-created
            # entry follows a DHCP lease move like any other.
            mac = await self.hass.async_add_executor_job(_read_mac, client)
            if mac is not None:
                if await self.async_set_unique_id(mac) is not None:
                    return self.async_abort(reason="already_configured")
            return self.async_create_entry(
                title=f"Midnite Solar @ {user_input[CONF_HOST]}",
                data={
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                },
            )
        except Exception:
            _LOGGER.exception("Unexpected exception during import connection test")
            return self.async_abort(reason="unknown")
        finally:
            # The aborts above leave this finally on every path: a read that
            # raises must not strand the socket on a single-connection device.
            client.close()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        config_entry = self._get_reconfigure_entry()

        if user_input is not None:
            # Update the config entry with new data
            #
            # An entry created before manual entries claimed a MAC has no
            # unique id at all; Home Assistant's mismatch check compares the
            # two (None != None is False, so it does not abort) and this flow
            # does not fabricate one - the repair is to delete and re-add, or
            # accept the discovery card the next time DHCP sees the Classic.
            await self.async_set_unique_id(config_entry.unique_id)
            self._abort_if_unique_id_mismatch()

            # Separate scan_interval from data to store in options
            entry_data = {
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
            }
            # Reconfigure's form shows address, not options, so it starts from
            # the entry's CURRENT options and overwrites only what the form
            # carries. Rebuilding the dict from nothing would silently switch
            # an enabled bridge off the next time someone moved an IP.
            entry_options = dict(config_entry.options)
            if CONF_SCAN_INTERVAL in user_input:
                entry_options[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

            # Update data and options BEFORE the reload, synchronously: HA's
            # async_update_entry is a SYNC call that returns bool; the await
            # this comment used to insist on raised TypeError on the real
            # thing (the entry update itself landed, the reload after it
            # never ran). The reload is the coroutine.
            self.hass.config_entries.async_update_entry(
                config_entry, data=entry_data, options=entry_options
            )

            await self.hass.config_entries.async_reload(config_entry.entry_id)
            return self.async_abort(reason="reconfigure_success")

        # Pre-fill the form with current values
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=config_entry.data.get(CONF_HOST)): str,
                vol.Required(
                    CONF_PORT, default=config_entry.data.get(CONF_PORT, DEFAULT_PORT)
                ): int,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): int,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> MidniteSolarOptionsFlow:
        """The options-flow factory Home Assistant 2026.x actually calls.

        HA decides `supports_options` (on the class) and to offer the options
        form it calls THIS. A module-level function of the
        same name is invisible to it - the check is
        `cls.async_get_options_flow is not ConfigFlow.async_get_options_flow` -
        so an integration that only has the module-level form reports
        `supports_options=False` and the bridge toggle never appears. Bench
        2026-09-22: exactly this left the Flutter app's bridge option missing.
        """
        return MidniteSolarOptionsFlow(config_entry)


class MidniteSolarOptionsFlow(OptionsFlow):
    """Change the two cadences and whether the bridge is up.

    `__init__.py` reads these options and `update_listener` reloads the entry
    when they change, but until now there was no options flow: the step that
    looked like one called a method Home Assistant does not do, so it could
    only ever raise and the interval stayed at its default.

    The cadences are deliberately separate: the Modbus poll feeds the live
    bridge cache, while the sensor interval is how often those readings may
    be republished to Home Assistant's entities (and so enter the history
    database). An app that watches the bridge at a second a pace needs fast
    Modbus and slow history, not one number serving both badly.

    The write PIN is the bridge's ONLY write gate (the bridge carries no
    access token): a required 6-digit value, validated so the all-zeros
    placeholder cannot be saved - writes stay refused until a real PIN is set.
    Changing it reloads the entry, which also clears the PIN's lockout ladder -
    correct, since the owner just rotated it.
    """

    def __init__(self, config_entry):
        """Hold the entry whose options are being edited.

        Home Assistant 2026.9 makes `OptionsFlow.config_entry` a READ-ONLY
        property resolved from `handler`; assigning to it in `__init__` raised
        "property has no setter", which surfaced as an HTTP 500 the instant the
        options dialog opened (and a dead "enable the bridge" step in the Flutter
        app). Storing the entry under our own attribute is the fix; it is only
        read here for the form defaults, and HA still writes the finished
        options through its own handler lookup.
        """
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show or store the two intervals, the bridge switch, and the PIN.

        The write PIN is validated HERE, in code, and never in the schema:
        Home Assistant turns a flow's data_schema into JSON for the web UI, and
        it can represent a plain `str` field but NOT a custom vol.All validator
        function - wrapping one made the options dialog 500 the instant it
        opened (caught live 2026-09). So the field is a plain `str` and the
        6-digit rule runs on submit, using the write gate's OWN predicate so
        the form refuses exactly what a write would refuse.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            # Leaving the placeholder (or omitting the field) is a VALID save:
            # it just means writes stay off, which the write gate already
            # enforces. The form only rejects a value that is neither the
            # placeholder nor a real 6-digit PIN - a half-typed 0000 or "abc",
            # which would silently do nothing. This way a watcher who never
            # writes can still save an interval change; no one can save a
            # look-alike PIN that they think enables writes but does not.
            pin = str(user_input.get(CONF_WRITE_PIN, DEFAULT_WRITE_PIN))
            if pin != DEFAULT_WRITE_PIN and not write_pin_is_set(pin):
                errors[CONF_WRITE_PIN] = "invalid_write_pin"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self._entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): int,
                    vol.Optional(
                        CONF_SENSOR_INTERVAL,
                        default=self._entry.options.get(
                            CONF_SENSOR_INTERVAL, DEFAULT_SENSOR_INTERVAL
                        ),
                    ): int,
                    # Off by default: it opens a PIN-guarded write path to the
                    # MPPT that other LAN tools can reach (reads go public too).
                    vol.Optional(
                        CONF_BRIDGE_ENABLED,
                        default=self._entry.options.get(
                            CONF_BRIDGE_ENABLED, DEFAULT_BRIDGE_ENABLED
                        ),
                    ): bool,
                    # The whole write protection (the bridge carries no token).
                    # A PLAIN str so Home Assistant can serialize the form; the
                    # 6-digit rule is enforced in code just above and again by
                    # the write gate at write time. Prefilled with the current
                    # value (or the all-zeros placeholder) so unset looks unset.
                    vol.Optional(
                        CONF_WRITE_PIN,
                        default=self._entry.options.get(
                            CONF_WRITE_PIN, DEFAULT_WRITE_PIN
                        ),
                    ): str,
                }
            ),
            errors=errors,
        )
