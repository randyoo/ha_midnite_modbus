"""Config flow for the Midnite Solar integration."""

from __future__ import annotations

import inspect
import logging
from typing import Any

from pymodbus.client import ModbusTcpClient
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
try:
    # Try new import path first (Home Assistant 2025.12+)
    from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
except ImportError:
    # Fallback to old import path for older versions
    from homeassistant.components.dhcp import DhcpServiceInfo

from .const import DEFAULT_PORT, DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class MidniteSolarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Midnite Solar."""

    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        super().__init__()
        self.discovery_info: DhcpServiceInfo | None = None

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        _LOGGER.info("========================================")
        _LOGGER.info("DHCP DISCOVERY TRIGGERED!")
        _LOGGER.info(f"Device IP: {discovery_info.ip}")
        _LOGGER.info(f"MAC Address: {discovery_info.macaddress}")
        if hasattr(discovery_info, 'hostname'):
            _LOGGER.info(f"Hostname: {discovery_info.hostname}")
        _LOGGER.info("========================================")
        
        # Format the MAC address properly for unique ID using Home Assistant's standard format
        from homeassistant.helpers.device_registry import format_mac
        formatted_mac = format_mac(discovery_info.macaddress)
        
        # Set unique ID to prevent duplicate setups
        await self.async_set_unique_id(formatted_mac, raise_on_progress=False)
        
        # Abort if device is already configured (this will also update IP if it changed)
        existing_entries = self._async_current_entries()
        for entry in existing_entries:
            if entry.unique_id == formatted_mac:
                _LOGGER.warning(
                    f"Device with MAC {discovery_info.macaddress} at {discovery_info.ip} "
                    f"is already configured as '{entry.title}'. Skipping discovery."
                )
                return self.async_abort(reason="already_configured")
        
        # Update IP if device was previously configured with a different IP
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.ip})
        
        # Store discovery info for user confirmation
        self.discovery_info = discovery_info
        
        # Set title placeholders - Home Assistant uses these for the badge display
        # The large font shows the model, small font shows manufacturer/integration name
        self.context["title_placeholders"] = {"name": "Midnite Solar"}
        
        # Try to read device model from the device for better identification in UI
        try:
            _LOGGER.info(f"Attempting to read device model from {discovery_info.ip}...")
            client = ModbusTcpClient(discovery_info.ip, port=DEFAULT_PORT)
            connected = await self.hass.async_add_executor_job(client.connect)
            if connected:
                # Read UNIT_ID register to get device type
                result = await self.hass.async_add_executor_job(
                    lambda: client.read_holding_registers(address=4100, count=2)
                )
                client.close()
                
                if result and not result.isError():
                    # Register 4101 contains device type in LSB
                    unit_id = result.registers[0] if len(result.registers) > 0 else None
                    if unit_id is not None:
                        from .const import DEVICE_TYPES
                        device_type = unit_id & 0xFF  # Get LSB (unit type)
                        model_name = DEVICE_TYPES.get(device_type, f"Midnite Device ({device_type})")
                        _LOGGER.info(f"Discovered device model: {model_name}")
                        # Set the model as the name for badge display
                        self.context["title_placeholders"]["name"] = model_name
                    else:
                        _LOGGER.warning("Could not read UNIT_ID register for device model identification")
                else:
                    _LOGGER.warning(f"Failed to read device registers: {result}")
            else:
                _LOGGER.warning(f"Could not connect to device at {discovery_info.ip} for model identification")
        except Exception as e:
            _LOGGER.warning(f"Error reading device model during discovery: {e}", exc_info=True)
        
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
        _LOGGER.info("========================================")
        _LOGGER.info("async_step_user CALLED")
        _LOGGER.info(f"user_input: {user_input}")
        
        # Check if we came from DHCP discovery
        discovered = hasattr(self, 'discovery_info') and self.discovery_info is not None
        if discovered:
            _LOGGER.info("✓ Called from DHCP DISCOVERY")
            _LOGGER.info(f"  MAC: {self.discovery_info.macaddress}")
            _LOGGER.info(f"  IP: {self.discovery_info.ip}")
        else:
            _LOGGER.info("✓ Called from MANUAL entry")
        _LOGGER.info("========================================")
        
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
            
            # Debug: Log pymodbus version and API signature
            import pymodbus
            _LOGGER.info(f"PyModbus version: {pymodbus.__version__}")
            sig = inspect.signature(ModbusTcpClient.read_holding_registers)
            _LOGGER.info(f"read_holding_registers signature: {sig}")
            
            # Test connection
            client = ModbusTcpClient(user_input[CONF_HOST], port=user_input[CONF_PORT])
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
                    
                client.close()
            except Exception as ex:
                _LOGGER.exception("Unexpected exception during connection test")
                errors["base"] = "unknown"
            
            if not errors:
                # Determine title based on discovery or manual entry
                if discovered and self.discovery_info:
                    title = f"Midnite Solar @ {user_input[CONF_HOST]}"
                else:
                    title = user_input.get(CONF_NAME, f"Midnite Solar @ {user_input[CONF_HOST]}")
                
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
            _LOGGER.info("========================================")
            _LOGGER.info("SHOWING DISCOVERY CONFIRMATION FORM")
            _LOGGER.info(f"Device IP: {self.discovery_info.ip}")
            _LOGGER.info("User should see a 'Discovered' card in UI")
            _LOGGER.info("========================================")
            
            # Create data schema with pre-filled values for DHCP discovery
            data_schema = vol.Schema({
                vol.Required(CONF_HOST, default=self.discovery_info.ip): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            })
            
            result = self.async_show_form(
                step_id="user",
                data_schema=data_schema,
                description_placeholders={
                    "ip": self.discovery_info.ip,
                    "mac": self.discovery_info.macaddress,
                },
                errors=errors,
            )
            return result
        else:
            # For manual entry, show the full configuration form
            _LOGGER.info("========================================")
            _LOGGER.info("SHOWING MANUAL CONFIGURATION FORM")
            _LOGGER.info("User should see full config form in UI")
            _LOGGER.info("========================================")
            result = self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                }),
                errors=errors,
            )
            return result

    async def async_step_options(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle options update."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=user_input,
            )
        
        # Get current options from the config entry
        entry = self._get_current_entries()[0]
        current_options = entry.options
        
        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL, 
                    default=current_options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ): int,
            }),
        )

    async def async_step_import(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Handle import from YAML configuration."""
        self._async_abort_entries_match(
            {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input[CONF_PORT]}
        )
        
        client = ModbusTcpClient(user_input[CONF_HOST], port=user_input[CONF_PORT])
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
            
            client.close()
        except Exception:
            _LOGGER.exception("Unexpected exception during import connection test")
            return self.async_abort(reason="unknown")

        return self.async_create_entry(
            title=f"Midnite Solar @ {user_input[CONF_HOST]}",
            data={
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
            },
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        config_entry = self._get_reconfigure_entry()
        
        if user_input is not None:
            # Update the config entry with new data
            self.async_set_unique_id(config_entry.unique_id)
            self._abort_if_unique_id_mismatch()
            
            # Separate scan_interval from data to store in options
            entry_data = {
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
            }
            entry_options = {}
            if CONF_SCAN_INTERVAL in user_input:
                entry_options[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]
            
            # Update data and options separately
            self.hass.config_entries.async_update_entry(
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