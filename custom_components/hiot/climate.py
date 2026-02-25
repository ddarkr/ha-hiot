# pyright: reportMissingTypeArgument=false, reportIncompatibleVariableOverride=false
"""Climate platform for HT HomeService."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CATEGORY_AIRCON, CATEGORY_HEATER, DOMAIN
from .coordinator import HiotDataUpdateCoordinator
from .entity import HiotEntity

# API mode → HA HVACMode mapping
AIRCON_MODE_MAP: dict[str, HVACMode] = {
    "cool": HVACMode.COOL,
    "heat": HVACMode.HEAT,
    "dry": HVACMode.DRY,
    "fan": HVACMode.FAN_ONLY,
    "airwash": HVACMode.FAN_ONLY,  # airwash mapped to fan_only (closest match)
}

# HA HVACMode → API mode mapping (explicit to avoid airwash overwriting fan)
AIRCON_HA_TO_API: dict[HVACMode, str] = {
    HVACMode.COOL: "cool",
    HVACMode.HEAT: "heat",
    HVACMode.DRY: "dry",
    HVACMode.FAN_ONLY: "fan",
}

# API wind → HA fan mode mapping
AIRCON_WIND_MAP: dict[str, str] = {
    "light": "low",
    "low": "low",
    "mid": "medium",
    "high": "high",
    "pow": "turbo",
    "auto": "auto",
}

# HA fan mode → API wind mapping
AIRCON_FAN_TO_API: dict[str, str] = {v: k for k, v in AIRCON_WIND_MAP.items()}


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
    """Set up HT HomeService climate entities."""
    coordinator: HiotDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[ClimateEntity] = []

    for device in coordinator.devices:
        device_type = device.get("deviceType")
        device_id = device["deviceId"]
        device_name = _build_device_name(device, device_type or "Unknown")

        if device_type == "heating":
            entities.append(HiotHeater(coordinator, device_id, device_name, device_type))
        elif device_type == "aircon":
            entities.append(HiotAircon(coordinator, device_id, device_name, device_type))

    async_add_entities(entities)


class HiotHeater(HiotEntity, ClimateEntity):
    """Representation of a HT HomeService heater (boiler)."""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 5
    _attr_max_temp = 40
    _attr_target_temperature_step = 1

    @property
    def hvac_mode(self) -> HVACMode:
        power = self._get_status_value("power")
        if power == "on":
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        value = self._get_status_value("currTemperature")
        if value is not None:
            try:
                return float(value)
            except ValueError:
                return None
        return None

    @property
    def target_temperature(self) -> float | None:
        value = self._get_status_value("setTemperature")
        if value is not None:
            try:
                return float(value)
            except ValueError:
                return None
        return None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        power_value = "on" if hvac_mode == HVACMode.HEAT else "off"
        await self.coordinator.api_client.async_control_device(
            CATEGORY_HEATER,
            self._device_id,
            [{"command": "power", "value": power_value}],
        )
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.coordinator.api_client.async_control_device(
            CATEGORY_HEATER,
            self._device_id,
            [{"command": "setTemperature", "value": str(int(temperature))}],
        )
        await self.coordinator.async_request_refresh()


class HiotAircon(HiotEntity, ClimateEntity):
    """Representation of a HT HomeService air conditioner."""

    _attr_hvac_modes = [
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.OFF,
    ]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_fan_modes = ["low", "medium", "high", "turbo", "auto"]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 16
    _attr_max_temp = 30
    _attr_target_temperature_step = 1

    @property
    def hvac_mode(self) -> HVACMode:
        power = self._get_status_value("power")
        if power != "on":
            return HVACMode.OFF
        api_mode = self._get_status_value("mode")
        return AIRCON_MODE_MAP.get(api_mode or "", HVACMode.COOL)

    @property
    def fan_mode(self) -> str | None:
        api_wind = self._get_status_value("wind")
        if api_wind is None:
            return None
        return AIRCON_WIND_MAP.get(api_wind, api_wind)

    @property
    def current_temperature(self) -> float | None:
        value = self._get_status_value("currTemperature")
        if value is not None:
            try:
                return float(value)
            except ValueError:
                return None
        return None

    @property
    def target_temperature(self) -> float | None:
        value = self._get_status_value("setTemperature")
        if value is not None:
            try:
                return float(value)
            except ValueError:
                return None
        return None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            commands = [{"command": "power", "value": "off"}]
        else:
            api_mode = AIRCON_HA_TO_API.get(hvac_mode, "cool")
            commands = [
                {"command": "power", "value": "on"},
                {"command": "mode", "value": api_mode},
            ]
        await self.coordinator.api_client.async_control_device(
            CATEGORY_AIRCON,
            self._device_id,
            commands,
        )
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan speed."""
        api_wind = AIRCON_FAN_TO_API.get(fan_mode, fan_mode)
        await self.coordinator.api_client.async_control_device(
            CATEGORY_AIRCON,
            self._device_id,
            [{"command": "wind", "value": api_wind}],
        )
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.coordinator.api_client.async_control_device(
            CATEGORY_AIRCON,
            self._device_id,
            [{"command": "setTemperature", "value": str(int(temperature))}],
        )
        await self.coordinator.async_request_refresh()
