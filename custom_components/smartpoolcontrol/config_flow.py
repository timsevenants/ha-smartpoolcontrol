"""Config flow for Smart Pool Control."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .api import AuthenticationError, SmartPoolControlClient, SmartPoolControlError
from .const import (
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
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
    }
)


class SmartPoolControlConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the configuration flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            client = SmartPoolControlClient(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                base_url=user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
            )
            try:
                await client.async_login()
                status = await client.async_get_status()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except SmartPoolControlError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(client.pool_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=status.name or f"Pool {client.pool_id}",
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_BASE_URL: user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                        CONF_POOL_ID: client.pool_id,
                        CONF_POOL_NAME: status.name,
                        CONF_POOL_MAC: status.mac,
                    },
                )
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
