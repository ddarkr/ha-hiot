# pyright: reportMissingImports=false

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.hiot.api import HiotAuthError, HiotConnectionError
from custom_components.hiot.const import DOMAIN


async def test_user_step_shows_form(hass) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_user_step_valid_single_danji_creates_entry(hass) -> None:
    mock_client = AsyncMock()
    mock_client.async_login = AsyncMock()
    mock_client.async_get_households = AsyncMock(
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

    with (
        patch.object(hass.config_entries, "async_setup", AsyncMock(return_value=True)),
        patch("custom_components.hiot.config_flow.async_create_clientsession"),
        patch("custom_components.hiot.config_flow.HiotApiClient", return_value=mock_client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={CONF_USERNAME: "testuser", CONF_PASSWORD: "testpass"},
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "Test Apartment (101동 1201호)"
    assert result["data"][CONF_USERNAME] == "testuser"
    assert result["data"]["site_id"] == "site001"


async def test_user_step_valid_multiple_danji_goes_to_select_step(hass) -> None:
    mock_client = AsyncMock()
    mock_client.async_login = AsyncMock()
    mock_client.async_get_households = AsyncMock(
        return_value=[
            {"siteId": "site001", "siteName": "Apt A", "dong": "101", "ho": "1201"},
            {"siteId": "site002", "siteName": "Apt B", "dong": "102", "ho": "1301"},
        ]
    )

    with (
        patch.object(hass.config_entries, "async_setup", AsyncMock(return_value=True)),
        patch("custom_components.hiot.config_flow.async_create_clientsession"),
        patch("custom_components.hiot.config_flow.HiotApiClient", return_value=mock_client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={CONF_USERNAME: "testuser", CONF_PASSWORD: "testpass"},
        )

    assert result["type"] == "form"
    assert result["step_id"] == "select_danji"


async def test_user_step_invalid_auth_error(hass) -> None:
    mock_client = AsyncMock()
    mock_client.async_login = AsyncMock(side_effect=HiotAuthError("bad creds"))

    with (
        patch.object(hass.config_entries, "async_setup", AsyncMock(return_value=True)),
        patch("custom_components.hiot.config_flow.async_create_clientsession"),
        patch("custom_components.hiot.config_flow.HiotApiClient", return_value=mock_client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={CONF_USERNAME: "testuser", CONF_PASSWORD: "wrong"},
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_step_cannot_connect_error(hass) -> None:
    mock_client = AsyncMock()
    mock_client.async_login = AsyncMock(side_effect=HiotConnectionError("network"))

    with (
        patch("custom_components.hiot.async_setup_entry", return_value=True),
        patch("custom_components.hiot.config_flow.async_create_clientsession"),
        patch("custom_components.hiot.config_flow.HiotApiClient", return_value=mock_client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={CONF_USERNAME: "testuser", CONF_PASSWORD: "testpass"},
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_step_no_danji_error(hass) -> None:
    mock_client = AsyncMock()
    mock_client.async_login = AsyncMock()
    mock_client.async_get_households = AsyncMock(return_value=[])

    with (
        patch.object(hass.config_entries, "async_setup", AsyncMock(return_value=True)),
        patch("custom_components.hiot.config_flow.async_create_clientsession"),
        patch("custom_components.hiot.config_flow.HiotApiClient", return_value=mock_client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={CONF_USERNAME: "testuser", CONF_PASSWORD: "testpass"},
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "no_danji"}


async def test_select_danji_step_creates_entry(hass) -> None:
    mock_client = AsyncMock()
    mock_client.async_login = AsyncMock()
    mock_client.async_get_households = AsyncMock(
        return_value=[
            {
                "siteId": "site001",
                "siteName": "Apt A",
                "dong": "101",
                "ho": "1201",
                "homepageDomain": "a.example.com",
            },
            {
                "siteId": "site002",
                "siteName": "Apt B",
                "dong": "102",
                "ho": "1301",
                "homepageDomain": "b.example.com",
            },
        ]
    )

    with (
        patch.object(hass.config_entries, "async_setup", AsyncMock(return_value=True)),
        patch("custom_components.hiot.config_flow.async_create_clientsession"),
        patch("custom_components.hiot.config_flow.HiotApiClient", return_value=mock_client),
    ):
        first = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={CONF_USERNAME: "testuser", CONF_PASSWORD: "testpass"},
        )
        result = await hass.config_entries.flow.async_configure(
            first["flow_id"],
            user_input={"danji": "1"},
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "Apt B (102동 1301호)"
    assert result["data"]["site_id"] == "site002"


async def test_reauth_flow(hass, mock_config_entry) -> None:
    mock_config_entry.add_to_hass(hass)

    mock_client = AsyncMock()
    mock_client.async_login = AsyncMock()

    with (
        patch.object(hass.config_entries, "async_reload", AsyncMock(return_value=True)),
        patch.object(hass.config_entries, "async_setup", AsyncMock(return_value=True)),
        patch("custom_components.hiot.config_flow.async_create_clientsession"),
        patch("custom_components.hiot.config_flow.HiotApiClient", return_value=mock_client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "reauth", "entry_id": mock_config_entry.entry_id},
            data=mock_config_entry.data,
        )

        assert result["type"] == "form"
        assert result["step_id"] == "reauth_confirm"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PASSWORD: "newpass"},
        )

    assert result2["type"] == "abort"
    assert result2["reason"] == "reauth_successful"
