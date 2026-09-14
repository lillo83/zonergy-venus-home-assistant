"""Read-only client for the Zonergy cloud API used by the official app."""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout

from .const import CLOUD_BASE_URL, CLOUD_REALTIME_INTERVAL, CLOUD_SCAN_INTERVAL


class ZonergyCloudError(Exception):
    """Base error raised by the Zonergy cloud client."""


class ZonergyCloudAuthError(ZonergyCloudError):
    """Raised when Zonergy rejects the account credentials."""


class ZonergyCloudConnectionError(ZonergyCloudError):
    """Raised when the Zonergy service cannot be reached."""


@dataclass(frozen=True, slots=True)
class ZonergyCloudDevice:
    """One inverter discovered in a Zonergy account."""

    plant_id: str
    plant_name: str
    device_id: str
    serial_number: str
    model: str
    realtime_id: str
    raw: dict[str, Any]


class ZonergyCloudApi:
    """Minimal, read-only implementation of the official app API."""

    def __init__(
        self,
        session: ClientSession,
        *,
        account: str,
        password: str,
        base_url: str = CLOUD_BASE_URL,
    ) -> None:
        self._session = session
        self._account = account
        self._password = password
        self._base_url = base_url.rstrip("/")
        self._auth: str | None = None
        self._cookies: dict[str, str] = {}
        self._last_realtime_request = 0.0
        self._realtime_available: bool | None = None
        self._realtime_data: dict[str, Any] = {}
        self._realtime_data_time = 0.0

    async def async_login(self) -> None:
        """Authenticate using the same renewal flow as the official app."""
        key_response = await self._request(
            "GET", "/dsweb/index/loginkey", authenticated=False
        )
        login_key = key_response.get("data")
        if not isinstance(login_key, str) or not login_key:
            raise ZonergyCloudConnectionError("The service returned no login key")

        # MD5 is required by the vendor protocol and combined with a temporary
        # per-session key before transmission.
        md5_password = hashlib.md5(self._password.encode()).hexdigest()
        obfuscated_password = "".join(
            chr(ord(char) ^ ord(login_key[index % len(login_key)]))
            for index, char in enumerate(md5_password)
        )
        first_sha = hashlib.sha256(self._password.encode()).hexdigest()
        double_sha = hashlib.sha256(first_sha.encode()).hexdigest()

        response = await self._request(
            "POST",
            "/dsweb/index/login",
            authenticated=False,
            json={
                "account": self._account,
                "password": obfuscated_password,
                "new_pass": double_sha,
                "loginKey": login_key,
                # The official app uses this value when renewing a session.
                "captcha": "9999",
            },
        )
        data = response.get("data")
        auth = data.get("auth") if isinstance(data, dict) else None
        if not isinstance(auth, str) or not auth:
            raise ZonergyCloudAuthError("The service returned no authorization token")
        self._auth = auth

    async def async_discover_devices(self) -> list[ZonergyCloudDevice]:
        """Return all inverters visible to the authenticated account."""
        if self._auth is None:
            await self.async_login()

        now = (
            datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        )
        response = await self._request(
            "GET",
            "/dsweb/plant/plantsList/1/999",
            params={"name": "", "sort": 4, "day": now},
        )
        data = response.get("data")
        plants = data.get("list", []) if isinstance(data, dict) else []

        devices: list[ZonergyCloudDevice] = []
        for plant in plants:
            if not isinstance(plant, dict):
                continue
            plant_id = _first_text(plant, "id", "plant_id")
            if not plant_id:
                continue
            plant_name = _first_text(plant, "name", "plant_name") or "Zonergy"
            device_response = await self._request(
                "GET",
                "/dsweb/device/deviceList/1/999",
                params={"id_plant": plant_id},
            )
            device_data = device_response.get("data")
            rows = device_data.get("list", []) if isinstance(device_data, dict) else []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                device_id = _first_text(row, "id", "device_id")
                if not device_id:
                    continue
                serial = _first_text(row, "inverter_sn", "sn", "device_sn")
                model = _first_text(row, "inverter_model", "model")
                realtime_id = _first_text(row, "device_id")
                devices.append(
                    ZonergyCloudDevice(
                        plant_id=plant_id,
                        plant_name=plant_name,
                        device_id=device_id,
                        serial_number=serial or device_id,
                        model=model or "Venus",
                        realtime_id=realtime_id or serial or device_id,
                        raw=row,
                    )
                )
        return devices

    async def async_device_data(
        self,
        *,
        plant_id: str,
        device_id: str,
        realtime_device_id: str | None = None,
    ) -> dict[str, Any]:
        """Read the current inverter and plant dashboards."""
        device = await self._request(
            "GET",
            "/dsweb/device/deviceDashboard",
            params={"id": device_id},
        )
        plant = await self._request(
            "GET",
            "/dsweb/plant/plantDashboard",
            params={"id": plant_id},
        )
        device_data = device.get("data")
        plant_data = plant.get("data")
        result = dict(plant_data) if isinstance(plant_data, dict) else {}
        if isinstance(device_data, dict):
            result.update(device_data)
        realtime_id = realtime_device_id
        if not realtime_id and isinstance(device_data, dict):
            realtime_id = _first_text(device_data, "device_id", "inverter_sn")
        if (
            realtime_id
            and time.monotonic() - self._last_realtime_request
            >= CLOUD_REALTIME_INTERVAL
        ):
            self._last_realtime_request = time.monotonic()
            realtime = await self._async_realtime_data(realtime_id)
            self._realtime_available = bool(realtime)
            if realtime:
                self._realtime_data = realtime
                self._realtime_data_time = time.monotonic()
        if (
            self._realtime_data
            and time.monotonic() - self._realtime_data_time
            <= CLOUD_REALTIME_INTERVAL + CLOUD_SCAN_INTERVAL
        ):
            result.update(self._realtime_data)
        result["_realtime_available"] = self._realtime_available
        return result

    async def _async_realtime_data(self, device_id: str) -> dict[str, Any]:
        """Try the legacy read-only real-time endpoint used by older app builds."""
        path = f"/dsweb/device/getRealtimeData/{quote(device_id, safe='')}"
        responses = await asyncio.gather(
            self._request("GET", path, params={"battery": 0}, timeout_seconds=8),
            self._request("GET", path, params={"battery": 1}, timeout_seconds=8),
            return_exceptions=True,
        )
        result: dict[str, Any] = {}
        for response in responses:
            if isinstance(response, Exception):
                continue
            result.update(_normalise_realtime_data(response.get("data")))
        return result

    async def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        retry_auth: bool = True,
        timeout_seconds: int = 30,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if authenticated and self._auth is None:
            await self.async_login()

        headers = {"Content-Type": "application/json"}
        if authenticated and self._auth:
            headers["Authorization"] = self._auth
        if self._cookies:
            headers["Cookie"] = "; ".join(
                f"{name}={value}" for name, value in self._cookies.items()
            )

        try:
            response: ClientResponse
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                timeout=ClientTimeout(total=timeout_seconds),
                **kwargs,
            ) as response:
                self._cookies.update(
                    {name: morsel.value for name, morsel in response.cookies.items()}
                )
                if response.status == 401 and authenticated and retry_auth:
                    self._auth = None
                    await self.async_login()
                    return await self._request(
                        method,
                        path,
                        authenticated=True,
                        retry_auth=False,
                        timeout_seconds=timeout_seconds,
                        **kwargs,
                    )
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise ZonergyCloudConnectionError from err

        if not isinstance(payload, dict):
            raise ZonergyCloudConnectionError("Invalid response from Zonergy")
        if payload.get("code") != 0:
            message = str(payload.get("msg") or "Unknown Zonergy error")
            if path.endswith("/login"):
                raise ZonergyCloudAuthError(message)
            raise ZonergyCloudError(message)
        return payload


def _first_text(data: dict[str, Any], *keys: str) -> str:
    """Return the first present identifier as text."""
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return str(value)
    return ""


def _normalise_realtime_data(data: Any) -> dict[str, Any]:
    """Convert supported real-time response shapes to a value dictionary."""
    if isinstance(data, dict):
        return data
    if not isinstance(data, list):
        return {}
    result: dict[str, Any] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        key = _first_text(item, "key", "name", "register")
        if key and "value" in item:
            result[key] = item["value"]
    return result
