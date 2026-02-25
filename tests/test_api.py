# pyright: reportMissingImports=false

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.hiot.api import (
    HiotApiClient,
    HiotApiError,
    HiotAuthError,
    HiotConnectionError,
)
from custom_components.hiot.const import (
    API_BASE_URL,
    PATH_CTOC_TOKEN,
    PATH_DEVICES,
    PATH_DEVICES_WITH_STATUS,
    PATH_EMS_FEE,
    PATH_EMS_USAGE,
    PATH_EMS_USAGE_GOAL,
    PATH_HOUSEHOLD,
    PATH_LOGIN,
)
from custom_components.hiot.crypto import encrypt

_WARMUP_ENCRYPT = encrypt("warmup")


@asynccontextmanager
async def _session():
    connector = aiohttp.TCPConnector(
        enable_cleanup_closed=False,
        resolver=aiohttp.ThreadedResolver(),
    )
    async with aiohttp.ClientSession(connector=connector) as session:
        yield session


async def test_async_login_success() -> None:
    async with _session() as session:
        client = HiotApiClient(session)

        with aioresponses() as mocked:
            mocked.post(f"{API_BASE_URL}/{PATH_LOGIN}", payload={"ok": True}, status=200)

            await client.async_login("testuser", "testpass")

        assert client._authenticated is True


async def test_async_login_auth_error() -> None:
    async with _session() as session:
        client = HiotApiClient(session)

        with aioresponses() as mocked:
            mocked.post(f"{API_BASE_URL}/{PATH_LOGIN}", status=401)

            with pytest.raises(HiotAuthError):
                await client.async_login("testuser", "wrongpass")


async def test_async_login_connection_error() -> None:
    async with _session() as session:
        client = HiotApiClient(session)

        with aioresponses() as mocked:
            mocked.post(
                f"{API_BASE_URL}/{PATH_LOGIN}",
                exception=aiohttp.ClientConnectionError("boom"),
            )

            with pytest.raises(HiotConnectionError):
                await client.async_login("testuser", "testpass")


async def test_async_get_households() -> None:
    async with _session() as session:
        client = HiotApiClient(session)

        with aioresponses() as mocked:
            mocked.get(
                f"{API_BASE_URL}/{PATH_HOUSEHOLD}",
                payload={
                    "resultData": {
                        "danjiList": [
                            {"siteId": "site001", "siteName": "Apt A", "dong": "101", "ho": "1201"}
                        ]
                    }
                },
                status=200,
            )

            households = await client.async_get_households()

        assert households == [{"siteId": "site001", "siteName": "Apt A", "dong": "101", "ho": "1201"}]


async def test_async_get_ctoc_token() -> None:
    async with _session() as session:
        client = HiotApiClient(session)

        with aioresponses() as mocked:
            mocked.post(f"{API_BASE_URL}/{PATH_CTOC_TOKEN}", payload={"ok": True}, status=200)

            await client.async_get_ctoc_token("site001", "101", "1201")

        assert client._site_id == "site001"
        assert client._dong == "101"
        assert client._ho == "1201"


async def test_async_get_devices_supports_list_response() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        payload = [{"deviceId": "light001", "deviceType": "light"}]

        with aioresponses() as mocked:
            mocked.get(f"{API_BASE_URL}/{PATH_DEVICES}", payload=payload, status=200)

            devices = await client.async_get_devices()

        assert devices == payload


async def test_async_get_devices_supports_resultdata_response() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        payload = [{"deviceId": "fan001", "deviceType": "fan"}]

        with aioresponses() as mocked:
            mocked.get(
                f"{API_BASE_URL}/{PATH_DEVICES}",
                payload={"resultData": payload},
                status=200,
            )

            devices = await client.async_get_devices()

        assert devices == payload


async def test_async_get_devices_supports_data_response() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        payload = [{"deviceId": "gas001", "deviceType": "gas"}]

        with aioresponses() as mocked:
            mocked.get(
                f"{API_BASE_URL}/{PATH_DEVICES}",
                payload={"data": payload},
                status=200,
            )

            devices = await client.async_get_devices()

        assert devices == payload


async def test_async_get_device_state() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        url = f"{API_BASE_URL}/proxy/ctoc/lights/light001"

        with aioresponses() as mocked:
            mocked.get(
                url,
                payload={"resultData": {"statusList": [{"command": "power", "value": "on"}]}},
                status=200,
            )

            state = await client.async_get_device_state("lights", "light001")

        assert state == {"statusList": [{"command": "power", "value": "on"}]}


async def test_async_control_device() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        url = f"{API_BASE_URL}/proxy/ctoc/lights/light001"

        with aioresponses() as mocked:
            mocked.put(url, payload={"ok": True}, status=200)

            result = await client.async_control_device(
                "lights",
                "light001",
                [{"command": "power", "value": "off"}],
            )

        assert result == {"ok": True}


async def test_auto_reauth_on_401_response() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        client._authenticated = True
        client._username = "testuser"
        client._password = "testpass"

        devices_url = f"{API_BASE_URL}/{PATH_DEVICES}"
        login_url = f"{API_BASE_URL}/{PATH_LOGIN}"

        with aioresponses() as mocked:
            mocked.get(devices_url, status=401)
            mocked.post(login_url, payload={"ok": True}, status=200)
            mocked.get(devices_url, payload=[{"deviceId": "light001", "deviceType": "light"}], status=200)

            devices = await client.async_get_devices()

        assert devices == [{"deviceId": "light001", "deviceType": "light"}]
        assert client._authenticated is True


async def test_raises_hiot_api_error_for_invalid_json_body() -> None:
    async with _session() as session:
        client = HiotApiClient(session)

        with aioresponses() as mocked:
            mocked.get(f"{API_BASE_URL}/{PATH_DEVICES}", body="not-json", status=200)

            with pytest.raises(HiotApiError):
                await client.async_get_devices()


async def test_async_get_all_device_states_returns_categorized_data() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        url = f"{API_BASE_URL}/{PATH_DEVICES_WITH_STATUS}"
        payload = {
            "data": {
                "deviceList": [
                    {
                        "id": "light001",
                        "deviceType": "light",
                        "deviceName": "거실 조명",
                        "statusList": [{"command": "power", "value": "on"}],
                    },
                    {
                        "id": "heat001",
                        "deviceType": "heating",
                        "deviceName": "난방",
                        "statusList": [{"command": "power", "value": "off"}, {"command": "setTemperature", "value": "25"}],
                    },
                    {
                        "id": "elev001",
                        "deviceType": "elevator",
                        "deviceName": "엘리베이터",
                    },
                ]
            }
        }

        with aioresponses() as mocked:
            mocked.get(url, payload=payload, status=200)

            result = await client.async_get_all_device_states()

        # light and heating are categorized
        assert result["lights"]["light001"]["statusList"] == [{"command": "power", "value": "on"}]
        assert result["heaters"]["heat001"]["statusList"][0]["value"] == "off"
        # elevator is unsupported, should be skipped
        assert "elev001" not in result.get("lights", {})
        # all categories initialized as empty dicts
        assert result["fans"] == {}
        assert result["gases"] == {}
        assert result["aircons"] == {}
        assert result["wall-sockets"] == {}


async def test_async_get_all_device_states_normalizes_id_field() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        url = f"{API_BASE_URL}/{PATH_DEVICES_WITH_STATUS}"
        payload = {
            "data": {
                "deviceList": [
                    {
                        "id": "fan001",
                        "deviceType": "fan",
                        "statusList": [{"command": "power", "value": "on"}],
                    },
                ]
            }
        }

        with aioresponses() as mocked:
            mocked.get(url, payload=payload, status=200)

            result = await client.async_get_all_device_states()

        # 'id' should be normalized to 'deviceId' and used as key
        assert "fan001" in result["fans"]
        assert result["fans"]["fan001"]["statusList"][0]["value"] == "on"


async def test_async_get_energy_usage() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        url = f"{API_BASE_URL}/{PATH_EMS_USAGE}?energyType=ELEC&period=MONTH&date=2025-02-01"

        with aioresponses() as mocked:
            mocked.get(
                url,
                payload={
                    "data": {
                        "usageList": [
                            {
                                "energyType": "ELEC",
                                "usage": 64400,
                                "sameAreaTypeUsage": 123000,
                            }
                        ]
                    }
                },
                status=200,
            )

            result = await client.async_get_energy_usage("ELEC", "2025-02-01")

        assert result["usage"] == 64400
        assert result["sameAreaTypeUsage"] == 123000


async def test_async_get_energy_fee() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        url = f"{API_BASE_URL}/{PATH_EMS_FEE}?energyType=WATER&period=MONTH&date=2025-02-01"

        with aioresponses() as mocked:
            mocked.get(
                url,
                payload={
                    "data": {
                        "feeList": [
                            {
                                "energyType": "WATER",
                                "fee": 28500,
                            }
                        ]
                    }
                },
                status=200,
            )

            result = await client.async_get_energy_fee("WATER", "2025-02-01")

        assert result == {"energyType": "WATER", "fee": 28500}


async def test_async_get_energy_goal() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        url = f"{API_BASE_URL}/{PATH_EMS_USAGE_GOAL}?energyType=GAS&period=MONTH&date=2025-02-01"

        with aioresponses() as mocked:
            mocked.get(
                url,
                payload={
                    "data": {
                        "goalList": [
                            {
                                "energyType": "GAS",
                                "goal": 200000,
                            }
                        ]
                    }
                },
                status=200,
            )

            result = await client.async_get_energy_goal("GAS", "2025-02-01")

        assert result == {"energyType": "GAS", "goal": 200000}


async def test_async_get_all_energy_data_allows_partial_failures() -> None:
    async with _session() as session:
        client = HiotApiClient(session)
        client.async_get_energy_usage = AsyncMock(
            side_effect=[
                {"usage": 64400},
                HiotApiError("usage fail"),
                {"usage": 72500},
            ]
        )
        client.async_get_energy_fee = AsyncMock(
            side_effect=[
                {"fee": 7860},
                {"fee": 28500},
                HiotApiError("fee fail"),
            ]
        )
        client.async_get_energy_goal = AsyncMock(
            side_effect=[
                {"goal": 400000},
                {"goal": 200000},
                {"goal": 200000},
            ]
        )

        result = await client.async_get_all_energy_data("2025-02-01")

    assert result["ELEC"]["usage"] == {"usage": 64400}
    assert result["ELEC"]["fee"] == {"fee": 7860}
    assert result["ELEC"]["goal"] == {"goal": 400000}
    assert result["WATER"]["usage"] == {}
    assert result["WATER"]["fee"] == {"fee": 28500}
    assert result["WATER"]["goal"] == {"goal": 200000}
    assert result["GAS"]["usage"] == {"usage": 72500}
    assert result["GAS"]["fee"] == {}
    assert result["GAS"]["goal"] == {"goal": 200000}
