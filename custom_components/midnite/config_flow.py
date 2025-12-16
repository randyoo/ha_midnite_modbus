"""Config flow for the Midnite Solar integration."""

from __future__ import annotations

import inspect
import logging
from typing import Any

from pymodbus.client import ModbusTcpClient
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.core import callback

from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MidniteSolarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Midnite Solar."""

    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        super().__init__()
        self.discovery_info: DhcpServiceInfo | None = None

    @callback
    def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        _LOGGER.info(f"DHCP discovery for Midnite Solar device at {discovery_info.ip}")
        
        # 1. SET UNIQUE ID (Crucial step - use MAC address)
        from homeassistant.config_entries import ConfigEntries
        await self.async_set_unique_id(ConfigEntries.format_mac(discovery_info.macaddress))
        
        # 2. ABORT IF ALREADY CONFIGURED (prevents duplicate discovery cards)
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: discovery_info.ip}
        )
        
        # 3. STORE DISCOVERY INFO FOR USER CONFIRMATION
        self.discovery_info = discovery_info
        self.context["title_placeholders"] = {"ip": discovery_info.ip}
        
        # 4. TRIGGER USER FLOW TO SHOW "DISCOVERED" CARD
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step (manual or DHCP discovery)."""
        errors: dict[str, str] = {}
        
        # Check if we came from DHCP discovery
        discovered = hasattr(self, 'discovery_info') and self.discovery_info is not None
        
        if user_input is not None:
            # If triggered by discovery, user_input may only contain confirmation
            # If triggered manually, user_input contains full form data
            
            # For DHCP discovery, pre-fill the host from discovery info
            if discovered and CONF_HOST not in user_input:
                user_input[CONF_HOST] = self.discovery_info.ip
            elif not discovered and CONF_HOST not in user_input:
                # Manual entry requires host
                errors["base"] = "missing_host"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
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
                
                return self.async_create_entry(
                    title=title,
                    data=user_input
                )

        # Show appropriate form based on discovery status
        if discovered and self.discovery_info:
            # For DHCP discovery, show a confirmation dialog
            _LOGGER.info(f"Showing confirmation for discovered device at {self.discovery_info.ip}")
            return self.async_show_form(
                step_id="user",
                description_placeholders={"ip": self.discovery_info.ip},
                errors=errors,
            )
        else:
            # For manual entry, show the full configuration form
            _LOGGER.info("Showing manual configuration form")
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                }),
                errors=errors,
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
