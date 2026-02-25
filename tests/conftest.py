# pyright: reportMissingImports=false

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

try:
    from tests.common import MockConfigEntry
except ImportError:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hiot.const import (
    CONF_DONG,
    CONF_HO,
    CONF_HOMEPAGE_DOMAIN,
    CONF_SITE_ID,
    CONF_SITE_NAME,
    DOMAIN,
)

MOCK_CONFIG_DATA = {
    CONF_USERNAME: "testuser",
    CONF_PASSWORD: "testpass",
    CONF_SITE_ID: "site001",
    CONF_SITE_NAME: "Test Apartment",
    CONF_DONG: "101",
    CONF_HO: "1201",
    CONF_HOMEPAGE_DOMAIN: "test.hthomeservice.com",
}


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Apartment (101동 1201호)",
        data=MOCK_CONFIG_DATA,
        unique_id="testuser_site001",
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_api_client() -> AsyncMock:
    client = AsyncMock()
    client.async_login = AsyncMock()
    client.async_get_households = AsyncMock(
        return_value=[
            {
                "siteId": "site001",
                "siteName": "Test Apartment",
                "dong": "101",
                "ho": "1201",
                "homepageDomain": "test.hthomeservice.com",
            }
        ]
    )
    client.async_get_ctoc_token = AsyncMock()
    client.async_get_devices = AsyncMock(
        return_value=[
            {"deviceId": "light001", "deviceType": "light", "deviceName": "거실 조명"},
            {"deviceId": "heat001", "deviceType": "heating", "deviceName": "난방"},
            {"deviceId": "air001", "deviceType": "aircon", "deviceName": "에어컨"},
            {"deviceId": "fan001", "deviceType": "fan", "deviceName": "환기"},
            {"deviceId": "gas001", "deviceType": "gas", "deviceName": "가스 밸브"},
            {"deviceId": "ws001", "deviceType": "wallsocket", "deviceName": "대기전력", "deviceLocation": "거실1"},
        ]
    )
    client.async_get_device_state = AsyncMock(
        return_value={"statusList": [{"command": "power", "value": "on"}]}
    )
    client.async_get_all_device_states = AsyncMock(
        return_value={
            "lights": {"light001": {"statusList": [{"command": "power", "value": "on"}]}},
            "heaters": {"heat001": {"statusList": [{"command": "power", "value": "on"}]}},
            "aircons": {"air001": {"statusList": [{"command": "power", "value": "on"}]}},
            "fans": {"fan001": {"statusList": [{"command": "power", "value": "on"}]}},
            "gases": {"gas001": {"statusList": [{"command": "power", "value": "on"}]}},
            "wall-sockets": {"ws001": {"statusList": [{"command": "power", "value": "on"}]}},
        }
    )
    client.async_get_energy_usage = AsyncMock(return_value={"usage": 64400, "sameAreaTypeUsage": 123000})
    client.async_get_energy_fee = AsyncMock(return_value={"fee": 7860})
    client.async_get_energy_goal = AsyncMock(return_value={"goal": 400000})
    client.async_get_all_energy_data = AsyncMock(
        return_value={
            "ELEC": {
                "usage": {"usage": 64400, "sameAreaTypeUsage": 123000},
                "fee": {"fee": 7860},
                "goal": {"goal": 400000},
            },
            "WATER": {
                "usage": {"usage": 22800, "sameAreaTypeUsage": 20000},
                "fee": {"fee": 28500},
                "goal": {"goal": 200000},
            },
            "GAS": {
                "usage": {"usage": 72500, "sameAreaTypeUsage": 60000},
                "fee": {"fee": 0},
                "goal": {"goal": 200000},
            },
        }
    )
    client.async_control_device = AsyncMock(return_value={})
    client.async_close = AsyncMock()
    client.get_category_for_device_type = MagicMock(
        side_effect=lambda t: {
            "light": "lights",
            "heating": "heaters",
            "fan": "fans",
            "gas": "gases",
            "aircon": "aircons",
            "wallsocket": "wall-sockets",
        }.get(t)
    )
    return client
