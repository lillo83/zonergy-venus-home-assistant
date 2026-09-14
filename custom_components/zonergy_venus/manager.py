"""ESPHome API connection manager for Zonergy Venus."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from aioesphomeapi import APIClient, ReconnectLogic
from aioesphomeapi.model import DeviceInfo, EntityInfo, EntityState
from homeassistant.core import HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)


class ZonergyVenusManager:
    """Maintain one push connection to the ESPHome RS485 gateway."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        host: str,
        port: int,
        password: str | None,
        encryption_key: str | None,
    ) -> None:
        self.hass = hass
        self.host = host
        self.available = False
        self.device_info: DeviceInfo | None = None
        self.entity_infos: list[EntityInfo] = []
        self.states: dict[tuple[int, int], EntityState] = {}
        self.last_error: Exception | None = None
        self._ready = asyncio.Event()
        self._listeners: set[Callable[[], None]] = set()

        self.client = APIClient(
            host,
            port,
            password=password,
            client_info="Zonergy Venus Home Assistant 0.1.0",
            noise_psk=encryption_key,
        )
        self._reconnect: ReconnectLogic | None = None

    async def async_start(self) -> None:
        """Start reconnect logic and wait for the initial entity list."""
        self._reconnect = ReconnectLogic(
            client=self.client,
            on_connect=self._async_on_connect,
            on_disconnect=self._async_on_disconnect,
            on_connect_error=self._async_on_connect_error,
            zeroconf_instance=None,
            name=None,
        )
        await self._reconnect.start()
        async with asyncio.timeout(20):
            await self._ready.wait()

    async def async_stop(self) -> None:
        """Stop reconnecting and close the API connection."""
        if self._reconnect is not None:
            await self._reconnect.stop()
            self._reconnect = None
        await self.client.disconnect(force=True)
        self.available = False

    async def _async_on_connect(self) -> None:
        """Load metadata and subscribe to live state updates."""
        device_info, entity_infos, _ = await self.client.device_info_and_list_entities()
        self.device_info = device_info
        self.entity_infos = entity_infos
        self.client.subscribe_states(self._on_state)
        self.available = True
        self.last_error = None
        self._ready.set()
        self._notify_listeners()
        _LOGGER.info("Connected to Zonergy gateway %s", self.host)

    async def _async_on_disconnect(self, expected_disconnect: bool) -> None:
        """Mark all entities unavailable while reconnecting."""
        self.available = False
        self._notify_listeners()

    async def _async_on_connect_error(self, err: Exception) -> None:
        """Remember the latest connection error for diagnostics."""
        self.last_error = err
        _LOGGER.debug("Unable to connect to %s: %s", self.host, err)

    @callback
    def _on_state(self, state: EntityState) -> None:
        """Receive one pushed entity state from ESPHome."""
        self.states[(state.device_id, state.key)] = state
        self._notify_listeners()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an entity update listener."""
        self._listeners.add(listener)

        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    @callback
    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    def state_for(self, info: EntityInfo) -> EntityState | None:
        """Return the latest state for an ESPHome entity."""
        return self.states.get((info.device_id, info.key))

    @property
    def device_identifier(self) -> str:
        """Return a stable device identifier."""
        if self.device_info and self.device_info.mac_address:
            return self.device_info.mac_address.replace(":", "").lower()
        return self.host
