"""Read-only client for the Zonergy cloud API used by the official app."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from aiohttp import (
    ClientError,
    ClientResponse,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
)

from .const import CLOUD_BASE_URL

LIVE_REGISTER_BLOCKS: tuple[dict[str, int | str], ...] = (
    {"reg": 2100, "func": "04", "len": 3, "typ": "s16"},
    {"reg": 2112, "func": "04", "len": 3, "typ": "s16"},
    {"reg": 2124, "func": "04", "len": 6, "typ": "s16"},
    {"reg": 2148, "func": "04", "len": 21, "typ": "u16"},
    {"reg": 2232, "func": "04", "len": 7, "typ": "u16"},
    {"reg": 2241, "func": "04", "len": 2, "typ": "u16"},
)


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
    register_device_id: str
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
        self._working_register_device_id: str | None = None

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
                register_device_id = _first_text(
                    row, "device_id", "collector_sn", "collectorSn"
                )
                devices.append(
                    ZonergyCloudDevice(
                        plant_id=plant_id,
                        plant_name=plant_name,
                        device_id=device_id,
                        serial_number=serial or device_id,
                        model=model or "Venus",
                        register_device_id=register_device_id or serial or device_id,
                        raw=row,
                    )
                )
        return devices

    async def async_device_data(
        self,
        *,
        plant_id: str,
        device_id: str,
        register_device_id: str | None = None,
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
        candidates = [
            self._working_register_device_id,
            register_device_id,
            _first_text(device_data, "device_id", "collector_sn", "collectorSn")
            if isinstance(device_data, dict)
            else None,
            device_id,
            _first_text(result, "inverter_sn", "sn", "device_sn"),
        ]
        register_ids = list(dict.fromkeys(value for value in candidates if value))
        live_data: dict[str, Any] = {}
        register_error = "No register identifier is available"
        used_register_id = register_ids[0] if register_ids else ""
        errors: list[str] = []
        for candidate in register_ids:
            try:
                live_data, diagnostic = await self._async_read_live_registers(candidate)
            except ZonergyCloudError as err:
                errors.append(f"{candidate}: {err}")
                continue
            if live_data:
                self._working_register_device_id = candidate
                used_register_id = candidate
                register_error = ""
                break
            errors.append(f"{candidate}: {diagnostic}")
        else:
            if errors:
                register_error = "; ".join(errors)
        result.update(live_data)
        result["_register_read_available"] = bool(live_data)
        result["_register_device_id"] = used_register_id
        result["_register_read_error"] = register_error
        return result

    async def _async_read_live_registers(
        self, device_id: str
    ) -> tuple[dict[str, Any], str]:
        """Read live inverter registers through the dongle's cloud bridge."""
        response = await self._request(
            "POST",
            "/dsweb/param/readDeviceData",
            json={"did": device_id, "data": list(LIVE_REGISTER_BLOCKS)},
        )
        data = response.get("data")
        registers = _normalise_register_data(data)
        values = _live_values(registers)
        diagnostic = (
            "No supported registers in "
            f"{type(data).__name__} response ({len(registers)} decoded values)"
        )
        return values, diagnostic

    async def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        retry_auth: bool = True,
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
                timeout=ClientTimeout(total=30),
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
                        **kwargs,
                    )
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except ClientResponseError as err:
            detail = err.message or "request rejected"
            raise ZonergyCloudConnectionError(f"HTTP {err.status} {detail}") from err
        except (ClientError, TimeoutError, ValueError) as err:
            detail = str(err) or type(err).__name__
            raise ZonergyCloudConnectionError(detail) from err

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


def _live_values(registers: dict[str, Any]) -> dict[str, Any]:
    """Convert the Venus live register response to dashboard field names."""

    def raw(address: int) -> int | None:
        value = registers.get(str(address), registers.get(address))
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def s16(address: int) -> int | None:
        value = raw(address)
        if value is None:
            return None
        value &= 0xFFFF
        return value - 0x10000 if value & 0x8000 else value

    def dword(address: int, *, signed: bool) -> int | None:
        high = raw(address)
        low = raw(address + 1)
        if high is None or low is None:
            return None
        value = ((high & 0xFFFF) << 16) | (low & 0xFFFF)
        if signed and value & 0x80000000:
            value -= 0x100000000
        return value

    values: dict[str, Any] = {}

    def put(key: str, value: Any) -> None:
        if value is not None:
            values[key] = value

    put("pv1_input_voltage", _scaled(s16(2100), 0.1))
    put("pv2_input_voltage", _scaled(s16(2101), 0.1))
    put("pv1_input_current", _scaled(s16(2112), 0.01))
    put("pv2_input_current", _scaled(s16(2113), 0.01))
    put("pv1_input_power", dword(2124, signed=True))
    put("pv2_input_power", dword(2126, signed=True))
    put("pv_input_power", dword(2241, signed=False))
    put("today_generation", _scaled(raw(2232), 0.1))
    put("month_generation", _scaled(dword(2233, signed=False), 0.1))
    put("year_generation", _scaled(dword(2235, signed=False), 0.1))
    put("total_generation", _scaled(dword(2237, signed=False), 0.1))
    put("inverter_rad_temp", _scaled(s16(2328), 0.1))
    put("dcdc_rad_temp", _scaled(s16(2329), 0.1))
    put("internal_temp", _scaled(s16(2330), 0.1))
    put("r_grid_voltage", _scaled(s16(2400), 0.1))
    put("r_grid_current", _scaled(s16(2401), 0.01))
    put("r_grid_freq", _scaled(s16(2402), 0.01))
    put("r_active_power", dword(2403, signed=True))
    put("r_load_voltage", _scaled(s16(2445), 0.1))
    put("r_load_current", _scaled(s16(2446), 0.01))
    put("r_load_power", dword(2447, signed=True))
    put("inverter_battery_voltage", _scaled(s16(2967), 0.1))
    put("inverter_battery_current", _scaled(s16(2968), 0.01))
    put("inverter_battery_cd_power", s16(2969))
    put("battery_avg_voltage", _scaled(raw(3004), 0.01))
    put("battery_current", _scaled(s16(3005), 0.01))
    put("battery_soc", raw(3006))
    return values


def _normalise_register_data(data: Any) -> dict[str, Any]:
    """Flatten the register response formats used by different portal builds."""
    registers: dict[str, Any] = {}

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return

        for key, item in value.items():
            if str(key).isdigit() and not isinstance(item, (dict, list)):
                registers[str(key)] = item

        address = value.get("reg", value.get("address", value.get("start")))
        values = value.get("data", value.get("values", value.get("value")))
        try:
            start = int(address) if address is not None else None
        except (TypeError, ValueError):
            start = None
        if start is not None and isinstance(values, list):
            for offset, item in enumerate(values):
                if not isinstance(item, (dict, list)):
                    registers[str(start + offset)] = item
        elif start is not None and not isinstance(values, (dict, list)):
            registers[str(start)] = values

        for key in ("data", "values", "registers", "list", "rows"):
            nested = value.get(key)
            if isinstance(nested, (dict, list)):
                visit(nested)

    visit(data)
    return registers


def _scaled(value: int | None, factor: float) -> float | None:
    """Scale a register value while preserving missing data."""
    return round(value * factor, 3) if value is not None else None
