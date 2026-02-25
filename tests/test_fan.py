# pyright: reportMissingImports=false

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.util.percentage import ordered_list_item_to_percentage

from custom_components.hiot.const import DOMAIN
from custom_components.hiot.coordinator import HiotDataUpdateCoordinator
from custom_components.hiot.fan import HiotFan, ORDERED_NAMED_FAN_SPEEDS, async_setup_entry


async def test_fan_setup_entry_creates_entities(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator._devices = [
        {"deviceId": "fan001", "deviceType": "fan", "deviceName": "환기"},
        {"deviceId": "light001", "deviceType": "light", "deviceName": "조명"},
    ]
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = {"coordinator": coordinator}

    add_entities = MagicMock()
    await async_setup_entry(hass, mock_config_entry, add_entities)

    entities = add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], HiotFan)


async def test_fan_state_and_controls(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.data = {
        "fans": {
            "fan001": {
                "statusList": [
                    {"command": "power", "value": "on"},
                    {"command": "wind", "value": "mid"},
                ]
            }
        }
    }
    coordinator.async_request_refresh = AsyncMock()

    entity = HiotFan(coordinator, "fan001", "환기", "fan")

    assert entity.is_on is True
    assert entity.percentage == ordered_list_item_to_percentage(ORDERED_NAMED_FAN_SPEEDS, "mid")

    await entity.async_turn_on(percentage=100)
    mock_api_client.async_control_device.assert_awaited_with(
        "fans",
        "fan001",
        [{"command": "power", "value": "on"}, {"command": "wind", "value": "pow"}],
    )

    await entity.async_set_percentage(33)
    mock_api_client.async_control_device.assert_awaited_with(
        "fans",
        "fan001",
        [{"command": "power", "value": "on"}, {"command": "wind", "value": ORDERED_NAMED_FAN_SPEEDS[0]}],
    )

    await entity.async_turn_off()
    mock_api_client.async_control_device.assert_awaited_with(
        "fans",
        "fan001",
        [{"command": "power", "value": "off"}],
    )
