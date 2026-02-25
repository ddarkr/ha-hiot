# pyright: reportIncompatibleVariableOverride=false
"""Sensor platform for HT HomeService."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENERGY_TYPES, MANUFACTURER
from .coordinator import HiotEnergyCoordinator


ENERGY_METRICS = ("usage", "fee", "goal")

METRIC_LABELS = {
    "usage": "사용량",
    "fee": "요금",
    "goal": "목표",
}

METRIC_DATA_FIELDS = {
    "usage": "usage",
    "fee": "fee",
    "goal": "goal",
}

METRIC_ICONS = {
    "usage": {
        "ELEC": "mdi:flash",
        "WATER": "mdi:water",
        "GAS": "mdi:fire",
    },
    "fee": {
        "ELEC": "mdi:cash",
        "WATER": "mdi:cash",
        "GAS": "mdi:cash",
    },
    "goal": {
        "ELEC": "mdi:target",
        "WATER": "mdi:target",
        "GAS": "mdi:target",
    },
}

METRIC_STATE_CLASSES = {
    "usage": SensorStateClass.TOTAL,
    "fee": SensorStateClass.TOTAL,
    "goal": None,
}

ENERGY_LABELS = {
    "ELEC": "전기",
    "WATER": "수도",
    "GAS": "가스",
}

ENERGY_DEVICE_CLASSES = {
    "ELEC": SensorDeviceClass.ENERGY,
    "WATER": SensorDeviceClass.WATER,
    "GAS": SensorDeviceClass.GAS,
}

ENERGY_UNITS = {
    "ELEC": "kWh",
    "WATER": "L",
    "GAS": "m³",
}

ENERGY_CONVERSION_DIVISORS = {
    "ELEC": 1000.0,
    "WATER": 1.0,
    "GAS": 1000.0,
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HT HomeService sensors."""
    coordinator: HiotEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]["energy_coordinator"]
    entities = [
        HiotEnergySensor(coordinator, entry.entry_id, energy_type, metric)
        for energy_type in ENERGY_TYPES
        for metric in ENERGY_METRICS
    ]
    async_add_entities(entities)


class HiotEnergySensor(CoordinatorEntity[HiotEnergyCoordinator], SensorEntity):
    """Energy sensor entity for apartment-level usage and fee data."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HiotEnergyCoordinator,
        entry_id: str,
        energy_type: str,
        metric: str,
    ) -> None:
        """Initialize energy sensor."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._energy_type = energy_type
        self._metric = metric

        energy_key = energy_type.lower()
        energy_label = ENERGY_LABELS[energy_type]

        self._attr_unique_id = f"{entry_id}_energy_{energy_key}_{metric}"
        self._attr_name = f"{energy_label} {METRIC_LABELS[metric]}"
        self._attr_icon = METRIC_ICONS[metric][energy_type]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_energy")},
            name="에너지 모니터링",
            manufacturer=MANUFACTURER,
            model="Energy Monitor",
        )

        if metric == "fee":
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_native_unit_of_measurement = "KRW"
        else:
            self._attr_device_class = ENERGY_DEVICE_CLASSES[energy_type]
            self._attr_native_unit_of_measurement = ENERGY_UNITS[energy_type]

        if METRIC_STATE_CLASSES[metric] is not None:
            self._attr_state_class = METRIC_STATE_CLASSES[metric]

        self._refresh_state_from_coordinator()

    def _get_metric_data(self) -> dict[str, Any]:
        """Return metric data from coordinator cache."""
        if not self.coordinator.data:
            return {}

        type_data = self.coordinator.data.get(self._energy_type)
        if not isinstance(type_data, dict):
            return {}

        metric_data = type_data.get(self._metric)
        if not isinstance(metric_data, dict):
            return {}

        return metric_data

    def _normalize_numeric_value(self, raw_value: Any) -> float | int | None:
        """Convert API raw value to sensor native units."""
        if raw_value is None:
            return None

        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            return None

        if self._metric == "fee":
            return int(numeric_value)

        if self._metric not in ("usage", "goal"):
            return numeric_value

        divisor = ENERGY_CONVERSION_DIVISORS[self._energy_type]
        converted_value = numeric_value / divisor

        if converted_value.is_integer():
            return int(converted_value)

        return round(converted_value, 3)

    def _get_native_value(self) -> float | int | None:
        metric_data = self._get_metric_data()
        data_field = METRIC_DATA_FIELDS[self._metric]
        return self._normalize_numeric_value(metric_data.get(data_field))

    def _get_extra_state_attributes(self) -> dict[str, Any] | None:
        if self._metric != "usage":
            return None

        metric_data = self._get_metric_data()
        same_area_usage = self._normalize_numeric_value(metric_data.get("sameAreaTypeUsage"))
        if same_area_usage is None:
            return None

        return {"sameAreaTypeUsage": same_area_usage}

    def _refresh_state_from_coordinator(self) -> None:
        self._attr_native_value = self._get_native_value()
        extra_attributes = self._get_extra_state_attributes()
        self._attr_extra_state_attributes = extra_attributes or {}

    def _handle_coordinator_update(self) -> None:
        self._refresh_state_from_coordinator()
        self.async_write_ha_state()
