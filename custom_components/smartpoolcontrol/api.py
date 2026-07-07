"""Async client for the Smart Pool Connect REST API.

The vendor migrated from the legacy ``owner.smartpoolcontrol.eu`` Django portal
(which this integration used to scrape) to a modern JSON API at
``api.smartpoolconnect.eu``. Authentication is an API key ("X-API-Key", prefix
``spc_``) which the owner/poolbuilder generates in the web portal under
*API Keys*.

Reading is a single ``GET /pool/{pid}`` returning every module. Control is a
``PATCH /pool/{pid}/{module}`` whose body is the changed field(s) at the top
level -- there is NO ``{"config": ...}`` envelope (that returns HTTP 500) and
the field names do not always mirror the read shape. The exact per-module
payloads were confirmed against the live API:

* ``ph`` / ``cl`` / ``temperature`` accept a partial update, e.g. ``{"target": v}``.
  Note ``cl`` writes ``{"target": v}`` flat even though it reads back under
  ``config.rx.target``.
* ``temperature.frost_protection`` is rejected on its own (HTTP 500); it must be
  sent together with ``target``.
* ``lighting`` accepts ``{"always_active": bool}``.
* ``filter`` is an untagged enum: a partial body never matches a variant
  (HTTP 422), so the *whole* config struct (``always_active`` + ``pump_speed`` +
  ``schedule_1/2/3``) must be read, mutated and sent back.

Momentary actions (cover open/stop/close, backwash, shock, lighting cycle) use a
separate ``POST /pool/{pid}/cmd/{command}`` endpoint. Cover motion is
intentionally NOT implemented here for safety; the cover is read-only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import (
    MODULE_CL,
    MODULE_FILTER,
    MODULE_LIGHTING,
    MODULE_PH,
    MODULE_TEMPERATURE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class PoolStatus:
    """Parsed snapshot of a pool from ``GET /pool/{pid}``."""

    online: bool = True
    name: str | None = None
    mac: str | None = None

    ph: float | None = None
    ph_target: float | None = None
    rx: float | None = None
    rx_target: float | None = None

    water_temperature: float | None = None
    water_temperature_target: float | None = None
    outside_temperature: float | None = None
    solar_temperature: float | None = None
    frost_protection: bool | None = None

    pump_speed: str | None = None  # configured speed: off/low/medium/high
    pump_force: bool | None = None  # filter "always active"
    pump_running: bool | None = None

    lighting_on: bool | None = None

    cover_state: str | None = None  # "open"/"closed" once mapping is known
    cover_status_raw: int | None = None

    raw: dict[str, Any] = field(default_factory=dict)


class SmartPoolControlError(Exception):
    """Base error."""


class AuthenticationError(SmartPoolControlError):
    """Raised when the API key is rejected."""


def _get(data: Any, *path: str, default: Any = None) -> Any:
    """Safely walk a nested dict/list by keys, returning *default* on miss."""
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


class SmartPoolControlClient:
    """Talks to the Smart Pool Connect REST API using an API key."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str,
        session: aiohttp.ClientSession | None = None,
        pool_id: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self.pool_id = pool_id
        self._owns_session = session is None
        self._session = session or aiohttp.ClientSession()

    # -- lifecycle ---------------------------------------------------------

    async def close(self) -> None:
        if self._owns_session:
            await self._session.close()

    async def __aenter__(self) -> SmartPoolControlClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # -- low level ---------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    async def _request(
        self, method: str, path: str, *, json: Any | None = None
    ) -> Any:
        headers = {"X-API-Key": self._api_key, "Accept": "application/json"}
        try:
            async with self._session.request(
                method, self._url(path), json=json, headers=headers
            ) as resp:
                if resp.status in (401, 403):
                    raise AuthenticationError(
                        f"API key rejected (HTTP {resp.status})"
                    )
                if resp.status >= 400:
                    body = await resp.text()
                    raise SmartPoolControlError(
                        f"{method} {path} failed: HTTP {resp.status} {body[:200]}"
                    )
                if resp.status == 204 or not resp.content_length:
                    # PATCH may return an empty body; fall through to text check.
                    text = await resp.text()
                    if not text:
                        return None
                    return await resp.json(content_type=None)
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise SmartPoolControlError(str(err)) from err

    # -- reading -----------------------------------------------------------

    async def async_list_pools(self) -> list[dict[str, Any]]:
        """Return the pools accessible to this API key."""
        data = await self._request("GET", "/pool")
        items = data.get("items") if isinstance(data, dict) else data
        return items or []

    async def async_get_status(self) -> PoolStatus:
        """Fetch and parse the full pool state."""
        if not self.pool_id:
            raise SmartPoolControlError("No pool id configured")
        data = await self._request("GET", f"/pool/{self.pool_id}")
        return self._parse_status(data)

    @staticmethod
    def _parse_status(data: dict[str, Any]) -> PoolStatus:
        status = PoolStatus(raw=data)
        status.online = data.get("status") == "online"
        status.name = data.get("name")
        status.mac = (data.get("mac_address") or "").upper() or None

        status.ph = _get(data, "ph", "metrics", "actual")
        ph_target = _get(data, "ph", "config", "target")
        status.ph_target = round(ph_target, 2) if ph_target is not None else None

        status.rx = _get(data, "cl", "metrics", "actual")
        status.rx_target = _get(data, "cl", "config", "rx", "target")

        water = _get(data, "temperature", "metrics", "water_temp")
        status.water_temperature = round(water, 1) if water is not None else None
        outside = _get(data, "temperature", "metrics", "ambient_temp")
        status.outside_temperature = round(outside, 1) if outside is not None else None
        status.water_temperature_target = _get(data, "temperature", "config", "target")
        status.frost_protection = _get(
            data, "temperature", "config", "frost_protection"
        )

        status.pump_speed = _get(data, "filter", "config", "pump_speed")
        status.pump_force = _get(data, "filter", "config", "always_active")
        actual_speed = _get(data, "filter", "metrics", "pump_speed")
        status.pump_running = bool(actual_speed) if actual_speed is not None else None

        light_state = _get(data, "lighting", "status", "status")
        status.lighting_on = bool(light_state) if light_state is not None else None

        status.cover_status_raw = _get(data, "cover", "status", "status")
        return status

    # -- writing (PATCH the changed field(s), no envelope) -----------------

    async def _patch_module(self, module: str, body: dict[str, Any]) -> None:
        """PATCH a module with *body* as the raw JSON (no ``config`` wrapper)."""
        await self._request(
            "PATCH", f"/pool/{self.pool_id}/{module}", json=body
        )

    async def _get_module_config(self, module: str) -> dict[str, Any]:
        """Return a module's current ``config`` object."""
        data = await self._request("GET", f"/pool/{self.pool_id}/{module}")
        return dict(data.get("config") or {})

    async def async_set_ph_target(self, value: float) -> None:
        await self._patch_module(MODULE_PH, {"target": value})

    async def async_set_rx_target(self, value: float) -> None:
        # cl accepts the setpoint flat, even though it reads back at config.rx.target.
        await self._patch_module(MODULE_CL, {"target": value})

    async def async_set_water_target(self, value: float) -> None:
        await self._patch_module(MODULE_TEMPERATURE, {"target": value})

    async def async_set_frost_protection(self, enabled: bool) -> None:
        # frost_protection alone is rejected (HTTP 500); it must ride along with
        # the current target, so read that first.
        config = await self._get_module_config(MODULE_TEMPERATURE)
        body: dict[str, Any] = {"frost_protection": enabled}
        if config.get("target") is not None:
            body["target"] = config["target"]
        await self._patch_module(MODULE_TEMPERATURE, body)

    async def async_set_pump_force(self, enabled: bool) -> None:
        # filter is an untagged enum: send the whole config struct back.
        config = await self._get_module_config(MODULE_FILTER)
        config["always_active"] = enabled
        await self._patch_module(MODULE_FILTER, config)

    async def async_set_pump_speed(self, speed: str) -> None:
        config = await self._get_module_config(MODULE_FILTER)
        config["pump_speed"] = speed
        await self._patch_module(MODULE_FILTER, config)

    async def async_set_lighting(self, on: bool) -> None:
        await self._patch_module(MODULE_LIGHTING, {"always_active": on})
