"""Config flow for HT HomeService."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from aiohttp import CookieJar

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import HiotApiClient, HiotAuthError, HiotConnectionError
from .const import (
    CONF_DONG,
    CONF_ENERGY_SCAN_INTERVAL,
    CONF_HO,
    CONF_HOMEPAGE_DOMAIN,
    CONF_DEVICE_SCAN_INTERVAL,
    CONF_SITE_ID,
    CONF_SITE_NAME,
    DEFAULT_ENERGY_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    DEVICE_SCAN_INTERVAL_OPTIONS,
    ENERGY_SCAN_INTERVAL_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class HiotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HT HomeService."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> HiotOptionsFlow:
        """Get the options flow handler."""
        return HiotOptionsFlow()

    def __init__(self) -> None:
        """Initialize."""
        super().__init__()
        self._username: str = ""
        self._password: str = ""
        self._danji_list: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial login step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            session = async_create_clientsession(
                self.hass, cookie_jar=CookieJar(unsafe=True)
            )
            client = HiotApiClient(session)

            try:
                await client.async_login(self._username, self._password)
                self._danji_list = await client.async_get_households()
            except HiotAuthError:
                errors["base"] = "invalid_auth"
            except HiotConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "unknown"
            else:
                if not self._danji_list:
                    errors["base"] = "no_danji"
                elif len(self._danji_list) == 1:
                    danji = self._danji_list[0]
                    return await self._create_entry(danji)
                else:
                    return await self.async_step_select_danji()

        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors,
        )

    async def async_step_select_danji(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle apartment complex selection."""
        if user_input is not None:
            selected_index = int(user_input["danji"])
            danji = self._danji_list[selected_index]
            return await self._create_entry(danji)

        danji_options = {
            str(i): f"{d['siteName']} ({d['dong']}동 {d['ho']}호)"
            for i, d in enumerate(self._danji_list)
        }

        return self.async_show_form(
            step_id="select_danji",
            data_schema=vol.Schema(
                {
                    vol.Required("danji"): vol.In(danji_options),
                }
            ),
        )

    async def _create_entry(self, danji: dict[str, Any]) -> ConfigFlowResult:
        """Create a config entry for the selected apartment."""
        site_id = danji["siteId"]
        site_name = danji["siteName"]

        unique_id = f"{self._username}_{site_id}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"{site_name} ({danji['dong']}동 {danji['ho']}호)",
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_SITE_ID: site_id,
                CONF_SITE_NAME: site_name,
                CONF_DONG: danji["dong"],
                CONF_HO: danji["ho"],
                CONF_HOMEPAGE_DOMAIN: danji.get("homepageDomain", ""),
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth upon auth failure."""
        self._username = entry_data[CONF_USERNAME]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            password = user_input[CONF_PASSWORD]

            session = async_create_clientsession(
                self.hass, cookie_jar=CookieJar(unsafe=True)
            )
            client = HiotApiClient(session)

            try:
                await client.async_login(self._username, password)
            except HiotAuthError:
                errors["base"] = "invalid_auth"
            except HiotConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"
            else:
                reauth_entry = self._get_reauth_entry()
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
            description_placeholders={"username": self._username},
        )


def _format_interval_label(seconds: int) -> str:
    """Format seconds into a human-readable label."""
    if seconds >= 60:
        minutes = seconds // 60
        return f"{minutes}min"
    return f"{seconds}s"


class HiotOptionsFlow(OptionsFlow):
    """Handle options for HT HomeService."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_device_interval = self.config_entry.options.get(
            CONF_DEVICE_SCAN_INTERVAL,
            self.config_entry.options.get(
                "scan_interval", int(DEFAULT_SCAN_INTERVAL.total_seconds())
            ),
        )
        current_energy_interval = self.config_entry.options.get(
            CONF_ENERGY_SCAN_INTERVAL, int(DEFAULT_ENERGY_SCAN_INTERVAL.total_seconds())
        )

        device_interval_options = {
            str(s): _format_interval_label(s) for s in DEVICE_SCAN_INTERVAL_OPTIONS
        }
        energy_interval_options = {
            str(s): _format_interval_label(s) for s in ENERGY_SCAN_INTERVAL_OPTIONS
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_SCAN_INTERVAL,
                        default=str(current_device_interval),
                    ): vol.In(device_interval_options),
                    vol.Required(
                        CONF_ENERGY_SCAN_INTERVAL,
                        default=str(current_energy_interval),
                    ): vol.In(energy_interval_options),
                }
            ),
        )
