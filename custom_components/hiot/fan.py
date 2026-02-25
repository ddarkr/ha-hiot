# pyright: reportMissingTypeArgument=false, reportIncompatibleVariableOverride=false
"""Fan platform for HT HomeService."""
from __future__ import annotations


from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import CATEGORY_FAN, DOMAIN
from .coordinator import HiotDataUpdateCoordinator
from .entity import HiotEntity


def _build_device_name(device: dict, fallback_prefix: str) -> str:
    """Build a device name including location for uniqueness."""
    name = device.get("deviceName", f"{fallback_prefix} {device.get('deviceId', '')}")
    location = device.get("deviceLocation", "")
    if location:
        return f"{name} {location}"
    return name
ORDERED_NAMED_FAN_SPEEDS = ["light", "mid", "pow"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HiotDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [
        HiotFan(
            coordinator,
            device["deviceId"],
            _build_device_name(device, "Fan"),
            "fan",
        )
        for device in coordinator.devices
        if device.get("deviceType") == "fan"
    ]
    async_add_entities(entities)


class HiotFan(HiotEntity, FanEntity):
    """Representation of a HT HomeService ventilation fan."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = len(ORDERED_NAMED_FAN_SPEEDS)

    @property
    def is_on(self) -> bool | None:
        value = self._get_status_value("power")
        if value is None:
            return None
        return value == "on"

    @property
    def percentage(self) -> int | None:
        if not self.is_on:
            return 0
        wind = self._get_status_value("wind")
        if wind is None or wind == "stop":
            return 0
        if wind in ORDERED_NAMED_FAN_SPEEDS:
            return ordered_list_item_to_percentage(ORDERED_NAMED_FAN_SPEEDS, wind)
        return None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        commands = [{"command": "power", "value": "on"}]
        if percentage is not None and percentage > 0:
            wind = percentage_to_ordered_list_item(ORDERED_NAMED_FAN_SPEEDS, percentage)
            commands.append({"command": "wind", "value": wind})
        await self.coordinator.api_client.async_control_device(
            CATEGORY_FAN,
            self._device_id,
            commands,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api_client.async_control_device(
            CATEGORY_FAN,
            self._device_id,
            [{"command": "power", "value": "off"}],
        )
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        wind = percentage_to_ordered_list_item(ORDERED_NAMED_FAN_SPEEDS, percentage)
        commands = [
            {"command": "power", "value": "on"},
            {"command": "wind", "value": wind},
        ]
        await self.coordinator.api_client.async_control_device(
            CATEGORY_FAN,
            self._device_id,
            commands,
        )
        await self.coordinator.async_request_refresh()
