"""Config flow for Smart Pool Connect."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .api import AuthenticationError, SmartPoolControlClient, SmartPoolControlError
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_POOL_ID,
    CONF_POOL_MAC,
    CONF_POOL_NAME,
    DEFAULT_BASE_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
    }
)


class SmartPoolControlConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the configuration flow."""

    VERSION = 2

    def __init__(self) -> None:
        self._api_key: str | None = None
        self._base_url: str = DEFAULT_BASE_URL
        self._pools: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            self._base_url = user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL)
            client = SmartPoolControlClient(self._api_key, base_url=self._base_url)
            try:
                self._pools = await client.async_list_pools()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except SmartPoolControlError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            else:
                if not self._pools:
                    errors["base"] = "no_pools"
                elif len(self._pools) == 1:
                    return await self._create_entry(self._pools[0])
                else:
                    return await self.async_step_select_pool()
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_select_pool(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick a pool when the API key exposes more than one."""
        if user_input is not None:
            pool = next(
                p for p in self._pools if p.get("pid") == user_input[CONF_POOL_ID]
            )
            return await self._create_entry(pool)

        options = {
            p["pid"]: f"{p.get('name') or p['pid']} ({p.get('mac_address', '?')})"
            for p in self._pools
        }
        return self.async_show_form(
            step_id="select_pool",
            data_schema=vol.Schema({vol.Required(CONF_POOL_ID): vol.In(options)}),
        )

    async def _create_entry(self, pool: dict[str, Any]) -> ConfigFlowResult:
        pid = pool["pid"]
        await self.async_set_unique_id(pid)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=pool.get("name") or f"Pool {pid}",
            data={
                CONF_API_KEY: self._api_key,
                CONF_BASE_URL: self._base_url,
                CONF_POOL_ID: pid,
                CONF_POOL_NAME: pool.get("name"),
                CONF_POOL_MAC: pool.get("mac_address"),
            },
        )
