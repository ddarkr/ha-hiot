# pyright: reportMissingTypeArgument=false, reportIncompatibleVariableOverride=false
"""Switch platform for HT HomeService."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CATEGORY_GAS, CATEGORY_WALLSOCKET, DOMAIN
from .coordinator import HiotDataUpdateCoordinator
from .entity import HiotEntity

_LOGGER = logging.getLogger(__name__)


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
    coordinator: HiotDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SwitchEntity] = []

    for device in coordinator.devices:
        device_type = device.get("deviceType")
        device_id = device["deviceId"]
        name = _build_device_name(device, device_type or "Switch")

        if device_type == "gas":
            entities.append(HiotGasValve(coordinator, device_id, name, "gas"))
        elif device_type == "wallsocket":
            entities.append(HiotWallSocket(coordinator, device_id, name, "wallsocket"))

    async_add_entities(entities)


class HiotGasValve(HiotEntity, SwitchEntity):
    """Representation of a HT HomeService gas valve."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:valve"

    @property
    def is_on(self) -> bool | None:
        value = self._get_status_value("power")
        if value is None:
            return None
        return value == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on is not supported for safety. Log warning."""
        _LOGGER.warning(
            "Turning on gas valve remotely is not supported for safety reasons"
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Shut off the gas valve."""
        await self.coordinator.api_client.async_control_device(
            CATEGORY_GAS,
            self._device_id,
            [{"command": "power", "value": "off"}],
        )
        await self.coordinator.async_request_refresh()


class HiotWallSocket(HiotEntity, SwitchEntity):
    """Representation of a HT HomeService standby power outlet."""

    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_icon = "mdi:power-socket-eu"

    @property
    def is_on(self) -> bool | None:
        value = self._get_status_value("power")
        if value is None:
            return None
        return value == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the outlet."""
        await self.coordinator.api_client.async_control_device(
            CATEGORY_WALLSOCKET,
            self._device_id,
            [{"command": "power", "value": "on"}],
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the outlet (cut standby power)."""
        await self.coordinator.api_client.async_control_device(
            CATEGORY_WALLSOCKET,
            self._device_id,
            [{"command": "power", "value": "off"}],
        )
        await self.coordinator.async_request_refresh()
