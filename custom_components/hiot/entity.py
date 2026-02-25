"""Base entity for HT HomeService integration."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_CATEGORY_MAP, DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from .coordinator import HiotDataUpdateCoordinator


class HiotEntity(CoordinatorEntity["HiotDataUpdateCoordinator"]):
    """Base class for HT HomeService entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HiotDataUpdateCoordinator,
        device_id: str,
        device_name: str,
        device_type: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._device_type = device_type
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_type}_{device_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.config_entry.entry_id}_{self._device_id}")},
            name=self._device_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get device data from coordinator."""
        category = DEVICE_CATEGORY_MAP.get(self._device_type)
        if category and self.coordinator.data:
            category_data = self.coordinator.data.get(category, {})
            if isinstance(category_data, dict):
                return category_data.get(self._device_id)
        return None

    def _get_status_value(self, command: str) -> str | None:
        """Get a specific status value from device data."""
        device_data = self._get_device_data()
        if not device_data:
            return None

        for status in device_data.get("statusList", []):
            if status.get("command") == command:
                value = status.get("value")
                return str(value) if value is not None else None
        return None
