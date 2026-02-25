# pyright: reportMissingTypeArgument=false, reportIncompatibleVariableOverride=false
"""Light platform for HT HomeService."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CATEGORY_LIGHT, DOMAIN
from .coordinator import HiotDataUpdateCoordinator
from .entity import HiotEntity


def _build_device_name(device: dict, fallback_prefix: str) -> str:
    """Build a device name including location for uniqueness."""
    name = device.get("deviceName", f"{fallback_prefix} {device.get('deviceId', '')}")
    location = device.get("deviceLocation", "")
    if location:
        return f"{name} {location}"
    return name


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HT HomeService lights."""
    coordinator: HiotDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        HiotLight(
            coordinator,
            device["deviceId"],
            _build_device_name(device, "Light"),
            "light",
        )
        for device in coordinator.devices
        if device.get("deviceType") == "light"
    ]

    async_add_entities(entities)


class HiotLight(HiotEntity, LightEntity):
    """Representation of a HT HomeService light."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool | None:
        value = self._get_status_value("power")
        if value is None:
            return None
        return value == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api_client.async_control_device(
            CATEGORY_LIGHT,
            self._device_id,
            [{"command": "power", "value": "on"}],
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api_client.async_control_device(
            CATEGORY_LIGHT,
            self._device_id,
            [{"command": "power", "value": "off"}],
        )
        await self.coordinator.async_request_refresh()
