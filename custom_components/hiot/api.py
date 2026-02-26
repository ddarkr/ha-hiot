"""API client for HT HomeService."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    DEVICE_CATEGORY_MAP,
    ENERGY_TYPES,
    PATH_CTOC_TOKEN,
    PATH_DEVICES,
    PATH_DEVICES_WITH_STATUS,
    PATH_EMS_FEE,
    PATH_EMS_USAGE,
    PATH_EMS_USAGE_GOAL,
    PATH_HOUSEHOLD,
    PATH_LOGIN,
)
from .crypto import encrypt

_LOGGER = logging.getLogger(__name__)

MAX_AUTH_RETRY_ATTEMPTS = 10
MAX_AUTH_RETRY_DELAY_SECONDS = 10


class HiotApiError(Exception):
    """Base exception for HT HomeService API."""


class HiotAuthError(HiotApiError):
    """Authentication error."""


class HiotConnectionError(HiotApiError):
    """Connection error."""


class HiotApiClient:
    """Async API client for HT HomeService."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._base_url = API_BASE_URL
        self._authenticated = False
        self._username: str | None = None
        self._password: str | None = None
        self._site_id: str | None = None
        self._dong: str | None = None
        self._ho: str | None = None
        self._auth_lock = asyncio.Lock()

    async def async_login(self, username: str, password: str) -> None:
        """Login with encrypted credentials."""
        self._username = username
        self._password = password

        encrypted_id = encrypt(username)
        encrypted_pw = encrypt(password)

        await self._async_request(
            "POST",
            PATH_LOGIN,
            json={"id": encrypted_id, "password": encrypted_pw, "rememberMe": False},
            require_auth=False,
        )
        self._authenticated = True
        _LOGGER.debug("Login successful")

    async def async_get_households(self) -> list[dict[str, Any]]:
        """Get list of apartment complexes (danji)."""
        data = await self._async_request("GET", PATH_HOUSEHOLD)
        return data.get("resultData", {}).get("danjiList", [])

    async def async_get_ctoc_token(self, site_id: str, dong: str, ho: str) -> None:
        """Get CTOC token for specific apartment."""
        self._site_id = site_id
        self._dong = dong
        self._ho = ho

        await self._async_request(
            "POST",
            PATH_CTOC_TOKEN,
            json={
                "siteId": site_id,
                "dong": dong,
                "ho": ho,
                "clientId": "HT-WEB",
                "uuid": "",
            },
        )
        _LOGGER.debug("CTOC token acquired for site %s", site_id)

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Get all devices."""
        data = await self._async_request("GET", PATH_DEVICES)
        return self._parse_device_list(data)

    @staticmethod
    def _parse_device_list(data: Any) -> list[dict[str, Any]]:
        """Parse device list from various API response formats."""
        device_list: list[dict[str, Any]] = []

        if isinstance(data, list):
            device_list = data
        elif isinstance(data, dict):
            # Actual API: {"data": {"deviceList": [...]}}
            nested_data = data.get("data")
            if isinstance(nested_data, dict):
                device_list = nested_data.get("deviceList", [])
            elif isinstance(nested_data, list):
                device_list = nested_data
            else:
                result_data = data.get("resultData")
                if isinstance(result_data, list):
                    device_list = result_data

        # Normalize: API returns 'id' but we use 'deviceId' internally
        for device in device_list:
            if "deviceId" not in device and "id" in device:
                device["deviceId"] = device["id"]

        return device_list

    async def async_get_all_device_states(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Get all devices with their current status in a single API call.

        Returns a nested dict: {category: {device_id: device_data}}.
        Each device_data contains at least 'statusList'.
        """
        data = await self._async_request("GET", PATH_DEVICES_WITH_STATUS)
        device_list = self._parse_device_list(data)

        result: dict[str, dict[str, dict[str, Any]]] = {}
        for category in DEVICE_CATEGORY_MAP.values():
            result[category] = {}

        for device in device_list:
            device_type = device.get("deviceType", "")
            device_id = device.get("deviceId", "")
            category = DEVICE_CATEGORY_MAP.get(device_type)

            if not category or not device_id:
                continue

            result[category][device_id] = {
                "statusList": device.get("statusList", []),
            }

        return result

    async def async_get_device_state(self, category: str, device_id: str) -> dict[str, Any]:
        """Get state of a specific device."""
        path = f"proxy/ctoc/{category}/{device_id}"
        data = await self._async_request("GET", path)
        if isinstance(data, dict):
            # Actual API: {"data": {"statusList": [...], ...}}
            nested_data = data.get("data")
            if isinstance(nested_data, dict):
                return nested_data
            result_data = data.get("resultData")
            if isinstance(result_data, dict):
                return result_data
            return data
        return {}

    @staticmethod
    def _parse_sortable_date(value: Any) -> datetime | None:
        if not isinstance(value, str):
            return None

        normalized = value.strip()
        if not normalized:
            return None

        for date_format in ("%Y-%m-%d", "%Y-%m", "%Y%m", "%Y%m%d"):
            try:
                return datetime.strptime(normalized, date_format)
            except ValueError:
                continue

        return None

    @classmethod
    def _select_latest_list_item(cls, values: list[Any]) -> dict[str, Any]:
        dict_items = [item for item in values if isinstance(item, dict)]
        if not dict_items:
            return {}
        if len(dict_items) == 1:
            return dict_items[0]

        date_keys = (
            "date",
            "usageDate",
            "feeDate",
            "goalDate",
            "targetDate",
            "yearMonth",
            "ym",
            "month",
        )

        dated_items: list[tuple[datetime, dict[str, Any]]] = []
        for item in dict_items:
            for key in date_keys:
                parsed_date = cls._parse_sortable_date(item.get(key))
                if parsed_date is not None:
                    dated_items.append((parsed_date, item))
                    break

        if dated_items:
            return max(dated_items, key=lambda entry: entry[0])[1]

        return dict_items[0]

    @staticmethod
    def _extract_first_list_item(response: Any, list_key: str) -> dict[str, Any]:
        if not isinstance(response, dict):
            return {}

        data = response.get("data")
        if not isinstance(data, dict):
            return {}

        values = data.get(list_key)
        if not isinstance(values, list) or not values:
            return {}

        return HiotApiClient._select_latest_list_item(values)

    async def async_get_energy_usage(self, energy_type: str, date: str) -> dict[str, Any]:
        """Get energy usage comparison for current month."""
        path = f"{PATH_EMS_USAGE}?energyType={energy_type}&period=MONTH&date={date}"
        response = await self._async_request("GET", path)
        return self._extract_first_list_item(response, "usageList")

    async def async_get_energy_fee(self, energy_type: str, date: str) -> dict[str, Any]:
        """Get energy fee for current month."""
        path = f"{PATH_EMS_FEE}?energyType={energy_type}&period=MONTH&date={date}"
        response = await self._async_request("GET", path)
        return self._extract_first_list_item(response, "feeList")

    async def async_get_energy_goal(self, energy_type: str, date: str) -> dict[str, Any]:
        """Get energy usage goal for current month."""
        path = f"{PATH_EMS_USAGE_GOAL}?energyType={energy_type}&period=MONTH&date={date}"
        response = await self._async_request("GET", path)
        return self._extract_first_list_item(response, "goalList")

    async def async_get_all_energy_data(self, date: str) -> dict[str, dict[str, Any]]:
        """Fetch usage, fee, and goal for all energy types in parallel."""
        request_specs = [
            (energy_type, "usage", self.async_get_energy_usage(energy_type, date))
            for energy_type in ENERGY_TYPES
        ]
        request_specs.extend(
            (energy_type, "fee", self.async_get_energy_fee(energy_type, date))
            for energy_type in ENERGY_TYPES
        )
        request_specs.extend(
            (energy_type, "goal", self.async_get_energy_goal(energy_type, date))
            for energy_type in ENERGY_TYPES
        )

        responses = await asyncio.gather(
            *(request for _, _, request in request_specs),
            return_exceptions=True,
        )

        result: dict[str, dict[str, Any]] = {
            energy_type: {"usage": {}, "fee": {}, "goal": {}}
            for energy_type in ENERGY_TYPES
        }

        for (energy_type, item_type, _), response in zip(request_specs, responses, strict=True):
            if isinstance(response, Exception):
                _LOGGER.error(
                    "Failed to fetch %s data for %s: %s",
                    item_type,
                    energy_type,
                    response,
                )
                continue
            result[energy_type][item_type] = response

        return result

    async def async_control_device(
        self, category: str, device_id: str, commands: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Control a device."""
        path = f"proxy/ctoc/{category}/{device_id}"
        data = await self._async_request(
            "PUT",
            path,
            json={"commandList": commands},
        )
        return data if isinstance(data, dict) else {}

    def get_category_for_device_type(self, device_type: str) -> str | None:
        """Get API category path for a device type."""
        return DEVICE_CATEGORY_MAP.get(device_type)

    async def async_ensure_authenticated(self) -> None:
        """Re-authenticate if needed."""
        async with self._auth_lock:
            if self._authenticated:
                return
            if not self._username or not self._password:
                raise HiotAuthError("No credentials stored for re-authentication")

            await self.async_login(self._username, self._password)
            if self._site_id and self._dong and self._ho:
                await self.async_get_ctoc_token(self._site_id, self._dong, self._ho)

    @staticmethod
    async def _parse_response(resp: aiohttp.ClientResponse) -> Any:
        """Parse response body, handling both JSON and plain text."""
        text = await resp.text()
        if not text:
            return {}
        content_type = resp.content_type or ""
        if "json" in content_type or text.startswith(("{", "[")):
            return await resp.json(content_type=None)
        return {}

    async def _async_request(
        self,
        method: str,
        path: str,
        require_auth: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Make an API request with error handling."""
        url = f"{self._base_url}/{path}"
        auth_retry_attempt = 0

        try:
            while True:
                async with self._session.request(method, url, **kwargs) as resp:
                    if resp.status != 401:
                        resp.raise_for_status()
                        return await self._parse_response(resp)

                    if not require_auth:
                        raise HiotAuthError("Authentication failed")

                self._authenticated = False
                auth_retry_attempt += 1
                if auth_retry_attempt > MAX_AUTH_RETRY_ATTEMPTS:
                    raise HiotAuthError(
                        f"Authentication failed after {MAX_AUTH_RETRY_ATTEMPTS} retries"
                    )

                await self.async_ensure_authenticated()

                retry_delay = min(
                    2 ** (auth_retry_attempt - 1),
                    MAX_AUTH_RETRY_DELAY_SECONDS,
                )
                _LOGGER.warning(
                    "Request unauthorized (401). Retrying auth for %s (attempt %s/%s) in %s seconds",
                    path,
                    auth_retry_attempt,
                    MAX_AUTH_RETRY_ATTEMPTS,
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)
        except aiohttp.ClientError as err:
            raise HiotConnectionError(f"Connection error: {err}") from err
        except HiotApiError:
            raise
        except Exception as err:
            raise HiotApiError(f"Unexpected error: {err}") from err

    async def async_close(self) -> None:
        """Close the session."""
        # Session is managed externally by HA, don't close it here
        self._authenticated = False
