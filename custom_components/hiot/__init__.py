"""HT HomeService integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from aiohttp import CookieJar

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import HiotApiClient
from .const import (
    CONF_DEVICE_SCAN_INTERVAL,
    CONF_DONG,
    CONF_ENERGY_SCAN_INTERVAL,
    CONF_HO,
    CONF_SITE_ID,
    DEFAULT_ENERGY_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import HiotDataUpdateCoordinator, HiotEnergyCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HT HomeService from a config entry."""
    session = async_create_clientsession(hass, cookie_jar=CookieJar(unsafe=True))
    client = HiotApiClient(session)

    await client.async_login(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    await client.async_get_ctoc_token(
        entry.data[CONF_SITE_ID],
        entry.data[CONF_DONG],
        entry.data[CONF_HO],
    )

    scan_interval = _get_scan_interval(entry)
    coordinator = HiotDataUpdateCoordinator(hass, entry, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    energy_scan_interval = _get_energy_scan_interval(entry)
    energy_coordinator = HiotEnergyCoordinator(hass, entry, client, energy_scan_interval)
    await energy_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "energy_coordinator": energy_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator: HiotDataUpdateCoordinator = entry_data["coordinator"]
        energy_coordinator: HiotEnergyCoordinator = entry_data["energy_coordinator"]
        if energy_coordinator.api_client is coordinator.api_client:
            await coordinator.api_client.async_close()
        else:
            await energy_coordinator.api_client.async_close()
            await coordinator.api_client.async_close()

    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)

    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — adjust coordinator polling interval."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: HiotDataUpdateCoordinator = data["coordinator"]
    energy_coordinator: HiotEnergyCoordinator = data["energy_coordinator"]

    coordinator.update_interval = _get_scan_interval(entry)
    energy_coordinator.update_interval = _get_energy_scan_interval(entry)

    _LOGGER.debug(
        "Scan intervals updated: device=%s, energy=%s",
        coordinator.update_interval,
        energy_coordinator.update_interval,
    )
def _get_scan_interval(entry: ConfigEntry) -> timedelta:
    """Get scan interval from options, falling back to default."""
    seconds = int(entry.options.get(
        CONF_DEVICE_SCAN_INTERVAL,
        entry.options.get("scan_interval", int(DEFAULT_SCAN_INTERVAL.total_seconds()))
    ))
    return timedelta(seconds=seconds)


def _get_energy_scan_interval(entry: ConfigEntry) -> timedelta:
    """Get energy scan interval from options, falling back to default."""
    seconds = int(entry.options.get(
        CONF_ENERGY_SCAN_INTERVAL, int(DEFAULT_ENERGY_SCAN_INTERVAL.total_seconds())
    ))
    return timedelta(seconds=seconds)
