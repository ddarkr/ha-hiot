# pyright: reportMissingImports=false

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

from custom_components.hiot.const import DOMAIN
from custom_components.hiot.coordinator import HiotDataUpdateCoordinator
from custom_components.hiot.switch import HiotGasValve, HiotWallSocket, async_setup_entry


async def test_switch_setup_entry_creates_entities(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator._devices = [
        {"deviceId": "gas001", "deviceType": "gas", "deviceName": "가스 밸브"},
        {"deviceId": "fan001", "deviceType": "fan", "deviceName": "환기"},
        {"deviceId": "ws001", "deviceType": "wallsocket", "deviceName": "대기전력", "deviceLocation": "거실1"},
    ]
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = {"coordinator": coordinator}

    add_entities = MagicMock()
    await async_setup_entry(hass, mock_config_entry, add_entities)

    entities = add_entities.call_args[0][0]
    assert len(entities) == 2
    assert any(isinstance(entity, HiotGasValve) for entity in entities)
    assert any(isinstance(entity, HiotWallSocket) for entity in entities)


async def test_switch_state_and_turn_off(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.data = {
        "gases": {
            "gas001": {"statusList": [{"command": "power", "value": "on"}]},
        }
    }
    coordinator.async_request_refresh = AsyncMock()

    entity = HiotGasValve(coordinator, "gas001", "가스 밸브", "gas")

    assert entity.is_on is True

    await entity.async_turn_off()
    mock_api_client.async_control_device.assert_awaited_with(
        "gases",
        "gas001",
        [{"command": "power", "value": "off"}],
    )


async def test_switch_turn_on_logs_warning_and_does_not_call_api(
    hass, mock_config_entry, mock_api_client, caplog
) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.async_request_refresh = AsyncMock()
    entity = HiotGasValve(coordinator, "gas001", "가스 밸브", "gas")

    caplog.set_level(logging.WARNING)

    await entity.async_turn_on()

    assert "not supported for safety reasons" in caplog.text
    mock_api_client.async_control_device.assert_not_called()


async def test_wallsocket_state_on_and_off(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.data = {
        "wall-sockets": {
            "ws001": {
                "statusList": [
                    {"command": "power", "value": "on"},
                    {"command": "currentWatt", "value": "5"},
                ]
            },
        }
    }
    coordinator.async_request_refresh = AsyncMock()

    entity = HiotWallSocket(coordinator, "ws001", "대기전력 거실1", "wallsocket")

    assert entity.is_on is True

    await entity.async_turn_off()
    mock_api_client.async_control_device.assert_awaited_with(
        "wall-sockets",
        "ws001",
        [{"command": "power", "value": "off"}],
    )


async def test_wallsocket_turn_on(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.data = {
        "wall-sockets": {
            "ws001": {
                "statusList": [
                    {"command": "power", "value": "off"},
                ]
            },
        }
    }
    coordinator.async_request_refresh = AsyncMock()

    entity = HiotWallSocket(coordinator, "ws001", "대기전력 거실1", "wallsocket")

    assert entity.is_on is False

    await entity.async_turn_on()
    mock_api_client.async_control_device.assert_awaited_with(
        "wall-sockets",
        "ws001",
        [{"command": "power", "value": "on"}],
    )
