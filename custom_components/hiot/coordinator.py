"""DataUpdateCoordinator for HT HomeService."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HiotApiClient, HiotApiError, HiotAuthError
from .const import DEFAULT_ENERGY_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HiotDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching data from HT HomeService API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_client: HiotApiClient,
        scan_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=scan_interval,
        )
        self.api_client = api_client
        self._devices: list[dict[str, Any]] = []

    @property
    def devices(self) -> list[dict[str, Any]]:
        """Return cached device list."""
        return self._devices

    async def _async_setup(self) -> None:
        """Set up the coordinator - fetch initial device list."""
        try:
            self._devices = await self.api_client.async_get_devices()
            _LOGGER.debug("Found %d devices", len(self._devices))
        except HiotAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except HiotApiError as err:
            raise UpdateFailed(f"Failed to fetch devices: {err}") from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest state for all devices via single bulk API call."""
        try:
            return await self.api_client.async_get_all_device_states()
        except HiotAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except HiotApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err


class HiotEnergyCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator for energy data (usage, fee, goal)."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_client: HiotApiClient,
        scan_interval: timedelta = DEFAULT_ENERGY_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_energy",
            update_interval=scan_interval,
        )
        self.api_client = api_client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch latest monthly energy usage, fee, and goal data."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            return await self.api_client.async_get_all_energy_data(today)
        except HiotAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except HiotApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
