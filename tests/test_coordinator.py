# pyright: reportMissingImports=false

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hiot.api import HiotApiError, HiotAuthError
from custom_components.hiot.coordinator import HiotDataUpdateCoordinator


async def test_async_setup_fetches_devices(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    mock_api_client.async_get_devices.return_value = [
        {"deviceId": "light001", "deviceType": "light"},
        {"deviceId": "fan001", "deviceType": "fan"},
    ]

    await coordinator._async_setup()

    assert coordinator.devices == [
        {"deviceId": "light001", "deviceType": "light"},
        {"deviceId": "fan001", "deviceType": "fan"},
    ]


async def test_async_update_data_uses_bulk_fetch(
    hass, mock_config_entry, mock_api_client
) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator._devices = [
        {"deviceId": "light001", "deviceType": "light"},
        {"deviceId": "heat001", "deviceType": "heating"},
        {"deviceId": "fan001", "deviceType": "fan"},
    ]

    bulk_result = {
        "lights": {"light001": {"statusList": [{"command": "power", "value": "on"}]}},
        "heaters": {"heat001": {"statusList": [{"command": "power", "value": "off"}]}},
        "fans": {"fan001": {"statusList": [{"command": "power", "value": "on"}]}},
        "gases": {},
        "aircons": {},
        "wall-sockets": {},
    }
    mock_api_client.async_get_all_device_states = AsyncMock(return_value=bulk_result)

    data = await coordinator._async_update_data()

    assert data["lights"]["light001"]["statusList"][0]["value"] == "on"
    assert data["heaters"]["heat001"]["statusList"][0]["value"] == "off"
    assert data["fans"]["fan001"]["statusList"][0]["value"] == "on"
    mock_api_client.async_get_all_device_states.assert_awaited_once()


async def test_async_setup_auth_error_raises_config_entry_auth_failed(
    hass, mock_config_entry, mock_api_client
) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    mock_api_client.async_get_devices.side_effect = HiotAuthError("auth failed")

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_setup()


async def test_async_setup_api_error_raises_update_failed(
    hass, mock_config_entry, mock_api_client
) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    mock_api_client.async_get_devices.side_effect = HiotApiError("api failed")

    with pytest.raises(UpdateFailed):
        await coordinator._async_setup()


async def test_async_update_data_auth_error_raises_config_entry_auth_failed(
    hass, mock_config_entry, mock_api_client
) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    mock_api_client.async_get_all_device_states = AsyncMock(
        side_effect=HiotAuthError("session expired")
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_async_update_data_api_error_raises_update_failed(
    hass, mock_config_entry, mock_api_client
) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    mock_api_client.async_get_all_device_states = AsyncMock(
        side_effect=HiotApiError("server error")
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
