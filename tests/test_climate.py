# pyright: reportMissingImports=false

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE

from custom_components.hiot.climate import HiotAircon, HiotHeater, async_setup_entry
from custom_components.hiot.const import DOMAIN
from custom_components.hiot.coordinator import HiotDataUpdateCoordinator


async def test_climate_setup_entry_creates_heater_and_aircon(
    hass, mock_config_entry, mock_api_client
) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator._devices = [
        {"deviceId": "heat001", "deviceType": "heating", "deviceName": "난방"},
        {"deviceId": "air001", "deviceType": "aircon", "deviceName": "에어컨"},
        {"deviceId": "light001", "deviceType": "light", "deviceName": "조명"},
    ]
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = {"coordinator": coordinator}

    add_entities = MagicMock()
    await async_setup_entry(hass, mock_config_entry, add_entities)

    entities = add_entities.call_args[0][0]
    assert len(entities) == 2
    assert any(isinstance(entity, HiotHeater) for entity in entities)
    assert any(isinstance(entity, HiotAircon) for entity in entities)


async def test_heater_state_and_controls(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.data = {
        "heaters": {
            "heat001": {
                "statusList": [
                    {"command": "power", "value": "on"},
                    {"command": "currTemperature", "value": "22"},
                    {"command": "setTemperature", "value": "24"},
                ]
            }
        }
    }
    coordinator.async_request_refresh = AsyncMock()

    entity = HiotHeater(coordinator, "heat001", "난방", "heating")

    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.current_temperature == 22.0
    assert entity.target_temperature == 24.0

    await entity.async_set_hvac_mode(HVACMode.OFF)
    mock_api_client.async_control_device.assert_awaited_with(
        "heaters",
        "heat001",
        [{"command": "power", "value": "off"}],
    )

    await entity.async_set_temperature(**{ATTR_TEMPERATURE: 26})
    mock_api_client.async_control_device.assert_awaited_with(
        "heaters",
        "heat001",
        [{"command": "setTemperature", "value": "26"}],
    )


async def test_aircon_state_and_controls(hass, mock_config_entry, mock_api_client) -> None:
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.data = {
        "aircons": {
            "air001": {
                "statusList": [
                    {"command": "power", "value": "on"},
                    {"command": "mode", "value": "cool"},
                    {"command": "wind", "value": "mid"},
                    {"command": "currTemperature", "value": "25"},
                    {"command": "setTemperature", "value": "23"},
                ]
            }
        }
    }
    coordinator.async_request_refresh = AsyncMock()

    entity = HiotAircon(coordinator, "air001", "에어컨", "aircon")

    assert entity.hvac_mode == HVACMode.COOL
    assert entity.fan_mode == "medium"
    assert entity.current_temperature == 25.0
    assert entity.target_temperature == 23.0

    await entity.async_set_hvac_mode(HVACMode.OFF)
    mock_api_client.async_control_device.assert_awaited_with(
        "aircons",
        "air001",
        [{"command": "power", "value": "off"}],
    )

    await entity.async_set_temperature(**{ATTR_TEMPERATURE: 21})
    mock_api_client.async_control_device.assert_awaited_with(
        "aircons",
        "air001",
        [{"command": "setTemperature", "value": "21"}],
    )


async def test_aircon_hvac_modes(hass, mock_config_entry, mock_api_client) -> None:
    """Test that aircon correctly maps all HVAC modes."""
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.async_request_refresh = AsyncMock()

    # Test heat mode reading
    coordinator.data = {
        "aircons": {
            "air001": {
                "statusList": [
                    {"command": "power", "value": "on"},
                    {"command": "mode", "value": "heat"},
                    {"command": "wind", "value": "auto"},
                ]
            }
        }
    }
    entity = HiotAircon(coordinator, "air001", "에어컨", "aircon")
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.fan_mode == "auto"

    # Test dry mode reading
    coordinator.data = {
        "aircons": {
            "air001": {
                "statusList": [
                    {"command": "power", "value": "on"},
                    {"command": "mode", "value": "dry"},
                    {"command": "wind", "value": "low"},
                ]
            }
        }
    }
    assert entity.hvac_mode == HVACMode.DRY
    assert entity.fan_mode == "low"

    # Test fan_only mode reading
    coordinator.data = {
        "aircons": {
            "air001": {
                "statusList": [
                    {"command": "power", "value": "on"},
                    {"command": "mode", "value": "fan"},
                    {"command": "wind", "value": "high"},
                ]
            }
        }
    }
    assert entity.hvac_mode == HVACMode.FAN_ONLY
    assert entity.fan_mode == "high"

    # Test airwash mode maps to FAN_ONLY
    coordinator.data = {
        "aircons": {
            "air001": {
                "statusList": [
                    {"command": "power", "value": "on"},
                    {"command": "mode", "value": "airwash"},
                    {"command": "wind", "value": "pow"},
                ]
            }
        }
    }
    assert entity.hvac_mode == HVACMode.FAN_ONLY
    assert entity.fan_mode == "turbo"

    # Test light wind maps to low
    coordinator.data = {
        "aircons": {
            "air001": {
                "statusList": [
                    {"command": "power", "value": "on"},
                    {"command": "mode", "value": "cool"},
                    {"command": "wind", "value": "light"},
                ]
            }
        }
    }
    assert entity.hvac_mode == HVACMode.COOL
    assert entity.fan_mode == "low"

    # Test power off always returns OFF regardless of mode
    coordinator.data = {
        "aircons": {
            "air001": {
                "statusList": [
                    {"command": "power", "value": "off"},
                    {"command": "mode", "value": "cool"},
                ]
            }
        }
    }
    assert entity.hvac_mode == HVACMode.OFF


async def test_aircon_set_hvac_mode_sends_power_and_mode(
    hass, mock_config_entry, mock_api_client
) -> None:
    """Test that setting HVAC mode sends both power and mode commands."""
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.data = {"aircons": {"air001": {"statusList": []}}}
    coordinator.async_request_refresh = AsyncMock()

    entity = HiotAircon(coordinator, "air001", "에어컨", "aircon")

    # Setting HEAT should send power=on + mode=heat
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    mock_api_client.async_control_device.assert_awaited_with(
        "aircons",
        "air001",
        [
            {"command": "power", "value": "on"},
            {"command": "mode", "value": "heat"},
        ],
    )

    # Setting DRY should send power=on + mode=dry
    await entity.async_set_hvac_mode(HVACMode.DRY)
    mock_api_client.async_control_device.assert_awaited_with(
        "aircons",
        "air001",
        [
            {"command": "power", "value": "on"},
            {"command": "mode", "value": "dry"},
        ],
    )

    # Setting FAN_ONLY should send power=on + mode=fan
    await entity.async_set_hvac_mode(HVACMode.FAN_ONLY)
    mock_api_client.async_control_device.assert_awaited_with(
        "aircons",
        "air001",
        [
            {"command": "power", "value": "on"},
            {"command": "mode", "value": "fan"},
        ],
    )


async def test_aircon_set_fan_mode(hass, mock_config_entry, mock_api_client) -> None:
    """Test that setting fan mode sends the correct API wind value."""
    coordinator = HiotDataUpdateCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.data = {"aircons": {"air001": {"statusList": []}}}
    coordinator.async_request_refresh = AsyncMock()

    entity = HiotAircon(coordinator, "air001", "에어컨", "aircon")

    await entity.async_set_fan_mode("medium")
    mock_api_client.async_control_device.assert_awaited_with(
        "aircons",
        "air001",
        [{"command": "wind", "value": "mid"}],
    )

    await entity.async_set_fan_mode("low")
    mock_api_client.async_control_device.assert_awaited_with(
        "aircons",
        "air001",
        [{"command": "wind", "value": "low"}],
    )

    await entity.async_set_fan_mode("high")
    mock_api_client.async_control_device.assert_awaited_with(
        "aircons",
        "air001",
        [{"command": "wind", "value": "high"}],
    )

    await entity.async_set_fan_mode("auto")
    mock_api_client.async_control_device.assert_awaited_with(
        "aircons",
        "air001",
        [{"command": "wind", "value": "auto"}],
    )

    await entity.async_set_fan_mode("turbo")
    mock_api_client.async_control_device.assert_awaited_with(
        "aircons",
        "air001",
        [{"command": "wind", "value": "pow"}],
    )
