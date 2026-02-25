# pyright: reportMissingImports=false

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from custom_components.hiot.const import DOMAIN
from custom_components.hiot.coordinator import HiotDataUpdateCoordinator
from custom_components.hiot.light import HiotLight, async_setup_entry


async def test_light_setup_entry_creates_entities(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator._devices = [
        {"deviceId": "light001", "deviceType": "light", "deviceName": "거실 조명"},
        {"deviceId": "fan001", "deviceType": "fan", "deviceName": "환기"},
    ]
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = {"coordinator": coordinator}

    add_entities = MagicMock()
    await async_setup_entry(hass, mock_config_entry, add_entities)

    entities = add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], HiotLight)


async def test_light_state_and_controls(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.data = {
        "lights": {
            "light001": {"statusList": [{"command": "power", "value": "on"}]},
        }
    }
    coordinator.async_request_refresh = AsyncMock()

    entity = HiotLight(coordinator, "light001", "거실 조명", "light")

    assert entity.is_on is True

    await entity.async_turn_off()
    mock_api_client.async_control_device.assert_awaited_with(
        "lights",
        "light001",
        [{"command": "power", "value": "off"}],
    )

    await entity.async_turn_on()
    mock_api_client.async_control_device.assert_awaited_with(
        "lights",
        "light001",
        [{"command": "power", "value": "on"}],
    )
