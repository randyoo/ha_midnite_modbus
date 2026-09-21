"""Config flow for the Midnite Solar integration."""

from __future__ import annotations

import logging
from typing import Any

from pymodbus.client import ModbusTcpClient
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
try:
    # Try new import path first (Home Assistant 2025.12+)
    from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
except ImportError:
    # Fallback to old import path for older versions
    from homeassistant.components.dhcp import DhcpServiceInfo

from .const import DEFAULT_PORT, DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL
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
        _LOGGER.debug("MAC probe raised; entry proceeds without a unique id", exc_info=True)
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

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        _LOGGER.info(
            "DHCP discovery: Classic candidate at %s (MAC %s)",
            discovery_info.ip,
            discovery_info.macaddress,
        )
        
        # Format the MAC address properly for unique ID using Home Assistant's standard format
        from homeassistant.helpers.device_registry import format_mac
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
                await self.hass.config_entries.async_update_entry(
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
                        unit_id = result.registers[0] if len(result.registers) > 0 else None
                        if unit_id is not None:
                            from .const import DEVICE_TYPES
                            device_type = unit_id & 0xFF  # Get LSB (unit type)
                            model_name = DEVICE_TYPES.get(device_type, f"Midnite Device ({device_type})")
                            _LOGGER.info("Discovered device model: %s", model_name)
                            # Set the model as the name for badge display
                            self.context["title_placeholders"]["name"] = model_name
                        else:
                            _LOGGER.info("Could not read UNIT_ID register - result.registers is empty")
                    else:
                        _LOGGER.info("Failed to read device registers: %s", result)
                else:
                    _LOGGER.info("Could not connect to device at %s for model identification", discovery_info.ip)
            finally:
                # close() in finally: if the read raises, the discovery socket is
                # still given back, so one unlucky DHCP callback leaks no fd.
                client.close()
        except Exception as e:
            _LOGGER.warning("Error reading device model during discovery: %s", e, exc_info=True)
        
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
        # Check if we came from DHCP discovery
        discovered = hasattr(self, 'discovery_info') and self.discovery_info is not None
        _LOGGER.info(
            "User step from %s discovery", "DHCP" if discovered else "manual entry"
        )
        
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # If triggered by discovery, user_input may only contain confirmation
            # If triggered manually, user_input contains full form data
            
            # For DHCP discovery, pre-fill the host and port from discovery info
            if discovered and CONF_HOST not in user_input:
                user_input[CONF_HOST] = self.discovery_info.ip
                user_input[CONF_PORT] = DEFAULT_PORT
            elif not discovered and CONF_HOST not in user_input:
                # Manual entry requires host
                errors["base"] = "missing_host"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                    }),
                    errors=errors,
                )
            
            # Check for duplicate entries
            self._async_abort_entries_match(
                {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT)}
            )
            
            # Test connection, bounded like every other flow socket and closed
            # in finally so a read that raises (the documented fate of a
            # half-dead 502 port) cannot leak the socket.
            mac = None
            probed = False
            client = _probe_client(user_input[CONF_HOST], user_input.get(CONF_PORT, DEFAULT_PORT))
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
            except Exception as ex:
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
                    title=title,
                    data=entry_data,
                    options=entry_options
                )

        # Show appropriate form based on discovery status
        if discovered and self.discovery_info:
            # For DHCP discovery, show a confirmation dialog with device details
            # and pre-filled values.
            data_schema = vol.Schema({
                vol.Required(CONF_HOST, default=self.discovery_info.ip): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            })
            
            return self.async_show_form(
                step_id="user",
                data_schema=data_schema,
                description_placeholders={
                    "ip": self.discovery_info.ip,
                    "mac": self.discovery_info.macaddress,
                },
                errors=errors,
            )
        else:
            # For manual entry, show the full configuration form.
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                }),
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

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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
            entry_options = {}
            if CONF_SCAN_INTERVAL in user_input:
                entry_options[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]
            
            # Update data and options separately, and await it: this is a
            # coroutine, and without the await the new address is never stored,
            # so reconfiguring the Classic in the UI appeared to work and changed
            # nothing.
            await self.hass.config_entries.async_update_entry(
                config_entry,
                data=entry_data,
                options=entry_options
            )
            
            await self.hass.config_entries.async_reload(config_entry.entry_id)
            return self.async_abort(reason="reconfigure_success")
        
        # Pre-fill the form with current values
        data_schema = vol.Schema({
            vol.Required(CONF_HOST, default=config_entry.data.get(CONF_HOST)): str,
            vol.Required(CONF_PORT, default=config_entry.data.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Optional(CONF_SCAN_INTERVAL, default=config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
        })
        
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
        )

class MidniteSolarOptionsFlow(OptionsFlow):
    """Change how often the Classic is polled.

    `__init__.py` reads this option and `update_listener` reloads the entry when
    it changes, but until now there was no options flow: the step that looked like
    one called a method Home Assistant does not do, so it could only ever raise
    and the interval stayed at its default.
    """

    def __init__(self, config_entry):
        """Keep the entry whose options are being edited."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show or store the scan interval."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): int,
                }
            ),
        )


async def async_get_options_flow(config_entry):
    """Home Assistant calls this to offer the options form."""
    return MidniteSolarOptionsFlow(config_entry)
